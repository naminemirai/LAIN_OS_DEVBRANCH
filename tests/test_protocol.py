import json
import unittest
from uuid import uuid4

from lain.errors import ErrorCode, LainError
from lain.protocol.models import ActionStatus, VerificationStatus
from lain.protocol.parser import parse_envelope


def valid_request():
    return {
        "version": "0",
        "request_id": str(uuid4()),
        "intent": "write a note",
        "actions": [
            {
                "id": "a1",
                "type": "file.write_text",
                "arguments": {"path": "note.md", "content": "hello"},
            }
        ],
    }


class ProtocolTests(unittest.TestCase):
    def test_parses_valid_envelope(self):
        envelope = parse_envelope(valid_request(), max_actions=8)
        self.assertEqual(envelope.version, "0")
        self.assertEqual(envelope.actions[0].type, "file.write_text")
        self.assertEqual(envelope.actions[0].arguments["content"], "hello")

    def test_parses_json_string(self):
        envelope = parse_envelope(json.dumps(valid_request()), max_actions=8)
        self.assertEqual(len(envelope.actions), 1)

    def test_rejects_malformed_json(self):
        with self.assertRaises(LainError) as ctx:
            parse_envelope("{bad json", max_actions=8)
        self.assertEqual(ctx.exception.code, ErrorCode.PROTOCOL_INVALID)

    def test_rejects_unsupported_version(self):
        request = valid_request()
        request["version"] = "99"
        with self.assertRaises(LainError) as ctx:
            parse_envelope(request, max_actions=8)
        self.assertEqual(ctx.exception.code, ErrorCode.PROTOCOL_VERSION_UNSUPPORTED)

    def test_rejects_missing_required_field(self):
        request = valid_request()
        del request["intent"]
        with self.assertRaises(LainError) as ctx:
            parse_envelope(request, max_actions=8)
        self.assertEqual(ctx.exception.code, ErrorCode.PROTOCOL_INVALID)

    def test_rejects_duplicate_action_ids(self):
        request = valid_request()
        request["actions"].append({
            "id": "a1",
            "type": "file.copy",
            "arguments": {"source": "a", "destination": "b"},
        })
        with self.assertRaises(LainError) as ctx:
            parse_envelope(request, max_actions=8)
        self.assertEqual(ctx.exception.code, ErrorCode.PROTOCOL_INVALID)

    def test_rejects_action_limit_overflow(self):
        request = valid_request()
        request["actions"].append({"id": "a2", "type": "file.copy", "arguments": {}})
        with self.assertRaises(LainError) as ctx:
            parse_envelope(request, max_actions=1)
        self.assertEqual(ctx.exception.code, ErrorCode.PROTOCOL_INVALID)

    def test_rejects_non_uuid_request_id(self):
        request = valid_request()
        request["request_id"] = "not-a-uuid"
        with self.assertRaises(LainError) as ctx:
            parse_envelope(request, max_actions=8)
        self.assertEqual(ctx.exception.code, ErrorCode.PROTOCOL_INVALID)

    def test_status_enums_are_stable_strings(self):
        self.assertEqual(ActionStatus.SUCCESS.value, "success")
        self.assertEqual(VerificationStatus.PASSED.value, "passed")


if __name__ == "__main__":
    unittest.main()
