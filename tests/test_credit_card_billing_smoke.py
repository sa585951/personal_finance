"""需明確指定本機 *_test PostgreSQL；不會碰正式資料庫。"""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine

from models.asset_manager import AssetManager
from models.schema import metadata
from models.seed_data import seed_reference_data
from models.user_manager import UserManager
from tests.test_schema_smoke import _get_test_database_url


def test_credit_card_billing_profile_round_trip_and_user_isolation():
    engine = create_engine(_get_test_database_url(), future=True)
    with engine.begin() as connection:
        metadata.drop_all(connection)
        metadata.create_all(connection)
        seed_reference_data(connection)

        users = UserManager(connection)
        owner = users.get_or_create_user_for_identity(
            provider="line", provider_user_id="U-card-owner", display_name="Card Owner"
        )
        other = users.get_or_create_user_for_identity(
            provider="line", provider_user_id="U-card-other", display_name="Other User"
        )
        assets = AssetManager(connection)
        success, _ = assets.add_account(
            owner["id"], "測試信用卡", "credit_card", -500, currency="TWD",
            credit_card_billing={"closing_day": 5, "due_day": 20, "due_month_offset": 1},
        )
        assert success
        account = next(iter(assets.get_all_assets(owner["id"]).values()))
        assert account["credit_card_billing"]["next_due_date_source"] == "estimated"
        assert assets.get_all_assets(other["id"]) == {}

        billing = account["credit_card_billing"]
        actual_due = (date.fromisoformat(billing["next_due_date"]) + timedelta(days=1)).isoformat()
        success, _ = assets.update_account(
            owner["id"], account["id"],
            credit_card_billing={
                "closing_day": 5, "due_day": 20, "due_month_offset": 1,
                "override_closing_date": billing["next_due_closing_date"],
                "override_due_date": actual_due,
            },
        )
        assert success
        updated = assets.get_all_assets(owner["id"])[account["id"]]
        assert updated["credit_card_billing"]["next_due_date"] == actual_due
        assert updated["credit_card_billing"]["next_due_date_source"] == "user_set"
        assert updated["balance"] == -500

        with pytest.raises(ValueError, match="找不到此帳戶"):
            assets.update_account(other["id"], account["id"], credit_card_billing=None)

        assets.update_account(owner["id"], account["id"], credit_card_billing=None)
        assert assets.get_all_assets(owner["id"])[account["id"]]["credit_card_billing"] is None
