"""Validation of the conservative structured battery evidence contract."""
from __future__ import annotations

import math
from typing import Any

_ENUMS = {
    "status": {"UNKNOWN", "CHARGING", "DISCHARGING", "NOT_CHARGING", "FULL"},
    "plugged": {"UNPLUGGED", "PLUGGED_AC", "PLUGGED_USB", "PLUGGED_WIRELESS", "PLUGGED_DOCK", "UNKNOWN"},
    "health": {"UNKNOWN", "GOOD", "OVERHEAT", "DEAD", "OVER_VOLTAGE", "UNSPECIFIED_FAILURE", "COLD"},
}


def validate_battery(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("battery result must be an object")
    percentage = value.get("percentage")
    if type(percentage) is not int or not 0 <= percentage <= 100:
        raise ValueError("battery percentage must be an integer in 0..100")
    result = {"percentage": percentage}
    for name, allowed in _ENUMS.items():
        if name in value:
            item = value[name]
            if not isinstance(item, str) or item not in allowed:
                raise ValueError("invalid battery enum")
            result[name] = item
    for name in ("temperature", "current"):
        if name in value:
            item = value[name]
            if type(item) not in (int, float) or not math.isfinite(item):
                raise ValueError("invalid battery measurement")
            if name == "temperature" and not -100 <= item <= 200:
                raise ValueError("invalid battery temperature")
            result[name] = item
    return result
