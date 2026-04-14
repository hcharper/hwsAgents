# HWS Proposal Agent

A conversational Discord bot that drafts professional software project proposals. It works hand-in-hand with an existing pricing bot — gathering project requirements from the user, requesting a cost estimate via @mention, then producing a polished proposal as both a Discord embed and a downloadable PDF.

Powered by Anthropic Claude.

## Architecture

```
Discord User ──message──▶ Proposal Bot ──@mention──▶ Pricing Bot
                               │                          │
                               │ pricing response ◀───────┘
                               ▼
                         Claude API
                               │
                               ▼
                    Embed + PDF ──▶ Discord User
```

1. A user describes a project in the dedicated channel.
2. The bot asks clarifying questions (via Claude) until scope is clear.
3. The bot @mentions the pricing bot with a structured summary.
4. Once pricing data comes back, Claude generates a full proposal.
5. The user can request revisions or approve.
6. On approval the bot sends a rich embed preview and an attached PDF.

## Prerequisites

- Python 3.11+
- A Discord bot token with the **Message Content** intent enabled
- An Anthropic API key
- The pricing bot's Discord user ID (right-click the bot in Discord → Copy User ID)

## Quick Start

```bash
# 1. Clone the repo
git clone <repo-url> && cd hws_agents

# 2. Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env with your tokens and IDs

# 5. Run
python -m proposal_agent.main
```

## Configuration Reference

| Variable | Required | Description | Default |
|---|---|---|---|
| `DISCORD_BOT_TOKEN` | Yes | Bot token from Discord Developer Portal | — |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key | — |
| `PROPOSAL_CHANNEL_ID` | Yes | Discord channel ID the bot listens in | — |
| `PRICING_BOT_ID` | Yes | Discord user ID of the pricing bot | — |
| `CLAUDE_MODEL` | No | Anthropic model identifier | `claude-sonnet-4-20250514` |
| `PRICING_TIMEOUT_SECONDS` | No | Seconds to wait for a pricing bot reply | `60` |

All values are loaded from a `.env` file in the project root (or system environment variables).

## Pricing Bot Integration Guide

This is the most important section if you maintain the pricing bot or want to connect a new pricing agent.

### Message Protocol

When the proposal bot has gathered enough project details, it sends a message in the channel that @mentions the pricing bot:

```
@PricingBot estimate for:
- Project: E-commerce Dashboard
- Tech: React, Node.js, PostgreSQL
- Pages/Features: 5 pages, auth, payment integration
- Timeline: 6 weeks
```

The mention uses the standard Discord user mention format `<@USER_ID>`. The body is a simple bulleted list with these fields (any may be absent if the user didn't provide them):

| Field | Description |
|---|---|
| `Project` | Name / title of the project |
| `Tech` | Tech stack or platform |
| `Pages/Features` | Feature list, page count, or scope summary |
| `Timeline` | Expected duration |

The formatting logic lives in `proposal_agent/handlers/pricing.py → build_pricing_request()`.

### Expected Response Format

The proposal bot listens for the next message in the channel from the pricing bot's user ID. It expects a text response roughly like this:

```
Estimate for E-commerce Dashboard:
- Frontend Development: $8,000
- Backend/API: $6,000
- Database & Auth: $3,000
- Payment Integration: $2,500
- Testing & QA: $1,500
Total: $21,000
```

**Parsing rules** (implemented in `proposal_agent/handlers/pricing.py → parse_pricing_response()`):

- Line items are matched by the pattern `- Description: $Amount` (bullets can be `-`, `•`, or `*`).
- A `Total: $Amount` line is matched separately.
- If no explicit total is found, the parser sums the line items.
- Dollar signs and commas in amounts are handled automatically.
- If no line items or total can be parsed, the bot reports a parse error and asks the user to paste pricing manually.

### How to Adapt

If your pricing bot uses a different output format:

1. Open `proposal_agent/handlers/pricing.py`
2. Modify `parse_pricing_response()` — the two regex patterns (`item_pattern` and `total_pattern`) control what gets extracted
3. The function must return a `PricingResult(raw_text, line_items, total)` where `line_items` is a list of `(description, float)` tuples

If you want to change what the proposal bot sends to the pricing bot:

1. Modify `build_pricing_request()` in the same file
2. Update the `field_map` dict to match whatever fields your pricing bot expects

### Fallback Behavior

- If the pricing bot doesn't respond within `PRICING_TIMEOUT_SECONDS` (default 60s), the proposal bot tells the user and drops back to the gathering state so they can paste pricing info manually.
- If the response can't be parsed, the bot reports the error and the raw text so the user can intervene.

### Discord Permissions

Both bots need these permissions in the shared channel:

- **Read Messages** / **View Channel**
- **Send Messages**
- **Read Message History**

The proposal bot also needs the **Message Content** privileged intent enabled in the Discord Developer Portal (Bot → Privileged Gateway Intents → Message Content Intent).

## Conversation Flow

```
┌─────────┐
│  IDLE    │◀──────────────────────────────────────┐
└────┬─────┘                                       │
     │ user sends message                          │
     ▼                                             │
┌───────────┐  Claude asks questions               │
│ GATHERING │◀──────────┐                          │
└────┬──────┘           │                          │
     │ enough detail    │ user answers              │
     ▼                  │                          │
┌──────────────────┐    │                          │
│ WAITING_FOR_     │────┘ (on timeout)             │
│ PRICING          │                               │
└────┬─────────────┘                               │
     │ pricing received                            │
     ▼                                             │
┌──────────┐                                       │
│ DRAFTING │                                       │
└────┬─────┘                                       │
     │ proposal generated                          │
     ▼                                             │
┌──────────┐  user requests changes                │
│ REVIEW   │──────────▶ DRAFTING ──▶ REVIEW        │
└────┬─────┘                                       │
     │ user approves                               │
     ▼                                             │
┌───────────┐  embed + PDF delivered               │
│ FINALIZED │──────────────────────────────────────┘
└───────────┘
```

**States:**

- **Idle** — Waiting for a user to start a conversation.
- **Gathering** — Claude asks clarifying questions about the project scope, tech stack, timeline, and deliverables.
- **Waiting for Pricing** — The bot has @mentioned the pricing bot and is waiting for a reply.
- **Drafting** — Claude is generating the proposal from project details + pricing data.
- **Review** — The user is reviewing the draft. They can request changes or approve.
- **Finalized** — The proposal has been approved and delivered as an embed + PDF.

## Customization

### Claude System Prompt

Edit `proposal_agent/templates/proposal_prompt.txt` to change the bot's persona, question style, or proposal structure. The prompt controls both the gathering phase and the proposal generation format.

### PDF Branding

The PDF template is in `proposal_agent/services/pdf.py`. Configurable elements:

- `_BRAND_COLOR` — Primary color used for headings and table headers
- `_LIGHT_BG` — Alternating row background color
- Page margins, font sizes, and styles in `_styles()`
- Add a logo by placing an image and using `reportlab.platypus.Image`

### Discord Embed

The embed layout is in `proposal_agent/templates/proposal_embed.py`. You can change:

- `EMBED_COLOR` — The accent color on the embed sidebar
- Field order and content
- Truncation limits (default 1024 chars per field, Discord's limit)

## Project Structure

```
proposal_agent/
  __init__.py
  main.py                  # Entry point
  config.py                # Env var loading and validation
  client.py                # Discord client, event routing
  handlers/
    __init__.py
    conversation.py        # Conversation state machine
    pricing.py             # Pricing bot @mention and response parsing
  services/
    __init__.py
    claude.py              # Anthropic API client
    proposal.py            # Proposal data model
    pdf.py                 # PDF generation with reportlab
  templates/
    __init__.py
    proposal_prompt.txt    # Claude system prompt
    proposal_embed.py      # Discord embed builder
  utils/
    __init__.py
    context.py             # Conversation memory store
tests/
  ...                      # pytest test suite
requirements.txt
.env.example
proposal_agent_README.md
```

## Running Tests

```bash
pytest tests/ -v
```

Tests mock all external services (Discord, Anthropic, file I/O) so no tokens or network access are needed.

## Adding New Agents

To add another agent (bot) to this repo:

1. Create a new package under the repo root (e.g., `billing_bot/`) following the same layout.
2. Share `Config` patterns — each agent loads its own env vars with distinct prefixes.
3. Each agent should filter to its own `CHANNEL_ID` so multiple bots can run in the same server without interference.
4. Shared utilities (like the `ContextStore` pattern) can be extracted to a common package if needed.

## Troubleshooting

| Problem | Check |
|---|---|
| Bot doesn't respond to messages | Verify `PROPOSAL_CHANNEL_ID` matches the channel. Ensure the Message Content intent is enabled in the Developer Portal. |
| Pricing bot timeout | Confirm `PRICING_BOT_ID` is correct (use Developer Mode → Copy User ID). Both bots must have access to the same channel. |
| Claude API errors | Check `ANTHROPIC_API_KEY` is valid. Look for rate-limit or quota errors in logs. |
| PDF generation fails | Ensure `reportlab` is installed (`pip install reportlab`). Check logs for rendering errors. |
| Bot responds in wrong channel | Double-check `PROPOSAL_CHANNEL_ID` — the bot strictly ignores all other channels. |
