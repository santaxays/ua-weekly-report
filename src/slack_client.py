"""Thin wrapper around slack_sdk for posting messages to Slack."""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackClient:
    def __init__(self, token: str):
        """Create a Slack client using a Bot token (starts with xoxb-)."""
        self._client = WebClient(token=token)

    def send_message(self, channel_id: str, text: str) -> None:
        """Post a plain-text message to a Slack channel.

        Args:
            channel_id: The Slack channel ID (e.g. C0123456789).
            text: The message text to send.

        Raises:
            RuntimeError: If Slack returns an error.
        """
        try:
            self._client.chat_postMessage(channel=channel_id, text=text)
        except SlackApiError as e:
            raise RuntimeError(f"Slack error: {e.response['error']}") from e

    def send_blocks(
        self, channel_id: str, blocks: list, fallback_text: str
    ) -> None:
        """Post a rich Block Kit message to a Slack channel.

        Args:
            channel_id: The Slack channel ID (e.g. C0123456789).
            blocks: A list of Slack Block Kit block dicts.
            fallback_text: Plain-text shown in notifications and as a fallback.

        Raises:
            RuntimeError: If Slack returns an error.
        """
        try:
            self._client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text=fallback_text,
            )
        except SlackApiError as e:
            raise RuntimeError(f"Slack error: {e.response['error']}") from e
