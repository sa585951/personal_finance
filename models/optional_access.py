"""S1 containment only; this is not the future G-AI quota/budget gateway."""
from dataclasses import dataclass

from .security_settings import load_security_settings


@dataclass(frozen=True)
class OptionalAccess:
    ai_parse: bool
    line_interactions: bool
    # No production or paid-cloud enable mode exists before G-AI is implemented.
    cloud_ai: bool = False
    line_help_user_ids: frozenset[str] = frozenset()
    line_oral_pilot: bool = False


def load_optional_access(environ):
    ai_mode = environ.get("NOMICA_AI_MODE", "disabled")
    line_mode = environ.get("NOMICA_LINE_MODE", "disabled")
    if ai_mode not in {"disabled", "synthetic"}:
        raise ValueError("AI mode 僅允許 disabled 或本機 synthetic")
    if line_mode not in {"disabled", "synthetic", "help_only", "oral_pilot"}:
        raise ValueError("LINE mode 僅允許 disabled、本機 synthetic、oral_pilot 或 help_only")
    if ai_mode == "synthetic" or line_mode in {"synthetic", "oral_pilot"}:
        settings = load_security_settings(environ)
        if settings.environment == "production":
            raise ValueError("AI / LINE 尚未通過公開門檻，synthetic / oral_pilot 僅允許本機測試")
    help_users = frozenset()
    if line_mode in {"help_only", "oral_pilot"}:
        help_users = frozenset(filter(None, map(str.strip, environ.get("NOMICA_LINE_HELP_USER_IDS", "").split(","))))
        if not help_users:
            raise ValueError("LINE 試用需要設定 NOMICA_LINE_HELP_USER_IDS")

    return OptionalAccess(
        ai_parse=ai_mode == "synthetic",
        line_interactions=line_mode == "synthetic",
        line_help_user_ids=help_users,
        line_oral_pilot=line_mode == "oral_pilot",
    )
