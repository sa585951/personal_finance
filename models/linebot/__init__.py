__all__ = ["LineBotManager"]


def __getattr__(name):
    if name == "LineBotManager":
        from .manager import LineBotManager

        return LineBotManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
