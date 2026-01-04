# MarcelloBot

Discord bot for homelab automation, integrating with n8n workflows.

## Architecture

- **Discord Bot**: Python bot using discord.py, handles slash commands
- **n8n**: Workflow automation backend at `https://workflows.marcellolab.com`

## Discord Channel Conventions

| Channel | Purpose |
|---------|---------|
| `#logs` | All workflow execution logs, errors, and status updates |
| `#ubiquiti-stock-alerts` | Stock availability alerts for Ubiquiti products |

The bot auto-creates channels if they don't exist.

## n8n Workflow Management

### Workflow Sync

Workflows are stored in `workflows/` as JSON files. Use the sync script:

```bash
# Push local workflows to n8n
./scripts/n8n-sync.sh push

# Pull workflows from n8n to local
./scripts/n8n-sync.sh pull

# List remote workflows
./scripts/n8n-sync.sh list

# Preview changes without applying
DRY_RUN=true ./scripts/n8n-sync.sh push
```

### Creating n8n Workflows

Workflow JSON files in `workflows/` follow this structure:

```json
{
  "name": "Workflow Name",
  "nodes": [...],
  "connections": {...},
  "settings": { "executionOrder": "v1" }
}
```

### Webhook-Triggered Workflows

For Discord command integration, use webhook triggers:

```json
{
  "parameters": {
    "httpMethod": "POST",
    "path": "workflow-name",
    "responseMode": "responseNode",
    "options": {}
  },
  "name": "Webhook",
  "type": "n8n-nodes-base.webhook",
  "typeVersion": 2
}
```

Access webhook data in Code nodes: `$('Webhook').first().json.body`

### Responding to Webhooks

Use `respondToWebhook` node to return data to the Discord bot:

```json
{
  "parameters": {
    "respondWith": "json",
    "responseBody": "={ \"success\": true, \"message\": \"...\", \"data\": {...} }"
  },
  "type": "n8n-nodes-base.respondToWebhook"
}
```

### Common Node Patterns

**HTTP Request** - Fetch external data:
```json
{
  "parameters": {
    "url": "={{ $json.body.url }}",
    "options": { "response": { "response": { "responseFormat": "text" } } }
  },
  "type": "n8n-nodes-base.httpRequest"
}
```

**Code Node** - Process data with JavaScript:
```json
{
  "parameters": {
    "jsCode": "const input = $input.first().json;\n// Process and return\nreturn [{ json: { result: ... } }];"
  },
  "type": "n8n-nodes-base.code"
}
```

**If Node** - Conditional branching:
```json
{
  "parameters": {
    "conditions": {
      "conditions": [{
        "leftValue": "={{ $json.fieldName }}",
        "rightValue": true,
        "operator": { "type": "boolean", "operation": "equals" }
      }]
    }
  },
  "type": "n8n-nodes-base.if"
}
```

### Workflow Response Format

Workflows should return consistent JSON to the Discord bot:

```json
{
  "success": true,
  "message": "Human-readable message for Discord",
  "data": { ... }
}
```

On error:
```json
{
  "success": false,
  "error": true,
  "message": "Error description"
}
```

## Discord Bot Integration

### Webhook Pattern

Commands trigger n8n workflows via webhooks:

```python
result = await self.n8n.trigger_webhook("workflow-name", payload)
```

Webhook endpoint: `{N8N_BASE_URL}/webhook/{workflow-name}`

### Standard Payload Fields

When triggering workflows, include:
- `url`: Resource URL (if applicable)
- `guild_id`: Discord server ID (for callbacks)
- `logs_channel`: Channel name for logs (default: `logs`)
- `alerts_channel`: Channel name for alerts (workflow-specific)

### Logging Guidelines

1. **Log workflow start**: When a command initiates a workflow
2. **Log errors**: Any failures or exceptions
3. **Log completion**: When workflows finish successfully

Use `log_to_channel()` helper:

```python
await self.log_to_channel(guild, "`[Tag]` Message here")
```

### Alert Channels

Create workflow-specific alert channels: `{category}-{type}-alerts`

Examples:
- `ubiquiti-stock-alerts`
- `plex-media-alerts`
- `network-status-alerts`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | Discord bot token |
| `N8N_BASE_URL` | n8n instance URL |
| `N8N_TOKEN` | n8n API token (for workflow sync) |
| `N8N_WEBHOOK_SECRET` | Optional webhook authentication |

## Adding New Commands

1. Create command file in `src/commands/`
2. Define channel constants at top of file
3. Use `get_or_create_channel()` for dynamic channel creation
4. Log all workflow activity to `#logs`
5. Register in `src/bot.py` setup_hook
6. **Update `src/commands/help.py`** to include the new command in the help embed

## Adding New Workflows

1. Create workflow JSON in `workflows/`
2. Use webhook trigger with path matching the Discord command
3. Return structured JSON response
4. Push to n8n: `./scripts/n8n-sync.sh push`
5. Activate workflow in n8n UI
