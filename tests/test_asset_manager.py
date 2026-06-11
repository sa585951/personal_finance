from models.asset_manager import AssetManager


def test_investment_account_type_aliases_are_supported():
    manager = AssetManager(db_session=None)

    assert manager._normalize_account_type("investment") == "investment"
    assert manager._normalize_account_type("投資") == "investment"
    assert manager._normalize_account_type("券商") == "investment"
