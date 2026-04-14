"""Anthropic Claude API wrapper with prompt caching."""

from anthropic import AsyncAnthropic


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
) -> str:
    """Send a message to Claude with prompt caching on the system prompt.

    The system prompt is marked with cache_control so repeated requests
    with the same system prompt use cached input tokens ($0.30/MTok
    instead of $3/MTok on Sonnet).
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
    return response.content[0].text
