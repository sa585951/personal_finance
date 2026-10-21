from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from sqlalchemy import create_engine, select, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from models.oauth_login_state_manager import OAuthLoginStateManager
from models.schema import oauth_login_states_table as states
from tests.test_schema_smoke import _get_test_database_url


@pytest.fixture
def state_db():
    url = _get_test_database_url()
    parsed = make_url(url)
    if parsed.host not in {"127.0.0.1", "localhost"} or not parsed.database.endswith("_test"):
        pytest.fail("OAuth regression requires an isolated loopback *_test database")
    engine = create_engine(url)
    with engine.begin() as connection:
        states.drop(connection, checkfirst=True)
        states.create(connection)
    yield engine
    engine.dispose()


def test_browser_binding_hashes_and_replay_survive_sessions(state_db):
    with Session(state_db) as session:
        challenge = OAuthLoginStateManager(session).issue("/trips/test")
        session.commit()
        row = session.execute(select(states)).mappings().one()
        assert row["state_hash"] != challenge["state"]
        assert row["browser_hash"] != challenge["browser_token"]
    with Session(state_db) as session:
        manager = OAuthLoginStateManager(session)
        with pytest.raises(ValueError):
            manager.consume(challenge["state"], "x" * 64)
        session.rollback()
        row = manager.consume(challenge["state"], challenge["browser_token"])
        assert row["redirect_path"] == "/trips/test" and row["nonce"] == challenge["nonce"]
        session.commit()
    with Session(state_db) as session:
        with pytest.raises(ValueError):
            OAuthLoginStateManager(session).consume(challenge["state"], challenge["browser_token"])


def test_parallel_callbacks_only_consume_once(state_db):
    with Session(state_db) as session:
        challenge = OAuthLoginStateManager(session).issue("/")
        session.commit()
    barrier = Barrier(4)
    def consume(_):
        with Session(state_db) as session:
            barrier.wait(timeout=10)
            try:
                OAuthLoginStateManager(session).consume(challenge["state"], challenge["browser_token"])
                session.commit()
                return True
            except ValueError:
                session.rollback()
                return False
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(consume, range(4))).count(True) == 1


def test_expiry_rejects_and_new_login_cleans_expired_metadata(state_db):
    with Session(state_db) as session:
        manager = OAuthLoginStateManager(session)
        challenge = manager.issue("/")
        session.execute(update(states).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        session.commit()
        with pytest.raises(ValueError):
            manager.consume(challenge["state"], challenge["browser_token"])
        session.rollback()
        manager.issue("/assets")
        session.commit()
        assert len(session.execute(select(states)).all()) == 1
