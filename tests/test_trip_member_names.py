"""Names belong to the trip: unique per trip, renameable, and avatars only for co-members."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update
from sqlalchemy.orm import Session

from models.schema import users_table
from models.trip_manager import TripManager, member_name_key, normalize_member_name, safe_avatar_url
from models.user_manager import UserManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def test_name_normalisation_and_keys():
    assert normalize_member_name("  Amy   Lin ") == "Amy Lin"
    assert normalize_member_name("ＡＭＹ") == "AMY"  # full-width letters fold to ASCII
    assert member_name_key("Amy") == member_name_key("ＡＭＹ ".strip()) == member_name_key("amy")
    for bad in ("", "   ", "x" * 41):
        with pytest.raises(ValueError):
            normalize_member_name(bad)


def test_only_https_avatars_are_exposed():
    assert safe_avatar_url("https://profile.line-scdn.net/abc") == "https://profile.line-scdn.net/abc"
    for bad in (None, "", "http://x.example/a.png", "javascript:alert(1)", "data:image/png;base64,AAAA", "https://" + "a" * 600):
        assert safe_avatar_url(bad) is None


def test_external_member_names_must_be_unique_in_the_trip(command_db):
    engine, data = command_db
    with Session(engine) as s:
        trips = TripManager(s)
        trips.add_external_member(data["a"], data["trip"], "Cara")
        for clash in ("cara", " CARA ", "Ｃａｒａ"):
            with pytest.raises(ValueError, match="已經有叫"):
                trips.add_external_member(data["a"], data["trip"], clash)
        # The same name in a different trip is fine.
        other = trips.create_trip(data["a"], "Other", "2026-12-01", "2026-12-02")
        trips.add_external_member(data["a"], other["id"], "Cara")


def test_joining_with_a_taken_name_gets_a_number_instead_of_being_refused(command_db):
    engine, data = command_db
    with Session(engine) as s:
        users = UserManager(s)
        trips = TripManager(s)
        first = users.get_or_create_user_for_identity("qa", "name-clash-1", "Amy")["id"]
        second = users.get_or_create_user_for_identity("qa", "name-clash-2", "amy")["id"]
        trips.close_invite(data["a"], data["trip"])
        invite = trips.create_invite(data["a"], data["trip"])
        one = trips.accept_invite(first, invite["token"])["member"]["display_name"]
        two = trips.accept_invite(second, invite["token"])["member"]["display_name"]
        assert one == "Amy" and two == "amy 2"


def test_rename_permissions_and_clashes(command_db):
    engine, data = command_db
    with Session(engine) as s:
        trips = TripManager(s)
        external = trips.add_external_member(data["a"], data["trip"], "Dan")
        # Owner renames anyone; a member renames only themselves.
        assert trips.rename_member(data["a"], data["trip"], external["id"], "Daniel")["display_name"] == "Daniel"
        assert trips.rename_member(data["b"], data["trip"], data["bm"], "Bobby")["display_name"] == "Bobby"
        with pytest.raises(ValueError, match="owner 或本人"):
            trips.rename_member(data["b"], data["trip"], external["id"], "Hacked")
        with pytest.raises(ValueError, match="owner 或本人"):
            trips.rename_member(data["b"], data["trip"], data["am"], "Hacked")
        # Clashes are refused, but keeping or re-casing your own name is allowed.
        with pytest.raises(ValueError, match="已經有叫"):
            trips.rename_member(data["a"], data["trip"], external["id"], "bobby")
        assert trips.rename_member(data["b"], data["trip"], data["bm"], "BOBBY")["display_name"] == "BOBBY"
        # Outsiders cannot rename at all.
        stranger = UserManager(s).get_or_create_user_for_identity("qa", "stranger", "S")["id"]
        with pytest.raises(ValueError):
            trips.rename_member(stranger, data["trip"], data["am"], "Nope")


def test_members_carry_an_avatar_only_when_they_have_one(command_db):
    engine, data = command_db
    with Session(engine) as s:
        s.execute(update(users_table).where(users_table.c.id == data["a"]).values(avatar_url="https://profile.line-scdn.net/a"))
        s.execute(update(users_table).where(users_table.c.id == data["b"]).values(avatar_url="http://insecure.example/b"))
        s.commit()
        members = {m["id"]: m for m in TripManager(s).list_trip_members(data["a"], data["trip"])}
        assert members[str(data["am"])]["avatar_url"] == "https://profile.line-scdn.net/a"
        assert members[str(data["bm"])]["avatar_url"] is None
        external = TripManager(s).add_external_member(data["a"], data["trip"], "Eve")
        assert {m["id"]: m for m in TripManager(s).list_trip_members(data["a"], data["trip"])}[external["id"]]["avatar_url"] is None
        # A stranger cannot list members (and so cannot see avatars).
        stranger = UserManager(s).get_or_create_user_for_identity("qa", "stranger2", "S")["id"]
        with pytest.raises(ValueError):
            TripManager(s).list_trip_members(stranger, data["trip"])
