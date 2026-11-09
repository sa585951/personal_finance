"""S5 minimum: export, sign-out everywhere and account deletion against PostgreSQL."""
import csv
import io
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.account_privacy import DELETE_CONFIRMATION, DELETED_NAME, AccountPrivacyService, SharedTripOwnershipError
from models.auth_session_manager import AuthSessionManager
from models.schema import (
    accounts_table, auth_sessions_table, transactions_table, trip_members_table,
    user_identities_table, users_table,
)
from models.trip_manager import TripManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def _rows(archive, name):
    text = archive.read(name).decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def test_export_contains_only_the_owners_rows(command_db):
    engine, data = command_db
    with Session(engine) as s:
        blob = AccountPrivacyService(s).export_zip(data["a"])
    archive = zipfile.ZipFile(io.BytesIO(blob))
    accounts = {row["name"] for row in _rows(archive, "accounts.csv")}
    assert accounts == {"cash", "bank"}
    assert [row["title"] for row in _rows(archive, "transactions.csv")] == ["Dinner"]
    assert _rows(archive, "profile.csv")[0]["display_name"] == "A"
    assert "README.txt" in archive.namelist()


def test_revoke_all_sessions_signs_out_every_device(command_db):
    engine, data = command_db
    with Session(engine) as s:
        sessions = AuthSessionManager(s)
        expires = datetime.now(timezone.utc) + timedelta(days=1)
        first = sessions.create_session(data["a"], "line", expires)
        second = sessions.create_session(data["a"], "line", expires)
        other = sessions.create_session(data["b"], "line", expires)
        assert AccountPrivacyService(s).revoke_all_sessions(data["a"]) == 2
        assert sessions.validate_session(first["id"], data["a"]) is None
        assert sessions.validate_session(second["id"], data["a"]) is None
        assert sessions.validate_session(other["id"], data["b"]) is not None


def test_owner_of_a_shared_trip_cannot_delete_and_nothing_changes(command_db):
    engine, data = command_db
    with Session(engine) as s:
        with pytest.raises(SharedTripOwnershipError) as error:
            AccountPrivacyService(s).delete_account(data["a"], DELETE_CONFIRMATION)
        s.rollback()
        assert error.value.trip_names == ["Commands"]
        assert s.scalar(select(users_table.c.deleted_at).where(users_table.c.id == data["a"])) is None


def test_wrong_confirmation_is_rejected(command_db):
    engine, data = command_db
    with Session(engine) as s, pytest.raises(ValueError):
        AccountPrivacyService(s).delete_account(data["b"], "delete")


def test_member_deletion_keeps_shared_records_but_anonymises(command_db):
    engine, data = command_db
    with Session(engine) as s:
        AuthSessionManager(s).create_session(data["b"], "line", datetime.now(timezone.utc) + timedelta(days=1))
        result = AccountPrivacyService(s).delete_account(data["b"], DELETE_CONFIRMATION)
        s.commit()
        assert result["closed_trips"] == 0

        user = s.execute(select(users_table).where(users_table.c.id == data["b"])).one()
        assert user.display_name == DELETED_NAME and user.deleted_at and user.purge_after
        assert s.scalar(select(func.count()).select_from(user_identities_table)
                        .where(user_identities_table.c.user_id == data["b"])) == 0
        assert s.scalar(select(func.count()).select_from(auth_sessions_table).where(
            auth_sessions_table.c.user_id == data["b"], auth_sessions_table.c.revoked_at.is_(None))) == 0
        assert s.scalar(select(accounts_table.c.deleted_at).where(accounts_table.c.id == data["b_cash"]))
        member = s.execute(select(trip_members_table).where(trip_members_table.c.id == data["bm"])).one()
        assert member.status == "removed" and member.display_name == DELETED_NAME
        # The owner's shared trip expense still exists for them.
        assert s.scalar(select(func.count()).select_from(transactions_table).where(
            transactions_table.c.trip_id == data["trip"], transactions_table.c.deleted_at.is_(None))) == 1
        # The owner's own data is untouched.
        assert s.scalar(select(accounts_table.c.deleted_at).where(accounts_table.c.id == data["cash"])) is None


def test_owner_can_delete_after_closing_shared_trip(command_db):
    engine, data = command_db
    with Session(engine) as s:
        TripManager(s).delete_trip(data["a"], data["trip"])
        AccountPrivacyService(s).delete_account(data["a"], DELETE_CONFIRMATION)
        s.commit()
        assert s.scalar(select(func.count()).select_from(accounts_table).where(
            accounts_table.c.user_id == data["a"], accounts_table.c.deleted_at.is_(None))) == 0
        assert s.scalar(select(users_table.c.deleted_at).where(users_table.c.id == data["a"]))
        with pytest.raises(ValueError):
            AccountPrivacyService(s).delete_account(data["a"], DELETE_CONFIRMATION)
