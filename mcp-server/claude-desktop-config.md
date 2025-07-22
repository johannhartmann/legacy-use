# Claude Desktop Configuration for Legacy-Use MCP Server

This guide explains how to configure Claude Desktop to use the Legacy-Use MCP server.

## Prerequisites

1. Claude Desktop installed
2. Legacy-Use running with the MCP server
3. Python 3.10+ installed on your system

## Configuration Steps

### 1. HTTP Streaming Transport (Recommended)

The MCP server uses **HTTP streaming transport** and runs on port 3000 when deployed with Kubernetes. 

**Connection URL**: `http://localhost:3000/mcp`

This is the modern approach that replaces outdated SSE (Server-Sent Events).

### 2. For Local Development

If you need to run the MCP server locally for development:

```bash
cd mcp-server
pip install -e .
```

### 3. Configure Claude Desktop (STDIO Transport)

For local desktop integration using STDIO transport, add the following configuration:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "legacy-use": {
      "command": "python",
      "args": ["-m", "legacy_use_mcp_server"],
      "cwd": "/path/to/legacy-use/mcp-server",
      "env": {
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/legacy_use_demo",
        "LEGACY_USE_URL": "http://localhost:8088",
        "LEGACY_USE_API_KEY": "your-api-key-here",
        "LOG_LEVEL": "INFO",
        "SYNC_INTERVAL": "30"
      }
    }
  }
}
```

### 3. Alternative: Using Docker

If you prefer to run the MCP server via Docker:

```json
{
  "mcpServers": {
    "legacy-use": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--network", "host",
        "-e", "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/legacy_use_demo",
        "-e", "LEGACY_USE_URL=http://localhost:8088",
        "-e", "LEGACY_USE_API_KEY=your-api-key-here",
        "legacy-use-mcp-server:local"
      ]
    }
  }
}
```

### 4. Get Your API Key

Generate an API key for the Legacy-Use backend:

```bash
cd /path/to/legacy-use
uv run python generate_api_key.py
```

Replace `your-api-key-here` in the configuration with the generated key.

### 5. Verify Connection

1. Restart Claude Desktop
2. In a new conversation, type: "What Legacy-Use APIs are available?"
3. Claude should list all available APIs from your Legacy-Use instance

## Usage Examples

Once configured, you can use Legacy-Use APIs in Claude Desktop:

```
User: "List all Legacy-Use APIs"
Claude: [Uses list_legacy_use_apis tool to show available APIs]

User: "Use the GnuCash API to read account information"
Claude: [Uses the gnucash_read_account_information tool]

User: "Add a new invoice to GnuCash with amount 500"
Claude: [Uses the gnucash_add_new_invoice tool with parameters]
```

## Troubleshooting

### MCP Server Not Appearing

1. Check the Claude Desktop logs:
   - macOS: `~/Library/Logs/Claude/`
   - Windows: `%LOCALAPPDATA%\Claude\logs\`
   - Linux: `~/.local/share/Claude/logs/`

2. Verify the MCP server runs standalone:
   ```bash
   cd mcp-server
   DATABASE_URL=postgresql://... python -m src
   ```

### Connection Issues

1. Ensure Legacy-Use is running and accessible
2. Verify the database URL is correct
3. Check that the API key is valid
4. Ensure ports 8088 (Legacy-Use) and 5432 (PostgreSQL) are accessible

### API Changes Not Reflected

The MCP server polls for changes every 30 seconds by default. You can:
1. Wait for the sync interval
2. Restart the MCP server
3. Decrease SYNC_INTERVAL in the configuration

## Security Notes

- Keep your API key secure
- Use environment variables or secure storage for sensitive data
- Consider using SSH tunnels for remote Legacy-Use instances
- The MCP server has read-only access to the database