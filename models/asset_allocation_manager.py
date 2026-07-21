from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import delete, desc, func, insert, select, update

from .schema import (
    accounts_table,
    currencies_table,
    holding_cost_entries_table,
    holdings_table,
    portfolio_snapshot_items_table,
    portfolio_snapshots_table,
    portfolios_table,
    transfers_table,
)


MONEY_QUANTUM = Decimal("0.0001")
WEIGHT_TOTAL = Decimal("1.00000000")


class AllocationNotFoundError(ValueError):
    pass


class AssetAllocationManager:
    """管理使用者自行維護的投資組合、成本與手動快照。"""

    def __init__(self, db_session):
        self.db_session = db_session

    def list_portfolios(self, user_id):
        rows = self.db_session.execute(
            select(portfolios_table)
            .where(
                portfolios_table.c.user_id == self._uuid(user_id, "user_id"),
                portfolios_table.c.deleted_at.is_(None),
            )
            .order_by(portfolios_table.c.created_at)
        ).all()
        return [self._serialize(dict(row._mapping)) for row in rows]

    def get_portfolio(self, user_id, portfolio_id):
        portfolio = self._get_portfolio(user_id, portfolio_id)
        holdings = self._list_holdings(portfolio["id"])
        costs_by_holding = self._costs_by_holding([item["id"] for item in holdings])
        for holding in holdings:
            holding["cost_entries"] = costs_by_holding.get(holding["id"], [])
            holding["recorded_cost"] = float(
                sum(
                    Decimal(str(item["amount"]))
                    for item in holding["cost_entries"]
                )
            )

        result = self._serialize(portfolio)
        result["holdings"] = holdings
        result["snapshots"] = self.list_snapshots(user_id, portfolio_id)
        return result

    def create_portfolio(self, user_id, name, base_currency):
        parsed_user_id = self._uuid(user_id, "user_id")
        normalized_name = self._text(name, "Portfolio 名稱", 100)
        currency = self._currency(base_currency)
        self._ensure_currency_exists(currency)
        self._ensure_unique_portfolio_name(parsed_user_id, normalized_name, currency)

        row = self.db_session.execute(
            insert(portfolios_table)
            .values(
                user_id=parsed_user_id,
                name=normalized_name,
                base_currency=currency,
            )
            .returning(portfolios_table)
        ).first()
        return self._serialize(dict(row._mapping))

    def update_portfolio(self, user_id, portfolio_id, **changes):
        portfolio = self._get_portfolio(user_id, portfolio_id)
        values = {}
        next_name = portfolio["name"]
        next_currency = portfolio["base_currency"]

        if "name" in changes:
            next_name = self._text(changes["name"], "Portfolio 名稱", 100)
            values["name"] = next_name
        if "base_currency" in changes:
            next_currency = self._currency(changes["base_currency"])
            self._ensure_currency_exists(next_currency)
            if next_currency != portfolio["base_currency"] and self._portfolio_has_holdings(portfolio["id"]):
                raise ValueError("已有 Holding 的 Portfolio 不可變更基準幣別")
            values["base_currency"] = next_currency
        if "is_active" in changes:
            is_active = self._boolean(changes["is_active"], "is_active")
            values["is_active"] = is_active
            values["archived_at"] = None if is_active else datetime.now(timezone.utc)

        if not values:
            raise ValueError("缺少可更新欄位")
        self._ensure_unique_portfolio_name(
            portfolio["user_id"],
            next_name,
            next_currency,
            exclude_id=portfolio["id"],
        )
        values["updated_at"] = datetime.now(timezone.utc)
        row = self.db_session.execute(
            update(portfolios_table)
            .where(portfolios_table.c.id == portfolio["id"])
            .values(**values)
            .returning(portfolios_table)
        ).first()
        return self._serialize(dict(row._mapping))

    def delete_portfolio(self, user_id, portfolio_id):
        portfolio = self._get_portfolio(user_id, portfolio_id)
        now = datetime.now(timezone.utc)
        self.db_session.execute(
            update(portfolios_table)
            .where(portfolios_table.c.id == portfolio["id"])
            .values(
                is_active=False,
                archived_at=now,
                deleted_at=now,
                purge_after=now + timedelta(days=30),
                updated_at=now,
            )
        )
        return True

    def create_holding(
        self,
        user_id,
        portfolio_id,
        account_id,
        name,
        symbol=None,
        asset_class=None,
        target_weight=None,
    ):
        portfolio = self._get_portfolio(user_id, portfolio_id)
        account = self._investment_account(user_id, account_id, portfolio["base_currency"])
        normalized_name = self._text(name, "Holding 名稱", 100)
        self._ensure_unique_holding_name(portfolio["id"], account["id"], normalized_name)

        row = self.db_session.execute(
            insert(holdings_table)
            .values(
                portfolio_id=portfolio["id"],
                account_id=account["id"],
                name=normalized_name,
                symbol=self._optional_text(symbol, 50, uppercase=True),
                asset_class=self._optional_text(asset_class, 50),
                target_weight=self._weight(target_weight),
            )
            .returning(holdings_table)
        ).first()
        return self._serialize(dict(row._mapping))

    def update_holding(self, user_id, holding_id, **changes):
        holding, portfolio = self._get_holding(user_id, holding_id)
        values = {}
        next_account_id = holding["account_id"]
        next_name = holding["name"]

        if "account_id" in changes:
            account = self._investment_account(
                user_id,
                changes["account_id"],
                portfolio["base_currency"],
            )
            next_account_id = account["id"]
            if next_account_id != holding["account_id"] and self._holding_has_history(holding["id"]):
                raise ValueError("已有成本或 Snapshot 的 Holding 不可變更所屬帳戶")
            values["account_id"] = next_account_id
        if "name" in changes:
            next_name = self._text(changes["name"], "Holding 名稱", 100)
            values["name"] = next_name
        if "symbol" in changes:
            values["symbol"] = self._optional_text(changes["symbol"], 50, uppercase=True)
        if "asset_class" in changes:
            values["asset_class"] = self._optional_text(changes["asset_class"], 50)
        if "target_weight" in changes:
            values["target_weight"] = self._weight(changes["target_weight"])
        if "is_active" in changes:
            is_active = self._boolean(changes["is_active"], "is_active")
            values["is_active"] = is_active
            values["archived_at"] = None if is_active else datetime.now(timezone.utc)

        if not values:
            raise ValueError("缺少可更新欄位")
        self._ensure_unique_holding_name(
            portfolio["id"],
            next_account_id,
            next_name,
            exclude_id=holding["id"],
        )
        values["updated_at"] = datetime.now(timezone.utc)
        row = self.db_session.execute(
            update(holdings_table)
            .where(holdings_table.c.id == holding["id"])
            .values(**values)
            .returning(holdings_table)
        ).first()
        return self._serialize(dict(row._mapping))

    def delete_holding(self, user_id, holding_id):
        holding, _ = self._get_holding(user_id, holding_id)
        now = datetime.now(timezone.utc)
        values = {
            "is_active": False,
            "archived_at": now,
            "updated_at": now,
        }
        if not self._holding_has_history(holding["id"]):
            values.update(
                deleted_at=now,
                purge_after=now + timedelta(days=30),
            )
        self.db_session.execute(
            update(holdings_table)
            .where(holdings_table.c.id == holding["id"])
            .values(**values)
        )
        return True

    def create_cost_entry(
        self,
        user_id,
        holding_id,
        entry_type,
        amount,
        occurred_on,
        source_transfer_id=None,
        note=None,
    ):
        holding, portfolio = self._get_holding(user_id, holding_id)
        normalized_type = self._entry_type(entry_type)
        parsed_amount = self._positive_money(amount, "投入成本")
        transfer = self._validate_cost_source(
            user_id,
            holding,
            portfolio,
            normalized_type,
            source_transfer_id,
            parsed_amount,
        )
        row = self.db_session.execute(
            insert(holding_cost_entries_table)
            .values(
                holding_id=holding["id"],
                source_transfer_id=transfer["id"] if transfer else None,
                entry_type=normalized_type,
                amount=parsed_amount,
                currency=portfolio["base_currency"],
                occurred_on=self._date(occurred_on),
                note=self._optional_text(note, 500),
            )
            .returning(holding_cost_entries_table)
        ).first()
        return self._serialize(dict(row._mapping))

    def update_cost_entry(self, user_id, cost_entry_id, **changes):
        entry, holding, portfolio = self._get_cost_entry(user_id, cost_entry_id)
        entry_type = self._entry_type(changes.get("entry_type", entry["entry_type"]))
        amount = self._positive_money(changes.get("amount", entry["amount"]), "投入成本")
        source_transfer_id = changes.get("source_transfer_id", entry["source_transfer_id"])
        transfer = self._validate_cost_source(
            user_id,
            holding,
            portfolio,
            entry_type,
            source_transfer_id,
            amount,
            exclude_entry_id=entry["id"],
        )
        values = {
            "entry_type": entry_type,
            "source_transfer_id": transfer["id"] if transfer else None,
            "amount": amount,
            "currency": portfolio["base_currency"],
            "occurred_on": self._date(changes.get("occurred_on", entry["occurred_on"])),
            "note": self._optional_text(changes.get("note", entry["note"]), 500),
            "updated_at": datetime.now(timezone.utc),
        }
        row = self.db_session.execute(
            update(holding_cost_entries_table)
            .where(holding_cost_entries_table.c.id == entry["id"])
            .values(**values)
            .returning(holding_cost_entries_table)
        ).first()
        return self._serialize(dict(row._mapping))

    def delete_cost_entry(self, user_id, cost_entry_id):
        entry, _, _ = self._get_cost_entry(user_id, cost_entry_id)
        now = datetime.now(timezone.utc)
        self.db_session.execute(
            update(holding_cost_entries_table)
            .where(holding_cost_entries_table.c.id == entry["id"])
            .values(
                deleted_at=now,
                purge_after=now + timedelta(days=30),
                updated_at=now,
            )
        )
        return True

    def list_snapshots(self, user_id, portfolio_id):
        portfolio = self._get_portfolio(user_id, portfolio_id)
        rows = self.db_session.execute(
            select(portfolio_snapshots_table)
            .where(
                portfolio_snapshots_table.c.portfolio_id == portfolio["id"],
                portfolio_snapshots_table.c.deleted_at.is_(None),
            )
            .order_by(desc(portfolio_snapshots_table.c.snapshot_date))
        ).all()
        snapshots = []
        for row in rows:
            snapshot = dict(row._mapping)
            items = self.db_session.execute(
                select(portfolio_snapshot_items_table).where(
                    portfolio_snapshot_items_table.c.snapshot_id == snapshot["id"]
                )
            ).all()
            serialized = self._serialize(snapshot)
            serialized["items"] = [self._serialize(dict(item._mapping)) for item in items]
            serialized["total_value"] = float(
                sum(Decimal(str(item._mapping["value"])) for item in items)
            )
            snapshots.append(serialized)
        return snapshots

    def create_or_update_snapshot(self, user_id, portfolio_id, snapshot_date, items, note=None):
        portfolio = self._get_portfolio(user_id, portfolio_id)
        active_holdings = self._active_holding_rows(portfolio["id"])
        if not active_holdings:
            raise ValueError("Portfolio 尚無 active Holding")

        item_values = self._snapshot_item_values(items)
        active_ids = {holding["id"] for holding in active_holdings}
        if set(item_values) != active_ids:
            raise ValueError("Snapshot 必須包含所有 active Holding，且不可包含其他 Holding")

        parsed_date = self._date(snapshot_date)
        existing = self.db_session.execute(
            select(portfolio_snapshots_table).where(
                portfolio_snapshots_table.c.portfolio_id == portfolio["id"],
                portfolio_snapshots_table.c.snapshot_date == parsed_date,
                portfolio_snapshots_table.c.deleted_at.is_(None),
            )
        ).first()
        if existing:
            snapshot = dict(existing._mapping)
            self.db_session.execute(
                update(portfolio_snapshots_table)
                .where(portfolio_snapshots_table.c.id == snapshot["id"])
                .values(note=self._optional_text(note, 500), updated_at=datetime.now(timezone.utc))
            )
            self.db_session.execute(
                delete(portfolio_snapshot_items_table).where(
                    portfolio_snapshot_items_table.c.snapshot_id == snapshot["id"]
                )
            )
            snapshot_id = snapshot["id"]
        else:
            snapshot_id = self.db_session.execute(
                insert(portfolio_snapshots_table)
                .values(
                    portfolio_id=portfolio["id"],
                    snapshot_date=parsed_date,
                    currency=portfolio["base_currency"],
                    note=self._optional_text(note, 500),
                )
                .returning(portfolio_snapshots_table.c.id)
            ).scalar_one()

        self.db_session.execute(
            insert(portfolio_snapshot_items_table),
            [
                {
                    "snapshot_id": snapshot_id,
                    "holding_id": holding_id,
                    "value": value,
                }
                for holding_id, value in item_values.items()
            ],
        )
        return next(
            snapshot
            for snapshot in self.list_snapshots(user_id, portfolio_id)
            if snapshot["id"] == str(snapshot_id)
        )

    def allocation_preview(self, user_id, portfolio_id, amount):
        portfolio = self._get_portfolio(user_id, portfolio_id)
        holdings = self._active_holding_rows(portfolio["id"])
        if not holdings:
            raise ValueError("Portfolio 尚無 active Holding")

        weights = [holding["target_weight"] for holding in holdings]
        if any(weight is None for weight in weights) or sum(weights, Decimal("0")) != WEIGHT_TOTAL:
            raise ValueError("active Holding 的目標比例合計必須為 100%")
        new_amount = self._positive_money(amount, "新增投入金額")
        current_values, basis, as_of = self._current_allocation_values(portfolio["id"], holdings)
        projected_total = sum(current_values.values(), Decimal("0")) + new_amount
        gaps = {
            holding["id"]: max(
                Decimal("0"),
                projected_total * holding["target_weight"] - current_values[holding["id"]],
            )
            for holding in holdings
        }
        total_gap = sum(gaps.values(), Decimal("0"))
        if total_gap == 0:
            gaps = {holding["id"]: holding["target_weight"] for holding in holdings}
            total_gap = WEIGHT_TOTAL

        allocations = []
        allocated = Decimal("0")
        for index, holding in enumerate(holdings):
            if index == len(holdings) - 1:
                recommended = new_amount - allocated
            else:
                recommended = (new_amount * gaps[holding["id"]] / total_gap).quantize(
                    MONEY_QUANTUM,
                    rounding=ROUND_HALF_UP,
                )
                allocated += recommended
            allocations.append(
                {
                    "holding_id": str(holding["id"]),
                    "name": holding["name"],
                    "symbol": holding["symbol"],
                    "target_weight": float(holding["target_weight"]),
                    "current_amount": float(current_values[holding["id"]]),
                    "recommended_amount": float(recommended),
                }
            )

        return {
            "portfolio_id": str(portfolio["id"]),
            "currency": portfolio["base_currency"],
            "basis": basis,
            "as_of": as_of,
            "new_amount": float(new_amount),
            "allocations": allocations,
        }

    def _get_portfolio(self, user_id, portfolio_id):
        row = self.db_session.execute(
            select(portfolios_table).where(
                portfolios_table.c.id == self._uuid(portfolio_id, "portfolio_id"),
                portfolios_table.c.user_id == self._uuid(user_id, "user_id"),
                portfolios_table.c.deleted_at.is_(None),
            )
        ).first()
        if not row:
            raise AllocationNotFoundError("找不到 Portfolio 或權限不足")
        return dict(row._mapping)

    def _get_holding(self, user_id, holding_id):
        row = self.db_session.execute(
            select(holdings_table, portfolios_table)
            .join(portfolios_table, holdings_table.c.portfolio_id == portfolios_table.c.id)
            .where(
                holdings_table.c.id == self._uuid(holding_id, "holding_id"),
                holdings_table.c.deleted_at.is_(None),
                portfolios_table.c.user_id == self._uuid(user_id, "user_id"),
                portfolios_table.c.deleted_at.is_(None),
            )
        ).first()
        if not row:
            raise AllocationNotFoundError("找不到 Holding 或權限不足")
        mapping = row._mapping
        holding = {column.name: mapping[column] for column in holdings_table.c}
        portfolio = {column.name: mapping[column] for column in portfolios_table.c}
        return holding, portfolio

    def _get_cost_entry(self, user_id, cost_entry_id):
        entry_row = self.db_session.execute(
            select(holding_cost_entries_table).where(
                holding_cost_entries_table.c.id == self._uuid(cost_entry_id, "cost_entry_id"),
                holding_cost_entries_table.c.deleted_at.is_(None),
            )
        ).first()
        if not entry_row:
            raise AllocationNotFoundError("找不到投入成本紀錄或權限不足")
        entry = dict(entry_row._mapping)
        holding, portfolio = self._get_holding(user_id, entry["holding_id"])
        return entry, holding, portfolio

    def _list_holdings(self, portfolio_id):
        rows = self.db_session.execute(
            select(holdings_table)
            .where(
                holdings_table.c.portfolio_id == portfolio_id,
                holdings_table.c.deleted_at.is_(None),
            )
            .order_by(holdings_table.c.created_at)
        ).all()
        return [self._serialize(dict(row._mapping)) for row in rows]

    def _active_holding_rows(self, portfolio_id):
        rows = self.db_session.execute(
            select(holdings_table)
            .where(
                holdings_table.c.portfolio_id == portfolio_id,
                holdings_table.c.is_active.is_(True),
                holdings_table.c.deleted_at.is_(None),
            )
            .order_by(holdings_table.c.created_at)
        ).all()
        return [dict(row._mapping) for row in rows]

    def _costs_by_holding(self, holding_ids):
        if not holding_ids:
            return {}
        parsed_ids = [self._uuid(value, "holding_id") for value in holding_ids]
        rows = self.db_session.execute(
            select(holding_cost_entries_table)
            .where(
                holding_cost_entries_table.c.holding_id.in_(parsed_ids),
                holding_cost_entries_table.c.deleted_at.is_(None),
            )
            .order_by(desc(holding_cost_entries_table.c.occurred_on))
        ).all()
        grouped = {}
        for row in rows:
            entry = self._serialize(dict(row._mapping))
            grouped.setdefault(entry["holding_id"], []).append(entry)
        return grouped

    def _investment_account(self, user_id, account_id, currency):
        row = self.db_session.execute(
            select(accounts_table).where(
                accounts_table.c.id == self._uuid(account_id, "account_id"),
                accounts_table.c.user_id == self._uuid(user_id, "user_id"),
                accounts_table.c.deleted_at.is_(None),
            )
        ).first()
        if not row:
            raise AllocationNotFoundError("找不到投資帳戶或權限不足")
        account = dict(row._mapping)
        if account["type"] != "investment":
            raise ValueError("Holding 只能連結 investment 帳戶")
        if account["currency"] != currency:
            raise ValueError("投資帳戶幣別必須與 Portfolio 基準幣別相同")
        return account

    def _validate_cost_source(
        self,
        user_id,
        holding,
        portfolio,
        entry_type,
        source_transfer_id,
        amount,
        exclude_entry_id=None,
    ):
        if entry_type == "manual_adjustment":
            if source_transfer_id:
                raise ValueError("手動成本不可連結帳戶轉帳")
            return None
        if not source_transfer_id:
            raise ValueError("轉帳成本必須提供 source_transfer_id")

        self._investment_account(user_id, holding["account_id"], portfolio["base_currency"])

        row = self.db_session.execute(
            select(transfers_table).where(
                transfers_table.c.id == self._uuid(source_transfer_id, "source_transfer_id"),
                transfers_table.c.user_id == self._uuid(user_id, "user_id"),
                transfers_table.c.deleted_at.is_(None),
            )
        ).first()
        if not row:
            raise AllocationNotFoundError("找不到帳戶轉帳或權限不足")
        transfer = dict(row._mapping)
        if transfer["target_account_id"] != holding["account_id"]:
            raise ValueError("帳戶轉帳的目標帳戶必須是 Holding 所屬帳戶")
        if transfer["target_currency"] != portfolio["base_currency"]:
            raise ValueError("帳戶轉帳幣別必須與 Portfolio 基準幣別相同")

        conditions = [
            holding_cost_entries_table.c.source_transfer_id == transfer["id"],
            holding_cost_entries_table.c.deleted_at.is_(None),
        ]
        if exclude_entry_id:
            conditions.append(holding_cost_entries_table.c.id != exclude_entry_id)
        duplicate_conditions = [
            holding_cost_entries_table.c.holding_id == holding["id"],
            holding_cost_entries_table.c.source_transfer_id == transfer["id"],
            holding_cost_entries_table.c.deleted_at.is_(None),
        ]
        if exclude_entry_id:
            duplicate_conditions.append(holding_cost_entries_table.c.id != exclude_entry_id)
        if self.db_session.execute(
            select(holding_cost_entries_table.c.id).where(*duplicate_conditions)
        ).first():
            raise ValueError("此 Holding 已連結該筆帳戶轉帳")
        allocated = self.db_session.execute(
            select(func.coalesce(func.sum(holding_cost_entries_table.c.amount), 0)).where(*conditions)
        ).scalar_one()
        if Decimal(str(allocated)) + amount > Decimal(str(transfer["target_amount"])):
            raise ValueError("此轉帳分配到 Holding 的成本總額不可超過轉入金額")
        return transfer

    def _current_allocation_values(self, portfolio_id, holdings):
        snapshot = self.db_session.execute(
            select(portfolio_snapshots_table)
            .where(
                portfolio_snapshots_table.c.portfolio_id == portfolio_id,
                portfolio_snapshots_table.c.deleted_at.is_(None),
            )
            .order_by(desc(portfolio_snapshots_table.c.snapshot_date))
            .limit(1)
        ).first()
        if snapshot:
            snapshot_data = dict(snapshot._mapping)
            rows = self.db_session.execute(
                select(
                    portfolio_snapshot_items_table.c.holding_id,
                    portfolio_snapshot_items_table.c.value,
                ).where(portfolio_snapshot_items_table.c.snapshot_id == snapshot_data["id"])
            ).all()
            values = {row.holding_id: row.value for row in rows}
            if set(values) == {holding["id"] for holding in holdings}:
                return values, "snapshot", snapshot_data["snapshot_date"].isoformat()

        values = {}
        for holding in holdings:
            total = self.db_session.execute(
                select(func.coalesce(func.sum(holding_cost_entries_table.c.amount), 0)).where(
                    holding_cost_entries_table.c.holding_id == holding["id"],
                    holding_cost_entries_table.c.deleted_at.is_(None),
                )
            ).scalar_one()
            values[holding["id"]] = Decimal(str(total))
        return values, "recorded_cost", None

    def _snapshot_item_values(self, items):
        if not isinstance(items, list) or not items:
            raise ValueError("Snapshot items 不可為空")
        values = {}
        for item in items:
            if not isinstance(item, dict) or "holding_id" not in item or "value" not in item:
                raise ValueError("Snapshot item 缺少 holding_id 或 value")
            holding_id = self._uuid(item["holding_id"], "holding_id")
            if holding_id in values:
                raise ValueError("Snapshot 不可重複包含同一 Holding")
            values[holding_id] = self._non_negative_money(item["value"], "Snapshot value")
        return values

    def _portfolio_has_holdings(self, portfolio_id):
        return self.db_session.execute(
            select(holdings_table.c.id).where(
                holdings_table.c.portfolio_id == portfolio_id,
                holdings_table.c.deleted_at.is_(None),
            ).limit(1)
        ).first() is not None

    def _holding_has_history(self, holding_id):
        has_cost = self.db_session.execute(
            select(holding_cost_entries_table.c.id)
            .where(
                holding_cost_entries_table.c.holding_id == holding_id,
                holding_cost_entries_table.c.deleted_at.is_(None),
            )
            .limit(1)
        ).first()
        if has_cost:
            return True
        return self.db_session.execute(
            select(portfolio_snapshot_items_table.c.id)
            .where(portfolio_snapshot_items_table.c.holding_id == holding_id)
            .limit(1)
        ).first() is not None

    def _ensure_currency_exists(self, currency):
        exists = self.db_session.execute(
            select(currencies_table.c.code).where(
                currencies_table.c.code == currency,
                currencies_table.c.is_active.is_(True),
            )
        ).first()
        if not exists:
            raise ValueError("不支援的 Portfolio 幣別")

    def _ensure_unique_portfolio_name(self, user_id, name, currency, exclude_id=None):
        conditions = [
            portfolios_table.c.user_id == user_id,
            portfolios_table.c.base_currency == currency,
            portfolios_table.c.name == name,
            portfolios_table.c.deleted_at.is_(None),
        ]
        if exclude_id:
            conditions.append(portfolios_table.c.id != exclude_id)
        if self.db_session.execute(select(portfolios_table.c.id).where(*conditions)).first():
            raise ValueError("同幣別已存在相同名稱的 Portfolio")

    def _ensure_unique_holding_name(self, portfolio_id, account_id, name, exclude_id=None):
        conditions = [
            holdings_table.c.portfolio_id == portfolio_id,
            holdings_table.c.account_id == account_id,
            holdings_table.c.name == name,
            holdings_table.c.deleted_at.is_(None),
        ]
        if exclude_id:
            conditions.append(holdings_table.c.id != exclude_id)
        if self.db_session.execute(select(holdings_table.c.id).where(*conditions)).first():
            raise ValueError("同一投資帳戶已存在相同名稱的 Holding")

    def _entry_type(self, value):
        normalized = str(value or "").strip()
        if normalized not in {"transfer", "manual_adjustment"}:
            raise ValueError("entry_type 必須是 transfer 或 manual_adjustment")
        return normalized

    def _weight(self, value):
        if value in (None, ""):
            return None
        parsed = self._decimal(value, "目標比例")
        if parsed < 0 or parsed > 1:
            raise ValueError("目標比例必須介於 0 與 1")
        return parsed.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

    def _positive_money(self, value, label):
        parsed = self._decimal(value, label).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        if parsed <= 0:
            raise ValueError(f"{label}必須大於 0")
        return parsed

    def _non_negative_money(self, value, label):
        parsed = self._decimal(value, label).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        if parsed < 0:
            raise ValueError(f"{label}不可為負數")
        return parsed

    def _decimal(self, value, label):
        try:
            parsed = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(f"{label}格式不正確") from exc
        if not parsed.is_finite():
            raise ValueError(f"{label}格式不正確")
        return parsed

    def _boolean(self, value, label):
        if not isinstance(value, bool):
            raise ValueError(f"{label} 必須是 boolean")
        return value

    def _uuid(self, value, label):
        try:
            return value if isinstance(value, UUID) else UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} 格式不正確") from exc

    def _date(self, value):
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        try:
            return date.fromisoformat(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError("日期格式必須為 YYYY-MM-DD") from exc

    def _currency(self, value):
        normalized = str(value or "").strip().upper()
        if len(normalized) != 3:
            raise ValueError("幣別格式不正確")
        return normalized

    def _text(self, value, label, max_length):
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError(f"{label}不可為空")
        if len(normalized) > max_length:
            raise ValueError(f"{label}不可超過 {max_length} 字")
        return normalized

    def _optional_text(self, value, max_length, uppercase=False):
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        if len(normalized) > max_length:
            raise ValueError(f"文字不可超過 {max_length} 字")
        return normalized.upper() if uppercase else normalized

    def _serialize(self, value):
        result = {}
        for key, item in value.items():
            if isinstance(item, UUID):
                result[key] = str(item)
            elif isinstance(item, Decimal):
                result[key] = float(item)
            elif isinstance(item, (date, datetime)):
                result[key] = item.isoformat()
            else:
                result[key] = item
        return result
