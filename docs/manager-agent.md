# Manager Agent

**Channel:** `#agent-admin`
**Bot name:** HWS Manager Bot
**Entry point:** `python3 -m manager_agent.main`
**CLI:** `hws-manager`

## What It Does

Admin-only control center for all HWS Discord agents. Lets admins (Harrison + brother) update pricing data, objection scripts, and agent configurations via plain-text instructions. Also tracks API usage and cost across all agents.

## How It Works

### Data Updates
1. Admin types a plain-text instruction (e.g. "Raise the SEO audit price to $199")
2. Bot sends the instruction to Claude, which returns a structured JSON change description
3. Bot shows the proposed change (old value → new value) and asks for confirmation
4. Admin types `yes` to apply or `no` to cancel
5. Bot creates a timestamped backup of the YAML file, then writes the update
6. All agents using that data pick up the changes on their next message — no restart needed

### Usage Tracking
The `/usage` command shows real-time API spend across all agents, broken down by:
- Requests per agent
- Token counts (input, output, cache read, cache write)
- Dollar cost calculated from Anthropic's per-model pricing

## Commands

| Command | Description |
|---------|-------------|
| `/clear` | Wipes all messages (except pinned) and resets conversation memory |
| `/usage` | Shows API cost breakdown for the current month |
| `/usage 2026-03` | Shows API cost breakdown for a specific month |

## Example Interactions

**Updating pricing:**
> "Change the SEO audit price to $199"
>
> **Proposed Change:**
> - **Field:** `products[0].price`
> - **Old:** 149
> - **New:** 199
> - **Summary:** Updated AI SEO + GEO Audit price from $149 to $199
>
> Type **yes** to confirm or **no** to cancel.

**Viewing data:**
> "Show me current website pricing"

**Checking usage:**
> `/usage`
>
> **API Usage — 2026-04**
>
> **pricing_agent** (claude-sonnet-4-5-20250929)
>   Requests: 47
>   Tokens: 412,000 in / 18,500 out
>   Cache: 380,000 read / 32,000 write
>   Cost: **$1.24**
>
> **Total: $1.24** across 47 requests

## Configuration

| Env Var | Description |
|---------|-------------|
| `MANAGER_BOT_TOKEN` | Discord bot token |
| `MANAGER_CHANNEL_IDS` | Comma-separated admin channel IDs |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `ANTHROPIC_MODEL` | Claude model ID (default: `claude-sonnet-4-5-20250929`) |

## Safety

- Always shows old → new values before writing
- Requires explicit confirmation (`yes` / `no`)
- Creates timestamped `.bak` files before every write
- Cannot delete entire products — only update fields

## Key Files

| File | Purpose |
|------|---------|
| `manager_agent/main.py` | Entrypoint — loads config, data, usage tracker, starts bot |
| `manager_agent/config.py` | Pydantic Settings configuration |
| `manager_agent/bot.py` | Discord client — routes messages |
| `manager_agent/handler.py` | Message handler — /clear, /usage, data updates with confirmation flow |
| `manager_agent/prompts.py` | Builds system prompt with current pricing data |

## Future Expansion

The manager agent is designed to grow into a control plane for all HWS agents:
- Edit system prompts and config files for other agents
- Restart or reconfigure agents
- Manage cross-agent workflows
- Control agent permissions and channel assignments
