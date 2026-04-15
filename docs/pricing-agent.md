# Pricing Agent

**Channel:** `#pricing-agent`
**Bot name:** HWS Pricing Agent
**Entry point:** `python3 -m pricing_agent.main`
**CLI:** `hws-pricing`

## What It Does

Conversational quoting tool for sales reps. Reps describe a client's needs during a live call, the bot asks 2-3 clarifying questions at a time, then delivers a formatted quote with list prices, floor prices (20% discount buffer), first-year totals, and rep commission breakdown.

Also handles objection lookups — reps can say "client says it's too expensive" and get the scripted response for that product.

## How It Works

1. Rep types a message describing the client situation
2. Bot asks short clarifying questions (2-3 max per message)
3. Once it has enough context, bot delivers a quote table
4. Rep can continue the conversation to adjust the quote or ask follow-ups
5. `/clear` wipes the channel and resets memory

All pricing data comes from `data/pricing.yaml` and `data/objections.yaml`, injected into the system prompt with prompt caching for cost efficiency.

## Commands

| Command | Description |
|---------|-------------|
| `/clear` | Wipes all messages (except pinned welcome) and resets conversation memory |

## Quote Format

The bot outputs quotes like:

```
**Dental Practice — Voice Receptionist + SEO**

| Item | One-Time | Monthly |
|------|----------|---------|
| AI Voice Receptionist (Standard) | $3,500 (floor: $2,800) | $149 (floor: $119) |
| AI SEO Services | — | $500 (floor: $400) |
| **Totals** | **$3,500** | **$649/mo** |

**First-Year Total:** $11,288
**Your Commission:** $800 upfront + $64.90/mo residual
```

## Configuration

| Env Var | Description |
|---------|-------------|
| `PRICING_BOT_TOKEN` | Discord bot token |
| `PRICING_CHANNEL_IDS` | Comma-separated channel IDs to listen in |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `ANTHROPIC_MODEL` | Claude model ID (default: `claude-sonnet-4-5-20250929`) |
| `PROPOSAL_BOT_ID` | _(Optional)_ Proposal bot's Discord user ID for @mention handoff |

## Data Sources

- `data/pricing.yaml` — 5 products, all tiers, prices, floors, SLAs, commissions, deliverables, pitch hooks
- `data/objections.yaml` — 8 universal objection scripts + per-product scripts for all products

Both files are extracted from the `productsPricing/` docs. Updated by the manager agent at runtime.

## Key Files

| File | Purpose |
|------|---------|
| `pricing_agent/main.py` | Entrypoint — loads config, data, starts bot |
| `pricing_agent/config.py` | Pydantic Settings configuration |
| `pricing_agent/bot.py` | Discord client — routes messages, pins welcome message, backlog guard |
| `pricing_agent/handler.py` | Message handler — conversation flow, /clear, LLM calls |
| `pricing_agent/prompts.py` | Builds system prompt from YAML data |

## Cross-Bot Communication

When `PROPOSAL_BOT_ID` is set, the pricing bot can @mention the proposal bot when a quote is finalized and the rep confirms they want a proposal generated.
