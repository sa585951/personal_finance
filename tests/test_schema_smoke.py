import os
import uuid
from datetime import date
from decimal import Decimal
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select

from models.schema import (
    accounts_table,
    ai_parse_events_table,
    budgets_table,
    categories_table,
    metadata,
    settlements_table,
    transaction_splits_table,
    transactions_table,
    transfers_table,
)
from models.ai_parse_event_manager import AIParseEventManager
from models.budget_manager import BudgetManager
from models.asset_manager import AssetManager
from models.seed_data import seed_reference_data
from models.trip_manager import TripManager
from models.user_manager import UserManager

load_dotenv()


def _get_test_database_url():
    if os.getenv("RUN_DB_SMOKE_TESTS") != "1":
        pytest.skip("Set RUN_DB_SMOKE_TESTS=1 to run DB smoke tests")

    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for destructive DB smoke tests")

    parsed_url = urlparse(database_url)
    database_name = parsed_url.path.lstrip("/")
    if not database_name.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must point to a database ending with '_test'")

    host = parsed_url.hostname
    if host not in {"localhost", "127.0.0.1"} and os.getenv("ALLOW_NON_LOCAL_DB_TESTS") != "1":
        pytest.skip("DB smoke tests only run against localhost by default")

    return database_url


def test_mvp_schema_can_create_core_records():
    engine = create_engine(_get_test_database_url(), future=True)

    with engine.begin() as connection:
        metadata.drop_all(connection)
        metadata.create_all(connection)
        seed_reference_data(connection)

        food_id = connection.execute(
            select(categories_table.c.id).where(
                categories_table.c.kind == "expense",
                categories_table.c.code == "food",
                categories_table.c.user_id.is_(None),
            )
        ).scalar_one()

        user_manager = UserManager(connection)
        user = user_manager.get_or_create_user_for_identity(
            provider="line",
            provider_user_id="U-test-user",
            display_name="Test User",
            provider_email="test@example.com",
        )
        same_user = user_manager.get_or_create_user_for_identity(
            provider="line",
            provider_user_id="U-test-user",
            display_name="Test User Updated",
            provider_email="test@example.com",
        )

        user_id = user["id"]
        source_account_id = uuid.uuid4()
        target_account_id = uuid.uuid4()

        assert same_user["id"] == user_id
        assert same_user["display_name"] == "Test User Updated"

        parse_event_manager = AIParseEventManager(connection)
        parse_event = parse_event_manager.record_from_parse_result(
            user_id=user_id,
            source="line_bot",
            parse_result={
                "intent": "create_transaction",
                "raw_text": "早餐 100",
                "legacy": {"type": "expense", "amount": 100},
                "transaction": {"type": "expense", "amount": "100"},
                "errors": [],
            },
        )
        assert parse_event["status"] == "success"
        stored_parse_event = connection.execute(
            select(ai_parse_events_table).where(ai_parse_events_table.c.id == parse_event["id"])
        ).first()
        assert stored_parse_event is not None

        asset_manager = AssetManager(connection)
        success, message = asset_manager.add_account(
            user_id=user_id,
            bank_name="日幣旅費",
            account_type="cash",
            balance=Decimal("30000"),
            currency="JPY",
        )
        assert success is True
        assert message == "成功新增帳戶"
        created_jpy_account = asset_manager.find_asset_by_name(user_id, "日幣旅費")
        assert created_jpy_account["currency"] == "JPY"
        assert created_jpy_account["balance"] == 30000

        connection.execute(
            accounts_table.insert(),
            [
                {
                    "id": source_account_id,
                    "user_id": user_id,
                    "name": "台幣銀行",
                    "type": "bank",
                    "currency": "TWD",
                    "track_balance": True,
                    "balance": Decimal("10000"),
                },
                {
                    "id": target_account_id,
                    "user_id": user_id,
                    "name": "日幣現金",
                    "type": "cash",
                    "currency": "JPY",
                    "track_balance": True,
                    "balance": Decimal("45000"),
                },
            ],
        )
        trip_manager = TripManager(connection)
        trip = trip_manager.create_trip(
            user_id=user_id,
            name="日本 2027",
            destination="Japan",
            start_date="2027-03-01",
            end_date="2027-03-07",
            timezone_name="Asia/Tokyo",
            base_currency="TWD",
            default_currency="JPY",
        )
        friend_member = trip_manager.add_external_member(
            user_id=user_id,
            trip_id=trip["id"],
            display_name="朋友 A",
            role="viewer",
        )
        unused_member = trip_manager.add_external_member(
            user_id=user_id,
            trip_id=trip["id"],
            display_name="臨時旅伴",
            role="viewer",
        )
        removed_member = trip_manager.remove_member(user_id, trip["id"], unused_member["id"])
        assert removed_member["status"] == "removed"
        assert removed_member["deleted_at"] is not None

        trip_members = trip_manager.list_trip_members(user_id=user_id, trip_id=trip["id"])

        assert len(trip_members) == 2
        assert all(member["display_name"] != "臨時旅伴" for member in trip_members)
        owner_member = next(member for member in trip_members if member["role"] == "owner")
        assert friend_member["user_id"] is None

        trip_id = uuid.UUID(trip["id"])
        owner_member_id = uuid.UUID(owner_member["id"])
        friend_member_id = uuid.UUID(friend_member["id"])

        listed_trips = trip_manager.list_trips(user_id)
        loaded_trip = trip_manager.get_trip(user_id, trip_id)
        assert listed_trips[0]["id"] == trip["id"]
        assert loaded_trip["members"][0]["role"] == "owner"
        assert loaded_trip["members"][0]["monthly_report_preference"] == "exclude"

        updated_trip = trip_manager.update_trip(
            user_id=user_id,
            trip_id=trip["id"],
            include_in_monthly_report=True,
        )
        assert updated_trip["include_in_monthly_report"] is True
        owner_preference = trip_manager.update_current_member_monthly_report_preference(
            user_id,
            trip["id"],
            "include",
        )
        assert owner_preference["member"]["monthly_report_preference"] == "include"

        managed_trip = trip_manager.create_trip(
            user_id=user_id,
            name="管理測試",
            destination="Taiwan",
            start_date="2027-01-01",
            end_date="2027-01-02",
            base_currency="TWD",
            default_currency="TWD",
        )
        trip_manager.archive_trip(user_id, managed_trip["id"])
        assert all(item["id"] != managed_trip["id"] for item in trip_manager.list_trips(user_id))
        assert any(
            item["id"] == managed_trip["id"]
            for item in trip_manager.list_trips(user_id, include_archived=True)
        )
        trip_manager.unarchive_trip(user_id, managed_trip["id"])
        trip_manager.delete_trip(user_id, managed_trip["id"])
        with pytest.raises(ValueError, match="找不到旅行或權限不足"):
            trip_manager.get_trip(user_id, managed_trip["id"])
        assert all(
            item["id"] != managed_trip["id"]
            for item in trip_manager.list_trips(user_id, include_archived=True)
        )
        assert any(
            item["id"] == managed_trip["id"]
            for item in trip_manager.list_trips(
                user_id,
                include_archived=True,
                include_deleted=True,
            )
        )
        trip_manager.restore_trip(user_id, managed_trip["id"])
        restored_trip = trip_manager.get_trip(user_id, managed_trip["id"])
        assert restored_trip["deleted_at"] is None
        assert any(item["id"] == managed_trip["id"] for item in trip_manager.list_trips(user_id))

        budget_manager = BudgetManager(connection)
        success, message = budget_manager.add_transaction(
            user_id=user_id,
            date="2027-03-02",
            item="拉麵",
            amount=Decimal("2001"),
            transaction_type="expense",
            budget_category="伙食",
            description="晚餐",
            account_id=target_account_id,
            trip_id=trip_id,
            paid_by_member_id=owner_member_id,
            merchant="一蘭",
            original_currency="JPY",
            exchange_rate=Decimal("0.22000000"),
            timezone_name="Asia/Tokyo",
            split_member_ids=[owner_member_id, friend_member_id],
        )

        assert success is True
        assert message == "交易新增成功"
        created_transaction_id = budget_manager.last_created_transaction_id
        confirmed_parse_event = parse_event_manager.confirm_event(
            user_id,
            parse_event["id"],
            "expense",
            created_transaction_id,
        )
        assert confirmed_parse_event["status"] == "confirmed"
        assert confirmed_parse_event["result_id"] == created_transaction_id
        recent_parse_events = parse_event_manager.list_recent_events(user_id, limit=5)
        assert recent_parse_events[0]["id"] == str(parse_event["id"])
        assert recent_parse_events[0]["status"] == "confirmed"

        target_balance_after_trip_expense = connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == target_account_id)
        ).scalar_one()
        assert target_balance_after_trip_expense == Decimal("42999.0000")

        transaction = connection.execute(
            select(transactions_table).where(transactions_table.c.trip_id == trip_id)
        ).first()
        transaction_id = transaction.id

        owner_split = connection.execute(
            select(transaction_splits_table.c.share_amount).where(
                transaction_splits_table.c.transaction_id == transaction_id,
                transaction_splits_table.c.trip_member_id == owner_member_id,
            )
        ).scalar_one()
        friend_split = connection.execute(
            select(transaction_splits_table.c.share_amount).where(
                transaction_splits_table.c.transaction_id == transaction_id,
                transaction_splits_table.c.trip_member_id == friend_member_id,
            )
        ).scalar_one()

        assert owner_split == Decimal("1001.0000")
        assert friend_split == Decimal("1000.0000")

        transactions = budget_manager.get_all_transactions(user_id)
        assert transactions == []

        all_transactions = budget_manager.get_all_transactions(user_id, include_trips=True)
        assert {transaction["category"] for transaction in all_transactions} == {"拉麵"}

        trip_transactions = budget_manager.get_all_transactions(user_id, trip_id=trip_id)
        assert trip_transactions[0]["trip_id"] == trip["id"]
        assert trip_transactions[0]["paid_by_member_id"] == str(owner_member_id)
        assert trip_transactions[0]["currency"] == "JPY"
        assert trip_transactions[0]["amount"] == 2001

        initial_split_summary = budget_manager.get_trip_split_summary(user_id, trip_id)
        initial_owner_summary = next(
            item for item in initial_split_summary if item["member_id"] == str(owner_member_id)
        )
        initial_friend_summary = next(
            item for item in initial_split_summary if item["member_id"] == str(friend_member_id)
        )
        assert initial_owner_summary["paid_amount"] == 440.22
        assert initial_owner_summary["share_amount"] == 220.22
        assert initial_owner_summary["net_amount"] == 220.0
        assert initial_friend_summary["paid_amount"] == 0.0
        assert initial_friend_summary["share_amount"] == 220.0
        assert initial_friend_summary["net_amount"] == -220.0

        success, message = budget_manager.update_transaction(
            user_id=user_id,
            transaction_id=transaction_id,
            date="2027-03-02",
            item="拉麵加點",
            amount=Decimal("3001"),
            transaction_type="expense",
            budget_category="伙食",
            description="晚餐加點",
            account_id=target_account_id,
            paid_by_member_id=owner_member_id,
            merchant="一蘭",
            original_currency="JPY",
            exchange_rate=Decimal("0.22000000"),
            timezone_name="Asia/Tokyo",
            split_member_ids=[owner_member_id, friend_member_id],
        )
        assert success is True
        assert message == "交易更新成功"

        target_balance_after_trip_update = connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == target_account_id)
        ).scalar_one()
        assert target_balance_after_trip_update == Decimal("41999.0000")

        updated_transaction = budget_manager.get_transaction_detail(user_id, transaction_id)
        assert updated_transaction["category"] == "拉麵加點"
        assert updated_transaction["amount"] == 3001
        assert updated_transaction["description"] == "晚餐加點"

        updated_owner_split = connection.execute(
            select(transaction_splits_table.c.share_amount).where(
                transaction_splits_table.c.transaction_id == transaction_id,
                transaction_splits_table.c.trip_member_id == owner_member_id,
            )
        ).scalar_one()
        updated_friend_split = connection.execute(
            select(transaction_splits_table.c.share_amount).where(
                transaction_splits_table.c.transaction_id == transaction_id,
                transaction_splits_table.c.trip_member_id == friend_member_id,
            )
        ).scalar_one()
        assert updated_owner_split == Decimal("1501.0000")
        assert updated_friend_split == Decimal("1500.0000")

        updated_split_summary = budget_manager.get_trip_split_summary(user_id, trip_id)
        updated_owner_summary = next(
            item for item in updated_split_summary if item["member_id"] == str(owner_member_id)
        )
        updated_friend_summary = next(
            item for item in updated_split_summary if item["member_id"] == str(friend_member_id)
        )
        assert updated_owner_summary["paid_amount"] == 660.22
        assert updated_owner_summary["share_amount"] == 330.22
        assert updated_owner_summary["net_amount"] == 330.0
        assert updated_friend_summary["paid_amount"] == 0.0
        assert updated_friend_summary["share_amount"] == 330.0
        assert updated_friend_summary["net_amount"] == -330.0

        with pytest.raises(ValueError, match="只有自己付款時才可連動自己的帳戶"):
            budget_manager.add_transaction(
                user_id=user_id,
                date="2027-03-02",
                item="朋友代墊",
                amount=Decimal("1000"),
                transaction_type="expense",
                budget_category="伙食",
                account_id=target_account_id,
                trip_id=trip_id,
                paid_by_member_id=friend_member_id,
                original_currency="JPY",
                exchange_rate=Decimal("0.22000000"),
                split_member_ids=[owner_member_id, friend_member_id],
            )

        with pytest.raises(ValueError, match="已有付款、分攤或結算紀錄"):
            trip_manager.remove_member(user_id, trip_id, friend_member_id)

        connection.execute(
            transfers_table.insert().values(
                user_id=user_id,
                trip_id=trip_id,
                source_account_id=source_account_id,
                target_account_id=target_account_id,
                source_amount=Decimal("10000"),
                source_currency="TWD",
                target_amount=Decimal("45000"),
                target_currency="JPY",
                target_per_source_rate=Decimal("4.50000000"),
                transfer_date=date(2027, 3, 1),
            )
        )
        connection.execute(
            budgets_table.insert().values(
                user_id=user_id,
                scope="monthly",
                period_start=date(2027, 3, 1),
                period_end=date(2027, 3, 31),
                category_id=food_id,
                amount=Decimal("10000"),
                currency="TWD",
            )
        )
        budget_manager.add_transaction(
            user_id=user_id,
            date="2027-03-03",
            item="便當",
            amount=Decimal("120"),
            transaction_type="expense",
            budget_category="伙食",
            account_id=source_account_id,
            original_currency="TWD",
            exchange_rate=Decimal("1"),
        )
        source_balance_after_daily_expense = connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == source_account_id)
        ).scalar_one()
        assert source_balance_after_daily_expense == Decimal("9880.0000")

        # Finance Contract: 手動校正只改帳戶快照，不建立收入或支出。
        transaction_count_before_adjustment = connection.execute(
            select(func.count()).select_from(transactions_table)
        ).scalar_one()
        success, message = asset_manager.update_balance(user_id, source_account_id, Decimal("10380"))
        assert success is True
        assert message == "餘額更新成功"
        success, _ = asset_manager.update_balance(user_id, source_account_id, Decimal("9880"))
        assert success is True
        transaction_count_after_adjustment = connection.execute(
            select(func.count()).select_from(transactions_table)
        ).scalar_one()
        assert transaction_count_after_adjustment == transaction_count_before_adjustment

        # Finance Contract: 信用卡還款是帳戶互轉，不是第二筆支出。
        success, message = asset_manager.add_account(
            user_id=user_id,
            bank_name="測試信用卡",
            account_type="credit_card",
            balance=Decimal("-1000"),
            currency="TWD",
        )
        assert success is True
        assert message == "成功新增帳戶"
        credit_card = asset_manager.find_asset_by_name(user_id, "測試信用卡")
        transaction_count_before_card_payment = connection.execute(
            select(func.count()).select_from(transactions_table)
        ).scalar_one()

        success, message = asset_manager.transfer(
            user_id,
            source_account_id,
            credit_card["id"],
            Decimal("1000"),
            note="繳信用卡費",
        )
        assert success is True
        assert message == "轉帳成功"
        source_balance_after_card_payment = connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == source_account_id)
        ).scalar_one()
        credit_balance_after_card_payment = connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == uuid.UUID(credit_card["id"]))
        ).scalar_one()
        assert source_balance_after_card_payment == Decimal("8880.0000")
        assert credit_balance_after_card_payment == Decimal("0.0000")
        assert connection.execute(select(func.count()).select_from(transactions_table)).scalar_one() == (
            transaction_count_before_card_payment
        )

        card_payment_transfer_id = connection.execute(
            select(transfers_table.c.id).where(transfers_table.c.note == "繳信用卡費")
        ).scalar_one()
        success, message = asset_manager.delete_transfer(user_id, card_payment_transfer_id)
        assert success is True
        assert message == "轉帳已刪除"
        assert connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == source_account_id)
        ).scalar_one() == Decimal("9880.0000")
        assert connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == uuid.UUID(credit_card["id"]))
        ).scalar_one() == Decimal("-1000.0000")

        daily_only_transactions = budget_manager.get_all_transactions(user_id)
        assert {transaction["category"] for transaction in daily_only_transactions} == {"便當"}

        monthly_report_before_included_trip = budget_manager.calculate_monthly_report_expenses(
            user_id,
            "2027-03",
        )
        assert monthly_report_before_included_trip["伙食"] == Decimal("450.2200")

        budget_manager.add_transaction(
            user_id=user_id,
            date="2027-03-03",
            item="測試收入",
            amount=Decimal("500"),
            transaction_type="income",
            budget_category="薪資",
            account_id=source_account_id,
            original_currency="TWD",
            exchange_rate=Decimal("1"),
        )
        source_balance_after_income = connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == source_account_id)
        ).scalar_one()
        assert source_balance_after_income == Decimal("10380.0000")

        income_transaction_id = connection.execute(
            select(transactions_table.c.id).where(transactions_table.c.title == "測試收入")
        ).scalar_one()
        budget_manager.delete_transaction(user_id, income_transaction_id)
        source_balance_after_income_delete = connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == source_account_id)
        ).scalar_one()
        assert source_balance_after_income_delete == Decimal("9880.0000")

        report_trip = trip_manager.create_trip(
            user_id=user_id,
            name="月報旅行",
            destination="Taipei",
            start_date="2027-03-04",
            end_date="2027-03-04",
            timezone_name="Asia/Taipei",
            base_currency="TWD",
            default_currency="TWD",
            include_in_monthly_report=True,
        )
        report_trip_members = trip_manager.list_trip_members(user_id=user_id, trip_id=report_trip["id"])
        report_owner_member = next(member for member in report_trip_members if member["role"] == "owner")
        assert report_owner_member["monthly_report_preference"] == "include"
        budget_manager.add_transaction(
            user_id=user_id,
            date="2027-03-04",
            item="旅行便當",
            amount=Decimal("300"),
            transaction_type="expense",
            budget_category="伙食",
            trip_id=uuid.UUID(report_trip["id"]),
            paid_by_member_id=uuid.UUID(report_owner_member["id"]),
            original_currency="TWD",
            exchange_rate=Decimal("1"),
            split_member_ids=[uuid.UUID(report_owner_member["id"])],
        )

        budget_summary = budget_manager.get_budget_summary(user_id, "2027-03")
        food_budget = next(item for item in budget_summary if item["category"] == "伙食")
        assert food_budget["spent"] == 750.22
        assert food_budget["budget"] == 10000
        assert food_budget["remaining"] == 9249.78

        daily_expenses = budget_manager.calculate_monthly_expenses(user_id, "2027-03")
        assert daily_expenses["伙食"] == Decimal("120.0000")

        monthly_report_expenses = budget_manager.calculate_monthly_report_expenses(user_id, "2027-03")
        assert monthly_report_expenses["伙食"] == Decimal("750.2200")

        monthly_report_transactions = budget_manager.get_all_transactions(user_id, monthly_report=True)
        assert {transaction["category"] for transaction in monthly_report_transactions} == {"拉麵加點", "便當", "旅行便當"}

        trend_data = budget_manager.get_transactions_by_category_over_time(user_id, interval="month")
        assert trend_data["labels"] == ["2027-03"]
        assert trend_data["datasets"][0]["label"] == "伙食"
        assert trend_data["datasets"][0]["data"] == [750.22]

        shared_trip = trip_manager.create_trip(
            user_id=user_id,
            name="分攤月報測試",
            destination="Taipei",
            start_date="2027-03-05",
            end_date="2027-03-05",
            timezone_name="Asia/Taipei",
            base_currency="TWD",
            default_currency="TWD",
            include_in_monthly_report=True,
        )
        shared_friend = trip_manager.add_external_member(
            user_id=user_id,
            trip_id=shared_trip["id"],
            display_name="朋友 B",
            role="viewer",
        )
        shared_members = trip_manager.list_trip_members(user_id=user_id, trip_id=shared_trip["id"])
        shared_owner_member = next(member for member in shared_members if member["role"] == "owner")
        budget_manager.add_transaction(
            user_id=user_id,
            date="2027-03-05",
            item="共享晚餐",
            amount=Decimal("1000"),
            transaction_type="expense",
            budget_category="伙食",
            trip_id=uuid.UUID(shared_trip["id"]),
            paid_by_member_id=uuid.UUID(shared_owner_member["id"]),
            original_currency="TWD",
            exchange_rate=Decimal("1"),
            split_member_ids=[uuid.UUID(shared_owner_member["id"]), uuid.UUID(shared_friend["id"])],
        )

        monthly_report_expenses = budget_manager.calculate_monthly_report_expenses(user_id, "2027-03")
        assert monthly_report_expenses["伙食"] == Decimal("1250.2200")

        monthly_report_transactions = budget_manager.get_all_transactions(user_id, monthly_report=True)
        shared_dinner = next(transaction for transaction in monthly_report_transactions if transaction["category"] == "共享晚餐")
        assert shared_dinner["amount"] == 500
        assert shared_dinner["converted_amount"] == 500

        split_count = connection.execute(
            select(transaction_splits_table.c.id).where(
                transaction_splits_table.c.transaction_id == transaction_id
            )
        ).all()

        assert len(split_count) == 2

        budget_manager.add_transaction(
            user_id=user_id,
            date="2027-03-05",
            item="自訂分帳晚餐",
            amount=Decimal("3000"),
            transaction_type="expense",
            budget_category="伙食",
            trip_id=trip_id,
            paid_by_member_id=owner_member_id,
            original_currency="JPY",
            exchange_rate=Decimal("0.22000000"),
            split_allocations=[
                {"trip_member_id": owner_member_id, "amount": Decimal("2500")},
                {"trip_member_id": friend_member_id, "amount": Decimal("500")},
            ],
        )
        custom_transaction_id = connection.execute(
            select(transactions_table.c.id).where(transactions_table.c.title == "自訂分帳晚餐")
        ).scalar_one()
        custom_splits = connection.execute(
            select(
                transaction_splits_table.c.trip_member_id,
                transaction_splits_table.c.split_method,
                transaction_splits_table.c.share_amount,
            ).where(transaction_splits_table.c.transaction_id == custom_transaction_id)
        ).all()
        assert {split.split_method for split in custom_splits} == {"custom"}
        assert {
            str(split.trip_member_id): split.share_amount for split in custom_splits
        } == {
            str(owner_member_id): Decimal("2500.0000"),
            str(friend_member_id): Decimal("500.0000"),
        }

        settlement_suggestions = budget_manager.get_trip_settlement_suggestions(user_id, trip_id)
        assert settlement_suggestions
        assert settlement_suggestions[0]["from_member_id"] == str(friend_member_id)
        assert settlement_suggestions[0]["to_member_id"] == str(owner_member_id)
        assert settlement_suggestions[0]["currency"] == "TWD"

        source_balance_before_settlement = connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == source_account_id)
        ).scalar_one()
        target_balance_before_settlement = connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == target_account_id)
        ).scalar_one()
        budget_manager.add_trip_settlement(
            user_id=user_id,
            trip_id=trip_id,
            from_member_id=friend_member_id,
            to_member_id=owner_member_id,
            amount=Decimal("100"),
            note="朋友先還一部分",
        )
        settlements = budget_manager.get_trip_settlements(user_id, trip_id)
        assert len(settlements) == 1
        assert settlements[0]["from_member_id"] == str(friend_member_id)
        assert settlements[0]["to_member_id"] == str(owner_member_id)
        assert settlements[0]["amount"] == 100

        source_balance_after_settlement = connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == source_account_id)
        ).scalar_one()
        target_balance_after_settlement = connection.execute(
            select(accounts_table.c.balance).where(accounts_table.c.id == target_account_id)
        ).scalar_one()
        assert source_balance_after_settlement == source_balance_before_settlement
        assert target_balance_after_settlement == target_balance_before_settlement

        reduced_suggestions = budget_manager.get_trip_settlement_suggestions(user_id, trip_id)
        assert reduced_suggestions[0]["amount"] == 340.0

        settlement_id = connection.execute(select(settlements_table.c.id)).scalar_one()
        budget_manager.delete_trip_settlement(user_id, trip_id, settlement_id)
        restored_suggestions = budget_manager.get_trip_settlement_suggestions(user_id, trip_id)
        assert restored_suggestions[0]["amount"] == 440.0
