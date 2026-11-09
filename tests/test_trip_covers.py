"""Trip cover themes and per-trip expense totals in the trip list."""
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from models.trip_manager import COVER_THEMES, TripManager
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def test_cover_theme_is_validated_and_owner_can_change_it(command_db):
    engine, data = command_db
    with Session(engine) as s:
        trips = TripManager(s)
        trip = trips.create_trip(data["a"], "Kyoto", "2026-12-01", "2026-12-03", cover_theme="sakura")
        assert trip["cover_theme"] == "sakura"
        with pytest.raises(ValueError, match="封面"):
            trips.create_trip(data["a"], "Bad", "2026-12-01", "2026-12-02", cover_theme="neon")
        updated = trips.update_trip(data["a"], trip["id"], cover_theme="night")
        assert updated["cover_theme"] == "night"
        # Members who are not the owner cannot repaint the shared cover.
        with pytest.raises(ValueError):
            trips.update_trip(data["b"], data["trip"], cover_theme="forest")
        assert set(COVER_THEMES) >= {"ocean", "sunset", "night"}


def test_trip_list_carries_expense_total(command_db):
    engine, data = command_db
    with Session(engine) as s:
        listed = {trip["id"]: trip for trip in TripManager(s).list_trips(data["a"])}
        assert Decimal(listed[str(data["trip"])]["expense_total"]) == Decimal("1000")
        empty = TripManager(s).create_trip(data["a"], "Empty", "2026-12-01", "2026-12-02")
        listed = {trip["id"]: trip for trip in TripManager(s).list_trips(data["a"])}
        assert Decimal(listed[empty["id"]]["expense_total"]) == 0
