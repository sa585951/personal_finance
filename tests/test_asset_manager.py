from models.asset_manager import AssetManager
import pytest


def test_investment_account_type_aliases_are_supported():
    manager = AssetManager(db_session=None)

    assert manager._normalize_account_type("investment") == "investment"
    assert manager._normalize_account_type("投資") == "investment"
    assert manager._normalize_account_type("券商") == "investment"


def test_account_appearance_uses_type_defaults_and_validates_keys():
    manager = AssetManager(db_session=None)

    assert manager._normalize_icon_key(None, "bank") == "bank"
    assert manager._normalize_color_key(None, "bank") == "blue"
    assert manager._normalize_icon_key(None, "credit_card") == "card"
    assert manager._normalize_color_key(None, "credit_card") == "rose"
    assert manager._normalize_icon_key("savings", "bank") == "savings"
    assert manager._normalize_color_key("amber", "bank") == "amber"

    with pytest.raises(ValueError, match="不支援的帳戶圖示"):
        manager._normalize_icon_key("sf-symbol-name", "bank")

    with pytest.raises(ValueError, match="不支援的帳戶顏色"):
        manager._normalize_color_key("#123456", "bank")


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


def test_specific_credit_card_hint_scores_named_card_higher_than_generic_card():
    manager = AssetManager(db_session=None)

    cathay_card = {"name": "國泰 CUBE 卡", "type": "credit_card", "updated_at": None}
    other_card = {"name": "台新信用卡", "type": "credit_card", "updated_at": None}

    assert manager._score_account_match(cathay_card, "國泰信用卡") > manager._score_account_match(
        other_card,
        "國泰信用卡",
    )


def test_generic_credit_card_hint_only_scores_by_type():
    manager = AssetManager(db_session=None)

    cathay_card = {"name": "國泰 CUBE 卡", "type": "credit_card", "updated_at": None}
    other_card = {"name": "台新信用卡", "type": "credit_card", "updated_at": None}

    assert manager._score_account_match(cathay_card, "信用卡") == manager._score_account_match(
        other_card,
        "信用卡",
    )


def test_context_text_can_help_match_when_parser_keeps_generic_hint():
    manager = AssetManager(db_session=None)

    cathay_card = {"name": "國泰 CUBE 卡", "type": "credit_card", "updated_at": None}
    other_card = {"name": "台新信用卡", "type": "credit_card", "updated_at": None}

    assert manager._score_account_match(
        cathay_card,
        "信用卡",
        context_text="晚餐 680 用國泰 CUBE 卡",
    ) > manager._score_account_match(
        other_card,
        "信用卡",
        context_text="晚餐 680 用國泰 CUBE 卡",
    )


def test_specific_bank_hint_scores_matching_bank_account_higher():
    manager = AssetManager(db_session=None)

    cathay_savings = {"name": "國泰活存", "type": "bank", "updated_at": None}
    cathay_deposit = {"name": "國泰定存", "type": "bank", "updated_at": None}

    assert manager._score_account_match(cathay_savings, "國泰活存") > manager._score_account_match(
        cathay_deposit,
        "國泰活存",
    )


def test_generic_bank_hint_only_scores_by_type():
    manager = AssetManager(db_session=None)

    cathay_savings = {"name": "國泰活存", "type": "bank", "updated_at": None}
    esun_savings = {"name": "玉山活存", "type": "bank", "updated_at": None}

    assert manager._score_account_match(cathay_savings, "銀行") == manager._score_account_match(
        esun_savings,
        "銀行",
    )


def test_context_text_can_help_match_named_bank_when_parser_keeps_generic_hint():
    manager = AssetManager(db_session=None)

    cathay_savings = {"name": "國泰活存", "type": "bank", "updated_at": None}
    esun_savings = {"name": "玉山活存", "type": "bank", "updated_at": None}

    assert manager._score_account_match(
        cathay_savings,
        "銀行",
        context_text="薪資 50000 存入國泰活存",
    ) > manager._score_account_match(
        esun_savings,
        "銀行",
        context_text="薪資 50000 存入國泰活存",
    )
