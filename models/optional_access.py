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


def load_optional_access(environ):
    ai_mode = environ.get("NOMICA_AI_MODE", "disabled")
    line_mode = environ.get("NOMICA_LINE_MODE", "disabled")
    if ai_mode not in {"disabled", "synthetic"}:
        raise ValueError("AI mode 僅允許 disabled 或本機 synthetic")
    if line_mode not in {"disabled", "synthetic", "help_only"}:
        raise ValueError("LINE mode 僅允許 disabled、本機 synthetic 或 help_only")
    if "synthetic" in (ai_mode, line_mode):
        settings = load_security_settings(environ)
        if settings.environment == "production":
            raise ValueError("AI / LINE 尚未通過公開門檻，synthetic 僅允許本機測試")
    help_users = frozenset()
    if line_mode == "help_only":
        help_users = frozenset(filter(None, map(str.strip, environ.get("NOMICA_LINE_HELP_USER_IDS", "").split(","))))
        if not help_users:
            raise ValueError("LINE help_only 需要設定 NOMICA_LINE_HELP_USER_IDS")

    return OptionalAccess(
        ai_parse=ai_mode == "synthetic",
        line_interactions=line_mode == "synthetic",
        line_help_user_ids=help_users,
    )
