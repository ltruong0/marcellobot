# MarcelloBot

Discord bot for homelab automation, integrated with n8n workflows.

## Structure

```
marcellobot/
├── src/                    # Bot source code
│   ├── bot.py              # Main entry point
│   ├── config.py           # Configuration
│   ├── commands/           # Slash command handlers
│   └── services/           # n8n client
├── workflows/              # n8n workflow JSON files
├── scripts/                # Sync and utility scripts
├── k8s/                    # Kubernetes manifests
├── Dockerfile
└── requirements.txt
```

## Discord Commands

| Command | Description |
|---------|-------------|
| `/utr [product]` | Check UTR stock status |
| `/home <action> [target]` | Home automation (lights on/off, status) |
| `/status [service]` | Check homelab service health |
| `/trigger <workflow> [data]` | Generic webhook trigger |

## n8n Workflow Sync

Sync workflows between local JSON files and n8n instance. The script is scoped to only manage workflows defined in this repo—other workflows in your n8n instance are not affected.

```bash
# Setup
cd scripts
cp .env.example .env
# Edit .env with your N8N_TOKEN

# Push local workflows to n8n
./n8n-sync.sh push

# Pull updates for workflows managed by this repo
./n8n-sync.sh pull

# Pull ALL workflows from n8n (including unmanaged)
./n8n-sync.sh pull --all

# Pull specific workflow by name
./n8n-sync.sh pull "My Workflow Name"

# List remote workflows (marks managed ones)
./n8n-sync.sh list

# Show differences between local and remote
./n8n-sync.sh diff

# Dry run (preview changes)
DRY_RUN=true ./n8n-sync.sh push
```

## Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Discord token

# Run
python -m src.bot
```

## Deployment

### Build Docker Image

```bash
docker build -t ghcr.io/leetruong/marcellobot:latest .
docker push ghcr.io/leetruong/marcellobot:latest
```

### Deploy to Kubernetes

```bash
cd k8s
cp secret.yaml.example secret.yaml
# Edit secret.yaml with your Discord token

kubectl apply -k .
```

## n8n Webhook Integration

The bot calls n8n webhooks and expects JSON responses:

| Webhook Path | Command | Payload |
|--------------|---------|---------|
| `utr-stock-check` | `/utr` | `{"product": "..."}` |
| `home-control` | `/home` | `{"action": "...", "target": "..."}` |
| `server-status` | `/status` | `{"service": "..."}` |

Expected response format:
```json
{"message": "Response text here"}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | Yes | Bot token from Discord Developer Portal |
| `N8N_BASE_URL` | No | n8n URL (default: https://workflows.marcellolab.com) |
| `N8N_WEBHOOK_SECRET` | No | Optional webhook authentication |
| `N8N_TOKEN` | For sync | n8n API token for workflow sync |
