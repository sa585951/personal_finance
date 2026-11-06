"""N04: durable balance-adjustment intent across requests and workers."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models.asset_manager import AssetManager
from models.idempotency import IdempotencyConflict
from models.reconciliation_manager import ReconciliationManager
from models.schema import accounts_table, account_adjustments_table, financial_commands_table
from tests.test_account_request_integrity import account_snapshot, asset_client
from tests.test_financial_command_idempotency import command_db  # noqa: F401


def payload(key, **changes):
    return {"new_balance": "1200.5000", "reason": "statement_reconciliation",
            "note": "QA original note", "client_request_id": str(key), **changes}


def send(client, headers, account_id, body):
    return client.post(f"/api/assets/{account_id}/adjustments", json=body, headers=headers)


def adjust(session, owner, account_id, key, **changes):
    options = {"new_balance": "1200.5000", "reason": "statement_reconciliation",
               "note": "QA original note", **changes}
    return AssetManager(session).create_balance_adjustment(owner, account_id, client_request_id=key, **options)


@pytest.mark.parametrize("changes", [
    {"new_balance": "1200.5001"}, {"reason": "other"}, {"note": "changed"}, {"account_id": "bank"},
])
def test_changed_adjustment_intent_is_conflict_without_effect(command_db, monkeypatch, changes):
    engine, data = command_db
    client, headers = asset_client(monkeypatch, engine, data)
    body = payload(uuid4())
    assert send(client, headers, data["cash"], body).status_code == 201
    with Session(engine) as session:
        before = account_snapshot(session)
    target = data[changes.get("account_id", "cash")]
    response = send(client, headers, target, {**body, **{k: v for k, v in changes.items() if k != "account_id"}})
    assert response.status_code == 409
    assert response.json["code"] == "REQUEST_PAYLOAD_CONFLICT"
    with Session(engine) as session:
        assert account_snapshot(session) == before


@pytest.mark.parametrize("key", ["omitted", None, "", [], {}, False, "not-a-uuid"])
def test_public_adjustment_requires_valid_key_without_effect(command_db, monkeypatch, key):
    engine, data = command_db
    client, headers = asset_client(monkeypatch, engine, data)
    body = payload(uuid4())
    if key == "omitted":
        del body["client_request_id"]
    else:
        body["client_request_id"] = key
    with Session(engine) as session:
        before = account_snapshot(session)
    assert send(client, headers, data["cash"], body).status_code == 400
    with Session(engine) as session:
        assert account_snapshot(session) == before


def test_bound_owner_mismatch_blocks_adjustment(command_db, monkeypatch):
    engine, data = command_db
    client, headers = asset_client(monkeypatch, engine, data)
    headers["X-Nomica-Request-Owner"] = str(data["b"])
    with Session(engine) as session:
        before = account_snapshot(session)
    response = send(client, headers, data["cash"], payload(uuid4()))
    assert response.status_code == 409 and response.json["code"] == "REQUEST_OWNER_CHANGED"
    with Session(engine) as session:
        assert account_snapshot(session) == before


@pytest.mark.parametrize("legacy", [False, True])
def test_adjustment_retry_uses_original_target_after_later_change(command_db, legacy):
    engine, data = command_db
    key = uuid4()
    with Session(engine) as session:
        first = adjust(session, data["a"], data["cash"], key)
        if legacy:
            session.execute(delete(financial_commands_table).where(financial_commands_table.c.request_id == key))
        adjust(session, data["a"], data["cash"], None, new_balance=1400)
        session.commit()
        before = account_snapshot(session)
    with Session(engine) as session:
        replay = adjust(session, data["a"], data["cash"], key, new_balance=1200.5, note=" QA original note ")
        assert replay == {**first, "replayed": True}
        with pytest.raises(IdempotencyConflict):
            adjust(session, data["a"], data["cash"], key, new_balance=1400)
        session.commit()
        assert account_snapshot(session) == before
        assert session.scalar(select(accounts_table.c.balance).where(accounts_table.c.id == data["cash"])) == 1400
        assert ReconciliationManager(session).reconcile()["summary"]["mismatched"] == 0


def test_legacy_adjustment_matches_decimal_without_float_round_trip(command_db):
    engine, data = command_db
    key = uuid4()
    original = Decimal("99999999999999.0001")
    with Session(engine) as session:
        first = adjust(session, data["a"], data["cash"], key, new_balance=original)
        session.execute(delete(financial_commands_table).where(financial_commands_table.c.request_id == key))
        session.commit()
        assert session.scalar(select(account_adjustments_table.c.balance_after)) == original
        before = account_snapshot(session)
    with Session(engine) as session:
        replay = adjust(session, data["a"], data["cash"], key, new_balance=str(original))
        assert replay == {**first, "replayed": True}
        with pytest.raises(IdempotencyConflict):
            adjust(session, data["a"], data["cash"], key, new_balance="99999999999999.0002")
        session.commit()
        assert account_snapshot(session) == before


@pytest.mark.parametrize("different_account", [False, True])
def test_concurrent_adjustment_requests_serialize_across_accounts(command_db, different_account):
    engine, data = command_db
    key, barrier = uuid4(), Barrier(2)

    def attempt(account_id):
        with Session(engine) as session:
            barrier.wait(timeout=8)
            try:
                result = adjust(session, data["a"], account_id, key)
                session.commit()
                return result
            except IdempotencyConflict:
                return None

    targets = [data["cash"], data["bank"] if different_account else data["cash"]]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, targets))
    assert sum(result is None for result in results) == int(different_account)
    assert sum(result is not None and not result["replayed"] for result in results) == 1
    assert len({result["id"] for result in results if result}) == 1
    with Session(engine) as session:
        assert len(session.execute(select(account_adjustments_table)).all()) == 1
        assert len(session.execute(select(financial_commands_table)).all()) == 1
        assert ReconciliationManager(session).reconcile()["summary"]["mismatched"] == 0


def test_adjustment_and_implicit_anchor_rollback_with_reservation(command_db, monkeypatch):
    from models.schema import account_balance_anchors_table

    engine, data = command_db
    key = uuid4()
    with Session(engine) as session:
        session.execute(delete(account_balance_anchors_table).where(account_balance_anchors_table.c.account_id == data["cash"]))
        session.commit()
        before = account_snapshot(session)
        with monkeypatch.context() as patch:
            def fail(*_):
                raise RuntimeError("Injected after adjustment and balance write")

            patch.setattr(AssetManager, "_get_adjustment", fail)
            with pytest.raises(RuntimeError, match="Injected"):
                adjust(session, data["a"], data["cash"], key)
        session.commit()
        assert account_snapshot(session) == before
        result = adjust(session, data["a"], data["cash"], key)
        session.commit()
        assert not result["replayed"]
        assert ReconciliationManager(session).reconcile()["summary"]["mismatched"] == 0


def test_adjustment_same_key_is_owner_scoped_and_internal_keyless_still_works(command_db):
    engine, data = command_db
    key = uuid4()
    with Session(engine) as session:
        first = adjust(session, data["a"], data["cash"], key, new_balance=0)
        second = adjust(session, data["b"], data["b_cash"], key)
        third = adjust(session, data["a"], data["cash"], None, new_balance=900)
        session.commit()
        assert len({first["id"], second["id"], third["id"]}) == 3
        assert first["balance_after"] == 0
        assert all(not result["replayed"] for result in (first, second, third))


def test_adjustment_replays_equivalent_signed_zero(command_db, monkeypatch):
    engine, data = command_db
    client, headers = asset_client(monkeypatch, engine, data)
    body = payload(uuid4(), new_balance=0)
    first = send(client, headers, data["cash"], body)
    replay = send(client, headers, data["cash"], {**body, "new_balance": "-0.0000"})
    assert first.status_code == 201 and replay.status_code == 200
    assert first.json["data"]["id"] == replay.json["data"]["id"]


def test_unstorable_adjustment_delta_is_definitive_400_and_no_effect(command_db, monkeypatch):
    engine, data = command_db
    client, headers = asset_client(monkeypatch, engine, data)
    with Session(engine) as session:
        card = AssetManager(session).add_account(data["a"], "QA card", "credit_card", "-90000000000000")
        session.commit()
        before = account_snapshot(session)
    response = send(client, headers, card.account_id, payload(uuid4(), new_balance="90000000000000"))
    assert response.status_code == 400
    with Session(engine) as session:
        assert account_snapshot(session) == before


@pytest.mark.parametrize("legacy_changes", [
    {"balance": 1200},
    {"new_balance": 0},
    {"bank_name": "Do not rename", "balance": 1200},
    {"bank_name": "Do not rename", "new_balance": None},
    {"balance": 1200, "new_balance": 1250},
])
def test_public_account_edit_rejects_legacy_balance_write_atomically(command_db, monkeypatch, legacy_changes):
    engine, data = command_db
    client, headers = asset_client(monkeypatch, engine, data)
    account_id = data["cash"]
    command = payload(uuid4(), new_balance=1300)
    adjustment = send(client, headers, account_id, command)
    assert adjustment.status_code == 201
    with Session(engine) as session:
        before = account_snapshot(session)

    rejected = client.put(f"/api/assets/{account_id}", json=legacy_changes, headers=headers)
    with Session(engine) as session:
        assert account_snapshot(session) == before
    assert rejected.status_code == 400
    assert "POST /api/assets/:accountId/adjustments" in rejected.json["message"]

    replay = send(client, headers, account_id, command)
    assert replay.status_code == 200 and replay.json["replayed"] is True
    assert replay.json["data"]["id"] == adjustment.json["data"]["id"]
    with Session(engine) as session:
        assert account_snapshot(session) == before


def test_public_account_edit_still_accepts_profile_and_preserves_ledger(command_db, monkeypatch):
    engine, data = command_db
    client, headers = asset_client(monkeypatch, engine, data)
    account_id = data["cash"]
    with Session(engine) as session:
        before = account_snapshot(session)
    edited = client.put(f"/api/assets/{account_id}", json={
        "bank_name": "Renamed cash", "currency": "TWD", "color_key": "amber",
    }, headers=headers)
    assert edited.status_code == 200 and edited.json["success"] is True
    with Session(engine) as session:
        account = session.execute(select(accounts_table).where(accounts_table.c.id == account_id)).one()
        assert (account.name, account.currency, account.color_key, account.balance) == (
            "Renamed cash", "TWD", "amber", Decimal("1000"),
        )
        assert account_snapshot(session)[1:] == before[1:]
