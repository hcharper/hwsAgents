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
| **Pricing Bot** | `#pricing-agent` | Conversational quoting tool — asks clarifying questions, builds quotes with floors and commission |
| **Manager Bot** | `#agent-admin` | Updates pricing/objection data, manages agent configs |
| **Proposal Bot** | `#proposals` | _(Coming soon)_ Generates client proposals from quotes |

## Discord Commands

| Command | What it does |
|---------|-------------|
| `/clear` | Wipes all messages in the channel (keeps pinned welcome message) |

---

## Discord Setup

### 1. Create Discord Bots

Go to [discord.com/developers/applications](https://discord.com/developers/applications) and create a bot application for each agent:

For each bot:
1. Click **New Application** → name it (e.g. "HWS Pricing Agent")
2. Go to **Bot** in the left sidebar → **Reset Token** → copy it (shown once)
3. Enable **Message Content Intent** under Privileged Gateway Intents → Save
4. Go to **OAuth2 → URL Generator** → check scope: `bot` → check permissions: **Send Messages**, **Read Message History**, **Manage Messages** → copy the generated URL
5. Open the URL in your browser → select your server → Authorize

### 2. Set Up Discord Server Channels

Recommended server structure:

```
AGENTS (category)
├── #pricing-agent      ← pricing bot listens here
├── #proposals          ← proposal bot (future)
└── #agent-admin        ← manager bot listens here

SALES (category)
├── #general
├── #leads
└── #wins

CLIENTS — ACTIVE (category)
├── #client-name-1
├── #client-name-2
└── ...

CLIENTS — ARCHIVE (category)
└── (completed/churned clients)

TEAM (category)
├── #general
└── #engineering
```

### 3. Get Channel IDs

In Discord: **Settings → Advanced → enable Developer Mode**. Then right-click each channel → **Copy Channel ID**.

---

## Hosting on Ubuntu Mac Mini (or any Ubuntu server)

### Initial Server Setup

SSH into your Mac Mini (or connect directly):

```bash
ssh user@your-mac-mini-ip
```

### 1. Install Python 3.10+ and pip

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git
```

### 2. Clone the Repo

```bash
cd ~
git clone git@github.com:hcharper/hwsAgents.git agents
cd agents
```

### 3. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 4. Configure Environment

```bash
cp .env.example .env
nano .env  # or vim .env
```

Fill in:
- `PRICING_BOT_TOKEN` — from Discord Developer Portal (Bot tab → Reset Token)
- `PRICING_CHANNEL_IDS` — right-click channel → Copy Channel ID
- `MANAGER_BOT_TOKEN` — same process, second bot application
- `MANAGER_CHANNEL_IDS` — admin channel ID
- `ANTHROPIC_API_KEY` — from [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)

### 5. Test Manually

```bash
source .venv/bin/activate
python3 -m pricing_agent.main
```

Send a message in your Discord channel. If it responds, you're good. `Ctrl+C` to stop.

### 6. Set Up systemd Services (Run 24/7)

Create a service file for each agent:

**Pricing Agent:**

```bash
sudo tee /etc/systemd/system/hws-pricing.service << 'EOF'
[Unit]
Description=HWS Pricing Agent Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/agents
Environment=PATH=/home/$USER/agents/.venv/bin:/usr/bin
ExecStart=/home/$USER/agents/.venv/bin/python3 -m pricing_agent.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

**Manager Agent:**

```bash
sudo tee /etc/systemd/system/hws-manager.service << 'EOF'
[Unit]
Description=HWS Manager Agent Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/agents
Environment=PATH=/home/$USER/agents/.venv/bin:/usr/bin
ExecStart=/home/$USER/agents/.venv/bin/python3 -m manager_agent.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

**Important:** Replace `$USER` with your actual username in the service files, or run:

```bash
sudo sed -i "s/\$USER/$USER/g" /etc/systemd/system/hws-pricing.service
sudo sed -i "s/\$USER/$USER/g" /etc/systemd/system/hws-manager.service
```

### 7. Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable hws-pricing hws-manager
sudo systemctl start hws-pricing hws-manager
```

### 8. Verify

```bash
sudo systemctl status hws-pricing
sudo systemctl status hws-manager
```

Both should show `active (running)`.

### Useful Commands

```bash
# View live logs
sudo journalctl -u hws-pricing -f
sudo journalctl -u hws-manager -f

# Restart after code changes
sudo systemctl restart hws-pricing
sudo systemctl restart hws-manager

# Stop a bot
sudo systemctl stop hws-pricing

# Check if running
sudo systemctl is-active hws-pricing
```

### Updating (After a git push)

```bash
cd ~/agents
git pull
source .venv/bin/activate
pip install -e .
sudo systemctl restart hws-pricing hws-manager
```

---

## Adding New Agents

1. Create a new directory: `new_agent/` with `__init__.py`, `main.py`, `config.py`, `bot.py`, `handler.py`, `prompts.py`
2. Add a new entrypoint in `pyproject.toml` under `[project.scripts]`
3. Add the package name to `[tool.hatch.build.targets.wheel]` packages list
4. Create a new Discord bot application and channel
5. Add the new bot's token and channel ID to `.env`
6. Create a new systemd service file on the Mac Mini
7. `pip install -e .` and `sudo systemctl start hws-newagent`

## Cross-Bot Communication

The pricing bot can @mention the proposal bot when a quote is finalized. Set `PROPOSAL_BOT_ID` in `.env` to the proposal bot's Discord user ID (visible in Discord after the bot joins — right-click the bot → Copy User ID).

## Cost (Claude Sonnet 4.5 with prompt caching)

- ~$0.02 per request (system prompt cached at 10x discount)
- ~100 requests/day = ~$60/month
- Switch `ANTHROPIC_MODEL` to `claude-haiku-4-5-20251001` for ~$15/month

## Testing

```bash
pip install -e ".[dev]"
python3 -m pytest tests/ -v
```
