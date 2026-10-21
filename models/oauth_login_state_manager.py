import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, insert, update

from .schema import oauth_login_states_table as states


class OAuthLoginStateManager:
    """Short-lived, browser-bound, single-use state shared by all workers."""

    def __init__(self, session):
        self.session = session

    @staticmethod
    def _digest(value):
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def issue(self, redirect_path, ttl_minutes=10):
        now = datetime.now(timezone.utc)
        state, browser_token, nonce = (secrets.token_hex(32) for _ in range(3))
        # Expired login metadata has no ongoing business or replay purpose.
        self.session.execute(delete(states).where(states.c.expires_at <= now))
        self.session.execute(insert(states).values(
            state_hash=self._digest(state), browser_hash=self._digest(browser_token),
            redirect_path=redirect_path, nonce=nonce,
            expires_at=now + timedelta(minutes=ttl_minutes),
        ))
        return {"state": state, "browser_token": browser_token, "nonce": nonce}

    def consume(self, state, browser_token):
        if any(not isinstance(value, str) or len(value) != 64 for value in (state, browser_token)):
            raise ValueError("登入驗證失敗或已過期，請重新登入")
        now = datetime.now(timezone.utc)
        # One conditional UPDATE makes simultaneous callbacks single-use.
        row = self.session.execute(update(states).where(
            states.c.state_hash == self._digest(state),
            states.c.browser_hash == self._digest(browser_token),
            states.c.consumed_at.is_(None), states.c.expires_at > now,
        ).values(consumed_at=now).returning(states)).mappings().one_or_none()
        if row is None:
            raise ValueError("登入驗證失敗或已過期，請重新登入")
        return dict(row)
