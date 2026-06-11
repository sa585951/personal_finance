from models.asset_manager import AssetManager


def test_investment_account_type_aliases_are_supported():
    manager = AssetManager(db_session=None)

    assert manager._normalize_account_type("investment") == "investment"
    assert manager._normalize_account_type("投資") == "investment"
    assert manager._normalize_account_type("券商") == "investment"


def test_transfer_note_and_limit_are_normalized():
    manager = AssetManager(db_session=None)

    assert manager._normalize_transfer_note("  旅費儲蓄  ") == "旅費儲蓄"
    assert manager._normalize_transfer_note("") is None
    assert len(manager._normalize_transfer_note("a" * 120)) == 100
    assert manager._normalize_limit("8") == 8
    assert manager._normalize_limit("invalid") == 10
    assert manager._normalize_limit("999") == 50


def test_only_credit_card_accounts_allow_negative_balance():
    manager = AssetManager(db_session=None)

    assert manager._allows_negative_balance("credit_card") is True
    assert manager._allows_negative_balance({"type": "credit_card"}) is True
    assert manager._allows_negative_balance("bank") is False
    assert manager._allows_negative_balance({"type": "investment"}) is False
