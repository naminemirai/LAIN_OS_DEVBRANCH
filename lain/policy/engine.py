from __future__ import annotations

from enum import Enum

from lain.capabilities.registry import CapabilityDefinition
from lain.config import RuntimeConfig
from lain.protocol.models import Action


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"


def evaluate_policy(
    capability: CapabilityDefinition,
    action: Action,
    config: RuntimeConfig,
) -> PolicyDecision:
    if int(capability.risk_class) >= config.deny_risk_threshold:
        return PolicyDecision.DENY
    if int(capability.risk_class) >= config.confirmation_risk_threshold:
        return PolicyDecision.REQUIRE_CONFIRMATION
    if capability.confirmation_required:
        return PolicyDecision.REQUIRE_CONFIRMATION
    if action.arguments.get("overwrite") is True:
        return PolicyDecision.REQUIRE_CONFIRMATION
    return PolicyDecision.ALLOW
