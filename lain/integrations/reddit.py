from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from typing import Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from lain.errors import ErrorCode, LainError
from lain.execution.models import ExecutionOutcome
from lain.protocol.models import VerificationResult, VerificationStatus


@dataclass(frozen=True, slots=True)
class RedditCredentials:
    client_id: str
    client_secret: str
    refresh_token: str
    user_agent: str

    @classmethod
    def from_environment(cls) -> "RedditCredentials":
        names = (
            "LAIN_REDDIT_CLIENT_ID",
            "LAIN_REDDIT_CLIENT_SECRET",
            "LAIN_REDDIT_REFRESH_TOKEN",
            "LAIN_REDDIT_USER_AGENT",
        )
        values = {name: os.environ.get(name, "") for name in names}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise LainError(
                ErrorCode.AUTHENTICATION_REQUIRED,
                "Reddit credentials are not configured",
                details={"missing": missing},
            )
        return cls(*(values[name] for name in names))


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class HttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        form: Mapping[str, str] | None,
        timeout: float,
    ) -> HttpResponse: ...


class UrllibTransport:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        form: Mapping[str, str] | None,
        timeout: float,
    ) -> HttpResponse:
        data = urlencode(form).encode() if form is not None else None
        request = Request(url, data=data, headers=dict(headers), method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                return HttpResponse(response.status, dict(response.headers.items()), response.read())
        except HTTPError as exc:
            return HttpResponse(exc.code, dict(exc.headers.items()), exc.read())


class RedditClient:
    def __init__(self, credentials: RedditCredentials, *, transport: HttpTransport | None = None, timeout: float = 15.0):
        self.credentials = credentials
        self.transport = transport or UrllibTransport()
        self.timeout = timeout
        self._access_token: str | None = None

    @classmethod
    def from_environment(cls) -> "RedditClient":
        return cls(RedditCredentials.from_environment())

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        form: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        try:
            return self.transport.request(method, url, headers=headers, form=form, timeout=self.timeout)
        except (TimeoutError, socket.timeout):
            raise LainError(ErrorCode.TIMEOUT, "Reddit request timed out") from None
        except (OSError, URLError):
            raise LainError(ErrorCode.REMOTE_UNAVAILABLE, "Reddit is unavailable") from None

    @staticmethod
    def _json(response: HttpResponse) -> dict:
        try:
            value = json.loads(response.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise LainError(ErrorCode.REMOTE_RESPONSE_INVALID, "Reddit returned invalid JSON") from None
        if not isinstance(value, dict):
            raise LainError(ErrorCode.REMOTE_RESPONSE_INVALID, "Reddit returned an invalid response")
        return value

    def _token(self) -> str:
        import base64

        if self._access_token is not None:
            return self._access_token
        basic = base64.b64encode(f"{self.credentials.client_id}:{self.credentials.client_secret}".encode()).decode()
        response = self._request(
            "POST", "https://www.reddit.com/api/v1/access_token",
            headers={"Authorization": f"Basic {basic}", "User-Agent": self.credentials.user_agent},
            form={"grant_type": "refresh_token", "refresh_token": self.credentials.refresh_token},
        )
        if response.status == 429:
            raise LainError(
                ErrorCode.REMOTE_RATE_LIMITED,
                "Reddit authentication is rate limited",
                details={"retry_after": _header(response.headers, "retry-after")},
            )
        if response.status in {401, 403}:
            raise LainError(ErrorCode.AUTHENTICATION_FAILED, "Reddit authentication failed", details={"http_status": response.status})
        if response.status >= 500:
            raise LainError(ErrorCode.REMOTE_UNAVAILABLE, "Reddit authentication service is unavailable", details={"http_status": response.status})
        payload = self._json(response)
        token = payload.get("access_token")
        if response.status != 200 or not isinstance(token, str) or not token:
            raise LainError(ErrorCode.AUTHENTICATION_FAILED, "Reddit authentication failed", details={"http_status": response.status})
        self._access_token = token
        return token

    def create_post(self, subreddit: str, title: str, body: str) -> ExecutionOutcome:
        try:
            token = self._token()
            response = self._request(
                "POST", "https://oauth.reddit.com/api/submit",
                headers={"Authorization": f"Bearer {token}", "User-Agent": self.credentials.user_agent},
                form={"api_type": "json", "kind": "self", "sr": subreddit, "title": title, "text": body, "resubmit": "true"},
            )
            if response.status == 429:
                return ExecutionOutcome.failure(
                    ErrorCode.REMOTE_RATE_LIMITED.value,
                    "Reddit rate limit reached",
                    retry_after=_header(response.headers, "retry-after"),
                )
            if response.status == 403:
                return ExecutionOutcome.failure(ErrorCode.REMOTE_PERMISSION_DENIED.value, "Reddit denied permission", http_status=403)
            if response.status >= 500:
                return ExecutionOutcome.failure(ErrorCode.REMOTE_UNAVAILABLE.value, "Reddit is unavailable", http_status=response.status)
            payload = self._json(response)
            json_result = payload.get("json")
            if not isinstance(json_result, dict):
                return ExecutionOutcome.failure(ErrorCode.REMOTE_RESPONSE_INVALID.value, "Reddit returned incomplete post metadata")
            errors = json_result.get("errors")
            data = json_result.get("data")
            if response.status != 200 or errors:
                return ExecutionOutcome.failure(ErrorCode.REMOTE_REJECTED.value, "Reddit rejected the post", http_status=response.status)
            if not isinstance(data, dict):
                return ExecutionOutcome.failure(ErrorCode.REMOTE_RESPONSE_INVALID.value, "Reddit returned incomplete post metadata")
            name, url = data.get("name"), data.get("url")
            if not isinstance(name, str) or not name.startswith("t3_") or not isinstance(url, str):
                return ExecutionOutcome.failure(ErrorCode.REMOTE_RESPONSE_INVALID.value, "Reddit returned incomplete post metadata")
            post_id = name.removeprefix("t3_")
            permalink = data.get("permalink") or url
            return ExecutionOutcome.success(post_id=post_id, subreddit=subreddit, permalink=permalink, url=url)
        except LainError as exc:
            return ExecutionOutcome.failure(exc.code.value, exc.message, **exc.details)

    def verify_post(self, *, post_id: str, subreddit: str, title: str) -> VerificationResult:
        try:
            token = self._token()
            headers = {"Authorization": f"Bearer {token}", "User-Agent": self.credentials.user_agent}
            account_response = self._request(
                "GET", "https://oauth.reddit.com/api/v1/me", headers=headers
            )
            if account_response.status != 200:
                return VerificationResult(VerificationStatus.UNAVAILABLE, {"http_status": account_response.status})
            account_name = self._json(account_response).get("name")
            if not isinstance(account_name, str) or not account_name:
                return VerificationResult(VerificationStatus.UNAVAILABLE, {"reason": "account identity unavailable"})
            response = self._request(
                "GET", f"https://oauth.reddit.com/api/info?id=t3_{post_id}",
                headers=headers,
            )
            if response.status != 200:
                return VerificationResult(VerificationStatus.UNAVAILABLE, {"http_status": response.status})
            listing_data = self._json(response).get("data")
            if not isinstance(listing_data, dict):
                return VerificationResult(VerificationStatus.FAILED, {"reason": "post not found"})
            children = listing_data.get("children", [])
            if not isinstance(children, list) or len(children) != 1 or not isinstance(children[0], dict):
                return VerificationResult(VerificationStatus.FAILED, {"reason": "post not found"})
            data = children[0].get("data", {})
            if not isinstance(data, dict):
                return VerificationResult(VerificationStatus.FAILED, {"reason": "post not found"})
            matches = (
                data.get("id") == post_id
                and str(data.get("subreddit", "")).casefold() == subreddit.casefold()
                and data.get("title") == title
                and str(data.get("author", "")).casefold() == account_name.casefold()
            )
            if not matches:
                return VerificationResult(VerificationStatus.FAILED, {"reason": "post metadata mismatch"})
            return VerificationResult(VerificationStatus.PASSED, {"post_id": post_id, "author_verified": True})
        except LainError as exc:
            return VerificationResult(VerificationStatus.UNAVAILABLE, {"error_code": exc.code.value})


def _header(headers: Mapping[str, str], name: str) -> str | None:
    wanted = name.casefold()
    return next((value for key, value in headers.items() if key.casefold() == wanted), None)
