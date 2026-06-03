import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, insert, select, update

from models.budget_manager import BudgetManager
from models.schema import (
    accounts_table,
    categories_table,
    metadata,
    transaction_splits_table,
    transactions_table,
    trip_members_table,
)
from models.seed_data import seed_reference_data
from models.trip_manager import TripManager
from models.user_manager import UserManager
from tests.test_schema_smoke import _get_test_database_url


def _reset_database(connection):
    metadata.drop_all(connection)
    metadata.create_all(connection)
    seed_reference_data(connection)


def _create_test_user(connection, provider_user_id, display_name):
    return UserManager(connection).get_or_create_user_for_identity(
        provider="line",
        provider_user_id=provider_user_id,
        display_name=display_name,
        provider_email=f"{provider_user_id}@example.test",
    )


def _create_account(connection, user_id, name, account_type, currency, balance=None, track_balance=True):
    account_id = uuid.uuid4()
    connection.execute(
        accounts_table.insert().values(
            id=account_id,
            user_id=user_id,
            name=name,
            type=account_type,
            currency=currency,
            track_balance=track_balance,
            balance=Decimal(str(balance)) if balance is not None else None,
        )
    )
    return account_id


def _get_balance(connection, account_id):
    return connection.execute(
        select(accounts_table.c.balance).where(accounts_table.c.id == account_id)
    ).scalar_one()


def _trip_members_by_name(trip_manager, user_id, trip_id):
    return {
        member["display_name"]: member
        for member in trip_manager.list_trip_members(user_id=user_id, trip_id=trip_id)
    }


def test_phase5_mvp_handles_10_person_trip_flow_and_edge_cases():
    engine = create_engine(_get_test_database_url(), future=True)

    with engine.begin() as connection:
        _reset_database(connection)

        owner = _create_test_user(connection, "U-phase5-owner", "我")
        owner_id = owner["id"]
        twd_bank_id = _create_account(connection, owner_id, "台幣銀行", "bank", "TWD", 50000)
        twd_cash_id = _create_account(connection, owner_id, "台幣現金", "cash", "TWD", 10000)
        jpy_cash_id = _create_account(connection, owner_id, "日幣現金", "cash", "JPY", 80000)
        credit_card_id = _create_account(
            connection,
            owner_id,
            "信用卡",
            "credit_card",
            "TWD",
            None,
            track_balance=False,
        )

        trip_manager = TripManager(connection)
        budget_manager = BudgetManager(connection)

        trip = trip_manager.create_trip(
            user_id=owner_id,
            name="日本關西 10 人測試",
            destination="Osaka",
            start_date="2027-03-01",
            end_date="2027-03-07",
            timezone_name="Asia/Tokyo",
            base_currency="TWD",
            default_currency="JPY",
            include_in_monthly_report=True,
        )
        for name in ["Amy", "Ben", "Cara", "Duke", "Eva", "Finn", "Gina", "Hank", "Ivy"]:
            trip_manager.add_external_member(owner_id, trip["id"], name, role="viewer")
        removable_member = trip_manager.add_external_member(owner_id, trip["id"], "臨時旅伴", role="viewer")
        removed_member = trip_manager.remove_member(owner_id, trip["id"], removable_member["id"])
        assert removed_member["status"] == "removed"

        members = _trip_members_by_name(trip_manager, owner_id, trip["id"])
        assert len(members) == 10
        owner_member_id = uuid.UUID(members["我"]["id"])
        amy_member_id = uuid.UUID(members["Amy"]["id"])
        all_member_ids = [uuid.UUID(member["id"]) for member in members.values()]

        success, message = budget_manager.add_transaction(
            user_id=owner_id,
            date="2027-03-02",
            item="拉麵",
            amount=Decimal("1200"),
            transaction_type="expense",
            budget_category="伙食",
            account_id=jpy_cash_id,
            trip_id=uuid.UUID(trip["id"]),
            paid_by_member_id=owner_member_id,
            merchant="一蘭",
            original_currency="JPY",
            exchange_rate=Decimal("0.22000000"),
            timezone_name="Asia/Tokyo",
            split_member_ids=all_member_ids,
        )
        assert success is True
        assert message == "交易新增成功"
        assert _get_balance(connection, jpy_cash_id) == Decimal("78800.0000")

        ramen_transaction_id = budget_manager.last_created_transaction_id
        ramen_splits = connection.execute(
            select(transaction_splits_table.c.share_amount).where(
                transaction_splits_table.c.transaction_id == ramen_transaction_id
            )
        ).scalars().all()
        assert len(ramen_splits) == 10
        assert set(ramen_splits) == {Decimal("120.0000")}

        budget_manager.add_transaction(
            user_id=owner_id,
            date="2027-03-02",
            item="便利商店",
            amount=Decimal("1001"),
            transaction_type="expense",
            budget_category="伙食",
            trip_id=uuid.UUID(trip["id"]),
            paid_by_member_id=owner_member_id,
            original_currency="JPY",
            exchange_rate=Decimal("0.22000000"),
            split_member_ids=all_member_ids,
        )
        convenience_transaction_id = budget_manager.last_created_transaction_id
        owner_remainder_share = connection.execute(
            select(transaction_splits_table.c.share_amount).where(
                transaction_splits_table.c.transaction_id == convenience_transaction_id,
                transaction_splits_table.c.trip_member_id == owner_member_id,
            )
        ).scalar_one()
        other_shares = connection.execute(
            select(transaction_splits_table.c.share_amount).where(
                transaction_splits_table.c.transaction_id == convenience_transaction_id,
                transaction_splits_table.c.trip_member_id != owner_member_id,
            )
        ).scalars().all()
        assert owner_remainder_share == Decimal("101.0000")
        assert set(other_shares) == {Decimal("100.0000")}

        jpy_balance_before_friend_payment = _get_balance(connection, jpy_cash_id)
        budget_manager.add_transaction(
            user_id=owner_id,
            date="2027-03-03",
            item="計程車",
            amount=Decimal("3000"),
            transaction_type="expense",
            budget_category="交通",
            trip_id=uuid.UUID(trip["id"]),
            paid_by_member_id=amy_member_id,
            original_currency="JPY",
            exchange_rate=Decimal("0.22000000"),
            split_member_ids=all_member_ids,
        )
        assert _get_balance(connection, jpy_cash_id) == jpy_balance_before_friend_payment

        with pytest.raises(ValueError, match="只有自己付款時才可連動自己的帳戶"):
            budget_manager.add_transaction(
                user_id=owner_id,
                date="2027-03-03",
                item="朋友刷卡但誤選我的帳戶",
                amount=Decimal("3000"),
                transaction_type="expense",
                budget_category="交通",
                account_id=jpy_cash_id,
                trip_id=uuid.UUID(trip["id"]),
                paid_by_member_id=amy_member_id,
                original_currency="JPY",
                exchange_rate=Decimal("0.22000000"),
                split_member_ids=all_member_ids,
            )

        custom_allocations = [
            {"trip_member_id": member_id, "amount": Decimal("1000")}
            for member_id in all_member_ids
        ]
        budget_manager.add_transaction(
            user_id=owner_id,
            date="2027-03-04",
            item="燒肉",
            amount=Decimal("10000"),
            transaction_type="expense",
            budget_category="伙食",
            account_id=jpy_cash_id,
            trip_id=uuid.UUID(trip["id"]),
            paid_by_member_id=owner_member_id,
            merchant="敘敘苑",
            original_currency="JPY",
            exchange_rate=Decimal("0.22000000"),
            split_allocations=custom_allocations,
        )
        assert _get_balance(connection, jpy_cash_id) == Decimal("68800.0000")

        with pytest.raises(ValueError, match="金額必須大於0"):
            budget_manager.add_transaction(
                user_id=owner_id,
                date="2027-03-04",
                item="零元測試",
                amount=Decimal("0"),
                transaction_type="expense",
                budget_category="伙食",
            )

        with pytest.raises(ValueError, match="exchange_rate 必須大於0"):
            budget_manager.add_transaction(
                user_id=owner_id,
                date="2027-03-04",
                item="匯率為零",
                amount=Decimal("100"),
                transaction_type="expense",
                budget_category="伙食",
                trip_id=uuid.UUID(trip["id"]),
                paid_by_member_id=owner_member_id,
                original_currency="JPY",
                exchange_rate=Decimal("0"),
                split_member_ids=all_member_ids,
            )

        with pytest.raises(ValueError, match="交易金額小數位超過幣別允許位數"):
            budget_manager.add_transaction(
                user_id=owner_id,
                date="2027-03-04",
                item="日幣小數",
                amount=Decimal("100.50"),
                transaction_type="expense",
                budget_category="伙食",
                trip_id=uuid.UUID(trip["id"]),
                paid_by_member_id=owner_member_id,
                original_currency="JPY",
                exchange_rate=Decimal("0.22000000"),
                split_member_ids=all_member_ids,
            )

        with pytest.raises(ValueError, match="自訂分帳合計必須等於交易金額"):
            budget_manager.add_transaction(
                user_id=owner_id,
                date="2027-03-04",
                item="自訂分帳少填",
                amount=Decimal("1000"),
                transaction_type="expense",
                budget_category="伙食",
                trip_id=uuid.UUID(trip["id"]),
                paid_by_member_id=owner_member_id,
                original_currency="JPY",
                exchange_rate=Decimal("0.22000000"),
                split_allocations=[
                    {"trip_member_id": owner_member_id, "amount": Decimal("500")},
                    {"trip_member_id": amy_member_id, "amount": Decimal("400")},
                ],
            )

        with pytest.raises(ValueError, match="此旅伴已有付款、分攤或結算紀錄"):
            trip_manager.remove_member(owner_id, trip["id"], amy_member_id)

        budget_manager.add_transaction(
            user_id=owner_id,
            date="2027-03-05",
            item="午餐",
            amount=Decimal("150"),
            transaction_type="expense",
            budget_category="伙食",
            account_id=twd_cash_id,
            original_currency="TWD",
            exchange_rate=Decimal("1"),
        )
        budget_manager.add_transaction(
            user_id=owner_id,
            date="2027-03-05",
            item="薪資",
            amount=Decimal("68000"),
            transaction_type="income",
            budget_category="薪資",
            account_id=twd_bank_id,
            original_currency="TWD",
            exchange_rate=Decimal("1"),
        )
        budget_manager.add_transaction(
            user_id=owner_id,
            date="2027-03-05",
            item="訂閱費",
            amount=Decimal("390"),
            transaction_type="expense",
            budget_category="訂閱",
            account_id=credit_card_id,
            original_currency="TWD",
            exchange_rate=Decimal("1"),
        )
        assert _get_balance(connection, twd_cash_id) == Decimal("9850.0000")
        assert _get_balance(connection, twd_bank_id) == Decimal("118000.0000")
        assert _get_balance(connection, credit_card_id) is None

        daily_transactions = budget_manager.get_all_transactions(owner_id)
        assert {transaction["category"] for transaction in daily_transactions} == {"午餐", "薪資", "訂閱費"}

        monthly_report_transactions = budget_manager.get_all_transactions(owner_id, monthly_report=True)
        assert {"拉麵", "便利商店", "計程車", "燒肉", "午餐", "薪資", "訂閱費"} == {
            transaction["category"] for transaction in monthly_report_transactions
        }

        non_report_trip = trip_manager.create_trip(
            user_id=owner_id,
            name="韓國週末測試",
            destination="Seoul",
            start_date="2027-04-10",
            end_date="2027-04-13",
            timezone_name="Asia/Seoul",
            base_currency="TWD",
            default_currency="KRW",
            include_in_monthly_report=False,
        )
        non_report_members = _trip_members_by_name(trip_manager, owner_id, non_report_trip["id"])
        budget_manager.add_transaction(
            user_id=owner_id,
            date="2027-04-11",
            item="韓國地鐵",
            amount=Decimal("1500"),
            transaction_type="expense",
            budget_category="交通",
            trip_id=uuid.UUID(non_report_trip["id"]),
            paid_by_member_id=uuid.UUID(non_report_members["我"]["id"]),
            original_currency="KRW",
            exchange_rate=Decimal("0.02300000"),
            split_member_ids=[uuid.UUID(non_report_members["我"]["id"])],
        )
        assert all(
            transaction["category"] != "韓國地鐵"
            for transaction in budget_manager.get_all_transactions(owner_id, monthly_report=True)
        )

        suggestions = budget_manager.get_trip_settlement_suggestions(owner_id, trip["id"])
        assert suggestions
        first_suggestion = suggestions[0]
        budget_manager.add_trip_settlement(
            user_id=owner_id,
            trip_id=uuid.UUID(trip["id"]),
            from_member_id=uuid.UUID(first_suggestion["from_member_id"]),
            to_member_id=uuid.UUID(first_suggestion["to_member_id"]),
            amount=Decimal(str(first_suggestion["amount"])) / Decimal("2"),
            note="先還一半",
        )
        assert budget_manager.get_trip_settlements(owner_id, trip["id"])

        balance_before_delete = _get_balance(connection, jpy_cash_id)
        budget_manager.delete_transaction(owner_id, ramen_transaction_id)
        assert _get_balance(connection, jpy_cash_id) == balance_before_delete + Decimal("1200.0000")
        deleted_transaction = connection.execute(
            select(transactions_table.c.deleted_at).where(transactions_table.c.id == ramen_transaction_id)
        ).scalar_one()
        assert deleted_transaction is not None


def test_bound_member_can_see_shared_trip_transactions_without_account_leakage():
    engine = create_engine(_get_test_database_url(), future=True)

    with engine.begin() as connection:
        _reset_database(connection)

        owner = _create_test_user(connection, "U-phase5-owner-visibility", "Owner")
        invited_user = _create_test_user(connection, "U-phase5-invited", "Amy")
        owner_id = owner["id"]
        invited_user_id = invited_user["id"]

        trip_manager = TripManager(connection)
        budget_manager = BudgetManager(connection)
        trip = trip_manager.create_trip(
            user_id=owner_id,
            name="多人可見性測試",
            destination="Tokyo",
            start_date="2027-05-01",
            end_date="2027-05-05",
            timezone_name="Asia/Tokyo",
            base_currency="TWD",
            default_currency="JPY",
        )
        amy_member = trip_manager.add_external_member(owner_id, trip["id"], "Amy", role="editor")
        connection.execute(
            update(trip_members_table)
            .where(trip_members_table.c.id == uuid.UUID(amy_member["id"]))
            .values(user_id=invited_user_id)
        )

        owner_members = _trip_members_by_name(trip_manager, owner_id, trip["id"])
        budget_manager.add_transaction(
            user_id=owner_id,
            date="2027-05-02",
            item="共同晚餐",
            amount=Decimal("5000"),
            transaction_type="expense",
            budget_category="伙食",
            trip_id=uuid.UUID(trip["id"]),
            paid_by_member_id=uuid.UUID(owner_members["Owner"]["id"]),
            original_currency="JPY",
            exchange_rate=Decimal("0.22000000"),
            split_member_ids=[uuid.UUID(member["id"]) for member in owner_members.values()],
        )

        invited_trips = trip_manager.list_trips(invited_user_id)
        assert {item["id"] for item in invited_trips} == {trip["id"]}
        invited_trip = trip_manager.get_trip(invited_user_id, trip["id"])
        assert invited_trip["current_member_id"] == amy_member["id"]

        invited_transactions = budget_manager.get_all_transactions(invited_user_id, trip_id=uuid.UUID(trip["id"]))
        assert [transaction["category"] for transaction in invited_transactions] == ["共同晚餐"]
        assert invited_transactions[0]["created_by_user_id"] == str(owner_id)
        assert invited_transactions[0]["can_edit"] is False
        assert invited_transactions[0]["can_delete"] is False
        assert invited_transactions[0]["account_id"] is None


def test_reusable_trip_invite_join_rejoin_limit_and_close():
    engine = create_engine(_get_test_database_url(), future=True)

    with engine.begin() as connection:
        _reset_database(connection)

        owner = _create_test_user(connection, "U-phase5-invite-owner", "Owner")
        owner_id = owner["id"]
        trip_manager = TripManager(connection)
        trip = trip_manager.create_trip(
            user_id=owner_id,
            name="邀請連結測試",
            destination="Kyoto",
            start_date="2027-06-01",
            end_date="2027-06-05",
            timezone_name="Asia/Tokyo",
            base_currency="TWD",
            default_currency="JPY",
        )

        invite = trip_manager.create_invite(owner_id, trip["id"])
        assert invite["role"] == "editor"
        assert invite["status"] == "active"
        assert invite["token"]
        assert "token_hash" not in invite

        with pytest.raises(ValueError, match="已有有效邀請連結"):
            trip_manager.create_invite(owner_id, trip["id"])

        amy = _create_test_user(connection, "U-phase5-invite-amy", "Amy")
        accepted = trip_manager.accept_invite(amy["id"], invite["token"])
        assert accepted["member"]["role"] == "editor"
        assert accepted["member"]["user_id"] == str(amy["id"])
        assert accepted["already_joined"] is False

        accepted_again = trip_manager.accept_invite(amy["id"], invite["token"])
        assert accepted_again["already_joined"] is True

        left_member = trip_manager.leave_trip(amy["id"], trip["id"])
        assert left_member["status"] == "removed"
        rejoined = trip_manager.accept_invite(amy["id"], invite["token"])
        assert rejoined["member"]["id"] == left_member["id"]
        assert rejoined["member"]["status"] == "active"

        for index in range(13):
            user = _create_test_user(connection, f"U-phase5-member-{index}", f"Member {index}")
            trip_manager.accept_invite(user["id"], invite["token"])

        overflow_user = _create_test_user(connection, "U-phase5-overflow", "Overflow")
        with pytest.raises(ValueError, match="成員已達上限"):
            trip_manager.accept_invite(overflow_user["id"], invite["token"])

        trip_manager.close_invite(owner_id, trip["id"])
        with pytest.raises(ValueError, match="已關閉"):
            trip_manager.accept_invite(overflow_user["id"], invite["token"])


def test_trip_member_roles_control_transaction_mutations():
    engine = create_engine(_get_test_database_url(), future=True)

    with engine.begin() as connection:
        _reset_database(connection)

        owner = _create_test_user(connection, "U-phase5-role-owner", "Owner")
        editor = _create_test_user(connection, "U-phase5-role-editor", "Editor")
        viewer = _create_test_user(connection, "U-phase5-role-viewer", "Viewer")
        owner_id = owner["id"]

        trip_manager = TripManager(connection)
        budget_manager = BudgetManager(connection)
        trip = trip_manager.create_trip(
            user_id=owner_id,
            name="權限測試",
            destination="Tokyo",
            start_date="2027-07-01",
            end_date="2027-07-03",
            timezone_name="Asia/Tokyo",
            base_currency="TWD",
            default_currency="JPY",
        )
        invite = trip_manager.create_invite(owner_id, trip["id"])
        editor_join = trip_manager.accept_invite(editor["id"], invite["token"])
        viewer_join = trip_manager.accept_invite(viewer["id"], invite["token"])
        trip_manager.update_member_role(owner_id, trip["id"], viewer_join["member"]["id"], "viewer")

        owner_members = _trip_members_by_name(trip_manager, owner_id, trip["id"])
        owner_member_id = uuid.UUID(owner_members["Owner"]["id"])
        member_ids = [uuid.UUID(member["id"]) for member in owner_members.values()]

        budget_manager.add_transaction(
            user_id=owner_id,
            date="2027-07-01",
            item="Owner 晚餐",
            amount=Decimal("3000"),
            transaction_type="expense",
            budget_category="伙食",
            trip_id=uuid.UUID(trip["id"]),
            paid_by_member_id=owner_member_id,
            original_currency="JPY",
            exchange_rate=Decimal("0.22000000"),
            split_member_ids=member_ids,
        )
        owner_transaction_id = budget_manager.last_created_transaction_id

        with pytest.raises(ValueError, match="不可編輯"):
            budget_manager.update_transaction(
                user_id=editor["id"],
                transaction_id=owner_transaction_id,
                date="2027-07-01",
                item="Editor 不可改",
                amount=Decimal("3000"),
                transaction_type="expense",
                budget_category="伙食",
                paid_by_member_id=owner_member_id,
                original_currency="JPY",
                exchange_rate=Decimal("0.22000000"),
                split_member_ids=member_ids,
            )

        editor_trip = trip_manager.get_trip(editor["id"], trip["id"])
        editor_member_id = uuid.UUID(editor_trip["current_member_id"])
        budget_manager.add_transaction(
            user_id=editor["id"],
            date="2027-07-02",
            item="Editor 午餐",
            amount=Decimal("1200"),
            transaction_type="expense",
            budget_category="伙食",
            trip_id=uuid.UUID(trip["id"]),
            paid_by_member_id=editor_member_id,
            original_currency="JPY",
            exchange_rate=Decimal("0.22000000"),
            split_member_ids=member_ids,
            review_status="pending",
        )
        editor_transaction_id = budget_manager.last_created_transaction_id
        editor_detail = budget_manager.get_transaction_detail(editor["id"], editor_transaction_id)
        assert editor_detail["can_edit"] is True
        assert editor_detail["review_status"] == "pending"

        budget_manager.update_transaction(
            user_id=owner_id,
            transaction_id=editor_transaction_id,
            date="2027-07-02",
            item="Owner 管理修正",
            amount=Decimal("1300"),
            transaction_type="expense",
            budget_category="伙食",
            paid_by_member_id=editor_member_id,
            original_currency="JPY",
            exchange_rate=Decimal("0.22000000"),
            split_member_ids=member_ids,
            review_status="confirmed",
        )
        updated_detail = budget_manager.get_transaction_detail(owner_id, editor_transaction_id)
        assert updated_detail["category"] == "Owner 管理修正"
        assert updated_detail["updated_by_user_id"] == str(owner_id)

        trip_manager.update_member_role(owner_id, trip["id"], editor_join["member"]["id"], "viewer")
        downgraded_detail = budget_manager.get_transaction_detail(editor["id"], editor_transaction_id)
        assert downgraded_detail["can_edit"] is False
        assert downgraded_detail["can_delete"] is False
        with pytest.raises(ValueError, match="不可編輯"):
            budget_manager.update_transaction(
                user_id=editor["id"],
                transaction_id=editor_transaction_id,
                date="2027-07-02",
                item="Viewer 不可再改自己的舊交易",
                amount=Decimal("1300"),
                transaction_type="expense",
                budget_category="伙食",
                paid_by_member_id=editor_member_id,
                original_currency="JPY",
                exchange_rate=Decimal("0.22000000"),
                split_member_ids=member_ids,
            )
        with pytest.raises(ValueError, match="不可刪除"):
            budget_manager.delete_transaction(editor["id"], editor_transaction_id)
        trip_manager.update_member_role(owner_id, trip["id"], editor_join["member"]["id"], "editor")

        viewer_trip = trip_manager.get_trip(viewer["id"], trip["id"])
        with pytest.raises(ValueError, match="不可新增"):
            budget_manager.add_transaction(
                user_id=viewer["id"],
                date="2027-07-02",
                item="Viewer 不可新增",
                amount=Decimal("500"),
                transaction_type="expense",
                budget_category="伙食",
                trip_id=uuid.UUID(trip["id"]),
                paid_by_member_id=uuid.UUID(viewer_trip["current_member_id"]),
                original_currency="JPY",
                exchange_rate=Decimal("0.22000000"),
                split_member_ids=member_ids,
            )

        budget_manager.delete_transaction(owner_id, editor_transaction_id)
        deleted_by = connection.execute(
            select(transactions_table.c.deleted_by_user_id).where(transactions_table.c.id == editor_transaction_id)
        ).scalar_one()
        assert deleted_by == owner_id


def test_settlement_confirmation_is_limited_to_owner_or_debtor():
    engine = create_engine(_get_test_database_url(), future=True)

    with engine.begin() as connection:
        _reset_database(connection)

        owner = _create_test_user(connection, "U-phase5-settlement-owner", "Owner")
        debtor = _create_test_user(connection, "U-phase5-settlement-debtor", "Debtor")
        bystander = _create_test_user(connection, "U-phase5-settlement-bystander", "Bystander")
        owner_id = owner["id"]

        trip_manager = TripManager(connection)
        budget_manager = BudgetManager(connection)
        trip = trip_manager.create_trip(
            user_id=owner_id,
            name="結算權限測試",
            destination="Seoul",
            start_date="2027-08-01",
            end_date="2027-08-03",
            timezone_name="Asia/Seoul",
            base_currency="TWD",
            default_currency="KRW",
        )
        invite = trip_manager.create_invite(owner_id, trip["id"])
        debtor_join = trip_manager.accept_invite(debtor["id"], invite["token"])
        bystander_join = trip_manager.accept_invite(bystander["id"], invite["token"])

        owner_members = _trip_members_by_name(trip_manager, owner_id, trip["id"])
        owner_member_id = uuid.UUID(owner_members["Owner"]["id"])
        debtor_member_id = uuid.UUID(debtor_join["member"]["id"])
        bystander_member_id = uuid.UUID(bystander_join["member"]["id"])

        budget_manager.add_transaction(
            user_id=owner_id,
            date="2027-08-01",
            item="Owner 代墊餐費",
            amount=Decimal("3000"),
            transaction_type="expense",
            budget_category="伙食",
            trip_id=uuid.UUID(trip["id"]),
            paid_by_member_id=owner_member_id,
            original_currency="KRW",
            exchange_rate=Decimal("0.02300000"),
            split_allocations=[
                {"trip_member_id": str(debtor_member_id), "amount": Decimal("3000")},
            ],
        )

        suggestions_for_debtor = budget_manager.get_trip_settlement_suggestions(debtor["id"], trip["id"])
        suggestions_for_bystander = budget_manager.get_trip_settlement_suggestions(bystander["id"], trip["id"])
        suggestion = suggestions_for_debtor[0]
        assert suggestion["from_member_id"] == str(debtor_member_id)
        assert suggestion["can_confirm"] is True
        assert suggestions_for_bystander[0]["can_confirm"] is False

        with pytest.raises(ValueError, match="付款方本人"):
            budget_manager.add_trip_settlement(
                bystander["id"],
                trip["id"],
                suggestion["from_member_id"],
                suggestion["to_member_id"],
                suggestion["amount"],
            )

        budget_manager.add_trip_settlement(
            debtor["id"],
            trip["id"],
            suggestion["from_member_id"],
            suggestion["to_member_id"],
            suggestion["amount"],
        )
        settlement = budget_manager.get_trip_settlements(bystander["id"], trip["id"])[0]
        assert settlement["can_void"] is False
        with pytest.raises(ValueError, match="結算記錄者"):
            budget_manager.delete_trip_settlement(bystander["id"], trip["id"], settlement["id"])

        owner_settlement = budget_manager.get_trip_settlements(owner_id, trip["id"])[0]
        assert owner_settlement["can_void"] is True
