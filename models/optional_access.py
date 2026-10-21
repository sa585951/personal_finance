"""S1 containment only; this is not the future G-AI quota/budget gateway."""
from dataclasses import dataclass

from .security_settings import load_security_settings


@dataclass(frozen=True)
class OptionalAccess:
    ai_parse: bool
    line_interactions: bool
    # No production or paid-cloud enable mode exists before G-AI is implemented.
    cloud_ai: bool = False


def load_optional_access(environ):
    modes = [environ.get(key, "disabled") for key in ("NOMICA_AI_MODE", "NOMICA_LINE_MODE")]
    if any(mode not in {"disabled", "synthetic"} for mode in modes):
        raise ValueError("AI / LINE mode 僅允許 disabled 或本機 synthetic")
    if "synthetic" in modes:
        settings = load_security_settings(environ)
        if settings.environment == "production":
            raise ValueError("AI / LINE 尚未通過公開門檻，synthetic 僅允許本機測試")
    return OptionalAccess(ai_parse=modes[0] == "synthetic", line_interactions=modes[1] == "synthetic")
