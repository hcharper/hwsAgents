"""Per-channel conversation history (in-memory deque)."""

from collections import deque


class ChannelMemory:
    """Manages conversation history for all channels."""

    def __init__(self, max_messages: int = 40):
        self._max = max_messages
        self._channels: dict[int, deque[dict]] = {}

    def _get_deque(self, channel_id: int) -> deque[dict]:
        if channel_id not in self._channels:
            self._channels[channel_id] = deque(maxlen=self._max)
        return self._channels[channel_id]

    def add(self, channel_id: int, role: str, content: str) -> None:
        """Add a message to a channel's history."""
        self._get_deque(channel_id).append({"role": role, "content": content})

    def get_messages(self, channel_id: int) -> list[dict]:
        """Get the conversation history for a channel."""
        return list(self._get_deque(channel_id))

    def clear(self, channel_id: int) -> None:
        """Clear a channel's history."""
        if channel_id in self._channels:
            self._channels[channel_id].clear()
