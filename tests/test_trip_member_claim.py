"""Invite preview, claiming an account-less member, and owner release."""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.schema import trip_members_table
from models.trip_manager import TripManager
from models.user_manager import UserManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def _fresh_invite(trips, data):
    trips.close_invite(data["a"], data["trip"])
    return trips.create_invite(data["a"], data["trip"])["token"]


def test_preview_shows_only_cover_name_and_inviter(command_db):
    engine, data = command_db
    with Session(engine) as s:
        trips = TripManager(s)
        token = _fresh_invite(trips, data)
        preview = trips.preview_invite(token)
        assert set(preview) == {"trip_name", "cover_theme", "inviter_name"}
        with pytest.raises(ValueError):
            trips.preview_invite("not-a-real-token")
        trips.close_invite(data["a"], data["trip"])
        with pytest.raises(ValueError, match="已關閉"):
            trips.preview_invite(token)


def test_claim_keeps_member_identity_role_and_name(command_db):
    engine, data = command_db
    with Session(engine) as s:
        trips = TripManager(s)
        users = UserManager(s)
        ext = trips.add_external_member(data["a"], data["trip"], "Cara", role="viewer")
        token = _fresh_invite(trips, data)
        newcomer = users.get_or_create_user_for_identity("qa", "claimer-1", "Carol")["id"]
        listing = trips.list_claim_candidates(newcomer, token)
        assert listing["already_joined"] is False and listing["my_name"] == "Carol"
        assert ext["id"] in [c["id"] for c in listing["candidates"]]
        result = trips.accept_invite(newcomer, token, claim_member_id=ext["id"])
        assert result["claimed"] is True
        assert result["member"]["id"] == ext["id"]
        assert result["member"]["display_name"] == "Cara"
        assert result["member"]["role"] == "viewer"
        assert result["member"]["user_id"] == str(newcomer)
        # Gone from the candidates now.
        other = users.get_or_create_user_for_identity("qa", "claimer-2", "Dave")["id"]
        assert ext["id"] not in [c["id"] for c in trips.list_claim_candidates(other, token)["candidates"]]
        with pytest.raises(ValueError, match="已被認領"):
            trips.accept_invite(other, token, claim_member_id=ext["id"])


def test_claim_rejects_real_members_other_trips_and_existing_members(command_db):
    engine, data = command_db
    with Session(engine) as s:
        trips = TripManager(s)
        users = UserManager(s)
        token = _fresh_invite(trips, data)
        newcomer = users.get_or_create_user_for_identity("qa", "claimer-3", "Eve")["id"]
        with pytest.raises(ValueError, match="已被認領"):
            trips.accept_invite(newcomer, token, claim_member_id=data["bm"])  # a real member
        other_trip = trips.create_trip(data["a"], "Other", "2026-12-01", "2026-12-02")
        foreign = trips.add_external_member(data["a"], other_trip["id"], "Zed")
        with pytest.raises(ValueError, match="已被認領"):
            trips.accept_invite(newcomer, token, claim_member_id=foreign["id"])
        # A user who is already in the trip cannot claim a second identity.
        ext = trips.add_external_member(data["a"], data["trip"], "Fay")
        result = trips.accept_invite(data["b"], token, claim_member_id=ext["id"])
        assert result["already_joined"] is True and result["member"]["id"] == str(data["bm"])
        assert ext["id"] in [c["id"] for c in trips.list_claim_candidates(newcomer, token)["candidates"]]


def test_release_detaches_account_but_keeps_member(command_db):
    engine, data = command_db
    with Session(engine) as s:
        trips = TripManager(s)
        users = UserManager(s)
        ext = trips.add_external_member(data["a"], data["trip"], "Gus")
        token = _fresh_invite(trips, data)
        claimer = users.get_or_create_user_for_identity("qa", "claimer-4", "Gus Real")["id"]
        trips.accept_invite(claimer, token, claim_member_id=ext["id"])
        with pytest.raises(ValueError, match="owner"):
            trips.release_member(data["b"], data["trip"], ext["id"])  # not the owner
        released = trips.release_member(data["a"], data["trip"], ext["id"])
        assert released["user_id"] is None and released["display_name"] == "Gus"
        with pytest.raises(ValueError):
            trips.release_member(data["a"], data["trip"], ext["id"])  # already unbound
        row = s.execute(select(trip_members_table).where(trip_members_table.c.id == ext["id"])).first()
        assert row.status == "active" and row.deleted_at is None
        # The released member can be claimed again.
        assert trips.accept_invite(claimer, token, claim_member_id=ext["id"])["claimed"] is True
