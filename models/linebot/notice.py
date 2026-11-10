"""The plain notice card used to send text replies and pushes over LINE."""
from .line_sdk import FlexSendMessage


def create_notice_message(title, message, color="#4CAF50"):
    flex_content = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": title, "weight": "bold", "size": "md", "color": color, "wrap": True},
                {"type": "text", "text": str(message), "size": "sm", "color": "#333333", "wrap": True,
                 "margin": "md"},
            ],
            "paddingAll": "20px",
        },
    }
    return FlexSendMessage(alt_text=title, contents=flex_content)
