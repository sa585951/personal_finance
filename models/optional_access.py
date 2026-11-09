"""S1 containment only; this is not the future G-AI quota/budget gateway."""
from dataclasses import dataclass

from .security_settings import load_security_settings


@dataclass(frozen=True)
class OptionalAccess:
    ai_parse: bool
    line_interactions: bool
    # No production or paid-cloud enable mode exists before G-AI is implemented.
    cloud_ai: bool = False
    line_oral_pilot: bool = False


def load_optional_access(environ):
    ai_mode = environ.get("NOMICA_AI_MODE", "disabled")
    line_mode = environ.get("NOMICA_LINE_MODE", "oral_pilot")
    if ai_mode not in {"disabled", "synthetic"}:
        raise ValueError("AI mode 僅允許 disabled 或本機 synthetic")
    if line_mode not in {"disabled", "synthetic", "help_only", "oral_pilot"}:
        raise ValueError("LINE mode 僅允許 disabled、本機 synthetic、oral_pilot 或 help_only")
    if "synthetic" in (ai_mode, line_mode):
        settings = load_security_settings(environ)
        if settings.environment == "production":
            raise ValueError("synthetic 僅允許本機測試")

    return OptionalAccess(
        ai_parse=ai_mode == "synthetic",
        line_interactions=line_mode == "synthetic",
        # Existing deployments can keep their old setting through the upgrade.
        line_oral_pilot=line_mode in {"oral_pilot", "help_only"},
    )
