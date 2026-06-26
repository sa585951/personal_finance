from linebot.v3.messaging import FlexContainer, FlexMessage


class FlexSendMessage(FlexMessage):
    """Keep the existing card builders stable while emitting SDK v3 messages."""

    def __init__(self, alt_text, contents):
        parsed_contents = (
            FlexContainer.from_dict(contents)
            if isinstance(contents, dict)
            else contents
        )
        super().__init__(altText=alt_text, contents=parsed_contents)

    def as_json_string(self):
        """Compatibility helper used by existing card tests."""
        return self.to_json()
