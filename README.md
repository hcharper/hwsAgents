# HWS Agents

Internal Discord agent fleet for Harper Web Services. Each agent is a separate Discord bot with its own token, channel, and personality.

## Architecture

```
agents/
├── shared/              # Shared code (LLM client, memory, data manager)
├── pricing_agent/       # Sales support — pricing, quotes, objections
├── manager_agent/       # Admin control — edits pricing data, manages agents
├── data/                # Shared YAML data (pricing, objections)
└── tests/
```

**Each agent = separate Discord bot** (separate token, separate identity). They can @mention each other for cross-agent workflows. All agents share the same `data/` directory — when the manager updates pricing, the pricing agent picks it up on its next message.

## Agents

| Agent | Channel | What it does |
|-------|---------|-------------|
| **Pricing Bot** | Sales channel | Answers pricing questions, builds quotes, handles objections, estimates scope |
| **Manager Bot** | Admin channel | Updates pricing/objection data, manages agent configs |
| **Proposal Bot** | Proposal channel | _(Coming soon)_ Generates client proposals from quotes |

## Setup

### 1. Create Discord Bots

Go to [discord.com/developers/applications](https://discord.com/developers/applications) and create **two** bot applications:

- **HWS Pricing Bot** — for the sales channel
- **HWS Manager Bot** — for the admin channel

For each:
1. Go to **Bot** tab → Reset Token → copy it
2. Enable **Message Content Intent** under Privileged Gateway Intents
3. Go to **OAuth2 → URL Generator** → check `bot` scope → check permissions: Send Messages, Read Messages/View Channels, Read Message History
4. Open the generated URL → invite to your server

### 2. Get Channel IDs

In Discord: Settings → Advanced → enable Developer Mode. Then right-click each channel → Copy Channel ID.

### 3. Install & Configure

```bash
cd agents
pip install -e .
cp .env.example .env
# Edit .env with your bot tokens, channel IDs, and Anthropic API key
```

### 4. Run

Run each bot in a separate terminal (or use a process manager):

```bash
hws-pricing   # starts the pricing bot
hws-manager   # starts the manager bot
```

## Cross-Bot Communication

The pricing bot can @mention the proposal bot when a quote is finalized. Set `PROPOSAL_BOT_ID` in `.env` to the proposal bot's Discord user ID (visible after the bot joins the server).

## Cost (Claude Sonnet 4.5 with prompt caching)

- ~$0.02 per request (system prompt cached at 10x discount)
- ~100 requests/day = ~$60/month
- Switch `ANTHROPIC_MODEL` to `claude-haiku-4-5-20251001` for ~$15/month

## Testing

```bash
pip install -e ".[dev]"
pytest
```
