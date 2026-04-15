# Proposal Agent

**Channel:** `#proposals`
**Bot name:** HWS Proposal Bot
**Entry point:** `python3 -m proposal_agent.main`

## What It Does

Interactive proposal generator. Walks through a conversational flow to gather project requirements, pulls pricing from the pricing bot, drafts a professional PDF proposal, and allows revisions before finalizing.

## How It Works (State Machine)

The agent follows a 6-state conversation flow:

1. **IDLE** → User sends first message → transitions to GATHERING
2. **GATHERING** → Bot asks conversational questions about the project (name, client, goals, features, tech stack, timeline, budget, deliverables). When enough info is collected, transitions to WAITING_FOR_PRICING.
3. **WAITING_FOR_PRICING** → Bot @mentions the pricing bot to get a quote. Waits up to 60 seconds for a response.
4. **DRAFTING** → Bot generates a complete proposal JSON using Claude with all gathered details + pricing data.
5. **REVIEW** → Bot displays the draft as a Discord embed + PDF attachment. User can:
   - `approve` / `yes` / `done` → finalize
   - `cancel` / `start over` → discard and reset
   - Any other message → apply revisions and regenerate
6. **FINALIZED** → Final PDF sent. Ready for next proposal.

## Commands

No explicit slash commands — the bot uses conversational keywords:

| Keyword (in Review state) | Action |
|--------------------------|--------|
| `approve`, `looks good`, `finalize`, `done`, `yes` | Finalize the proposal |
| `cancel`, `start over`, `reset` | Discard and start fresh |
| Anything else | Apply as revision feedback |

## Configuration

| Env Var | Description |
|---------|-------------|
| `DISCORD_BOT_TOKEN` | Discord bot token for proposal bot |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `PROPOSAL_CHANNEL_ID` | Channel ID where the bot listens |
| `PRICING_BOT_ID` | Pricing bot's Discord user ID (for @mention requests) |
| `CLAUDE_MODEL` | _(Optional)_ Model ID (default: `claude-sonnet-4-20250514`) |
| `PRICING_TIMEOUT_SECONDS` | _(Optional)_ How long to wait for pricing bot response (default: 60) |

## Cross-Bot Communication

The proposal bot @mentions the pricing bot to request pricing. The pricing bot's response is parsed to extract line items and totals, which get included in the generated proposal.

Flow:
1. Pricing agent finalizes a quote, @mentions proposal bot
2. — OR — user starts a conversation in `#proposals` directly
3. Proposal bot gathers requirements, @mentions pricing bot for numbers
4. Pricing bot responds with a quote
5. Proposal bot incorporates the quote into the PDF proposal

## Output

Generates a branded PDF proposal using ReportLab with:
- Project overview and goals
- Scope and deliverables
- Timeline with phases
- Pricing table (from pricing bot)
- Terms and conditions

## Key Files

| File | Purpose |
|------|---------|
| `proposal_agent/main.py` | Entrypoint |
| `proposal_agent/config.py` | Environment configuration |
| `proposal_agent/client.py` | Discord bot (ProposalBot) |
| `proposal_agent/handlers/conversation.py` | State machine driving the conversation flow |
| `proposal_agent/handlers/pricing.py` | @mention pricing bot and parse response |
| `proposal_agent/services/claude.py` | Anthropic API calls for gathering, drafting, revisions |
| `proposal_agent/services/proposal.py` | Data classes (Proposal, TimelinePhase, PricingLineItem) |
| `proposal_agent/services/pdf.py` | PDF generation with ReportLab |
| `proposal_agent/utils/context.py` | Per-channel conversation state management |
| `proposal_agent/templates/proposal_prompt.txt` | System prompt template |

## Dependencies

Requires `reportlab` in addition to the shared dependencies:
```bash
pip install reportlab
```
