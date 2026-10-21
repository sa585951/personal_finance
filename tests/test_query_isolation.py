from models.budget_manager import BudgetManager
from tests.test_ai_parse_api import FakeDBSession, _auth_headers, _load_web_app


def test_api_rejects_trip_monthly_projection_before_query(monkeypatch):
    app = _load_web_app(monkeypatch)
    monkeypatch.setattr(app, "budget_manager", BudgetManager(None))
    monkeypatch.setattr(app, "db_session", FakeDBSession())
    response = app.app.test_client().get(
        "/api/transactions?trip_id=11111111-1111-1111-1111-111111111111&monthly_report=true",
        headers=_auth_headers(),
    )
    assert response.status_code == 400
    assert "trip_id 不可與 monthly_report" in response.get_json()["message"]


def test_regular_trip_and_monthly_requests_keep_distinct_projections(monkeypatch):
    # Compile both normal query paths without opening a database connection.
    from sqlalchemy.dialects import postgresql

    class StopQuery(Exception):
        pass

    class CaptureSession:
        def execute(self, statement):
            self.sql = str(statement.compile(dialect=postgresql.dialect()))
            raise StopQuery

    import pytest
    from models.trip_manager import TripManager
    monkeypatch.setattr(TripManager, "get_trip", lambda *args: {})
    monkeypatch.setattr(BudgetManager, "_get_current_trip_member", lambda *args: {})
    session = CaptureSession()
    manager = BudgetManager(session)
    for kwargs in (
        {"trip_id": "11111111-1111-1111-1111-111111111111"},
        {"monthly_report": True},
    ):
        with pytest.raises(StopQuery):
            manager.get_all_transactions("22222222-2222-2222-2222-222222222222", **kwargs)
        assert ", transaction_splits " not in session.sql
        if kwargs.get("monthly_report"):
            assert "JOIN transaction_splits ON" in session.sql
            assert "transaction_splits.trip_member_id = trip_members.id" in session.sql
