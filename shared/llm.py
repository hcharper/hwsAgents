"""Anthropic Claude API wrapper with prompt caching and usage tracking."""

from anthropic import AsyncAnthropic

from shared.usage_tracker import UsageTracker

# Global usage tracker — shared across all agents in this process
_tracker: UsageTracker | None = None


def get_tracker() -> UsageTracker:
    """Get the global usage tracker, creating it if needed."""
    global _tracker
    if _tracker is None:
        from pathlib import Path
        _tracker = UsageTracker(Path("data") / "usage.json")
    return _tracker


def set_tracker(tracker: UsageTracker) -> None:
    """Set the global usage tracker (called from main.py with correct data_dir)."""
    global _tracker
    _tracker = tracker


def create_client(api_key: str) -> AsyncAnthropic:
    """Create an AsyncAnthropic client."""
    return AsyncAnthropic(api_key=api_key)


async def chat(
    client: AsyncAnthropic,
    model: str,
    system_prompt: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 2048,
    agent_name: str = "unknown",
) -> str:
    """Send a message to Claude with prompt caching on the system prompt.

    Tracks token usage per agent automatically.
    """
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
    )

    # Track usage
    usage = response.usage
    tracker = get_tracker()
    tracker.record(
        agent=agent_name,
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
    )

    return response.content[0].text
