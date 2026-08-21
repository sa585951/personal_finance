from decimal import Decimal

from sqlalchemy import insert

from .schema import account_movements_table


def record_account_movement(
    db_session,
    *,
    account,
    source_type,
    source_id,
    operation,
    amount_delta,
    balance_before,
    balance_after,
    occurred_at,
):
    """Append one auditable account movement in the caller's DB transaction."""
    delta = Decimal(str(amount_delta))
    if delta == 0 or not account.get("track_balance"):
        return

    db_session.execute(
        insert(account_movements_table).values(
            user_id=account["user_id"],
            account_id=account["id"],
            source_type=source_type,
            source_id=source_id,
            operation=operation,
            amount_delta=delta,
            currency=account["currency"],
            balance_before=Decimal(str(balance_before)),
            balance_after=Decimal(str(balance_after)),
            occurred_at=occurred_at,
        )
    )
