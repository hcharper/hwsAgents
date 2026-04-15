# Shared Modules

Code shared across all HWS agents, located in `shared/`.

## shared/llm.py — Anthropic API Client

Wrapper around the Anthropic SDK with two key features:
- **Prompt caching** — system prompts are marked with `cache_control: ephemeral`, so repeated requests with the same system prompt use cached tokens at 10x lower cost
- **Usage tracking** — every API call automatically records token counts to the global `UsageTracker`

```python
from shared.llm import create_client, chat

client = create_client("sk-ant-...")
reply = await chat(
    client=client,
    model="claude-sonnet-4-5-20250929",
    system_prompt="You are a helpful assistant.",
    messages=[{"role": "user", "content": "Hello"}],
    agent_name="my_agent",  # tracked in usage.json
)
```

## shared/memory.py — Conversation History

In-memory per-channel message history using a bounded deque. Automatically drops old messages when the limit is reached.

```python
from shared.memory import ChannelMemory

mem = ChannelMemory(max_messages=40)
mem.add(channel_id, "user", "Hello")
mem.add(channel_id, "assistant", "Hi there")
messages = mem.get_messages(channel_id)  # list of {"role": ..., "content": ...}
mem.clear(channel_id)
```

## shared/data_manager.py — YAML Data Layer

Loads, saves, and validates `pricing.yaml` and `objections.yaml`. Features:
- **Change callbacks** — register functions that fire when data is updated (used to rebuild system prompts)
- **Timestamped backups** — creates `.bak` files before every write
- **Lazy loading** — data loaded on first access

```python
from shared.data_manager import DataManager

dm = DataManager(Path("data"))
dm.load()
dm.on_change(lambda: print("Data changed!"))
dm.save_pricing(updated_data)  # backs up, saves, notifies
```

## shared/usage_tracker.py — API Cost Tracking

Records token usage per agent per month. Calculates real dollar costs using Anthropic's published pricing (Sonnet 4.5 and Haiku 4.5 rates built in).

Data stored in `data/usage.json`. All agents in the repo write to the same file.

```python
from shared.usage_tracker import UsageTracker

tracker = UsageTracker(Path("data/usage.json"))
tracker.record(
    agent="pricing_agent",
    model="claude-sonnet-4-5-20250929",
    input_tokens=8000,
    output_tokens=400,
    cache_read_tokens=7500,
)
print(tracker.format_summary())  # Discord-formatted usage report
```

### Cost Calculation

Pricing per million tokens (built into `usage_tracker.py`):

| Model | Input | Output | Cache Write | Cache Read |
|-------|-------|--------|-------------|------------|
| Sonnet 4.5 | $3.00 | $15.00 | $3.75 | $0.30 |
| Haiku 4.5 | $0.80 | $4.00 | $1.00 | $0.08 |
