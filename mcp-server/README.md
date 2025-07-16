# Legacy-Use MCP Server

This MCP (Model Context Protocol) server provides access to Legacy-Use APIs as tools that can be used by Claude Desktop and other MCP-compatible clients.

## Features

- Automatically discovers and exposes all Legacy-Use APIs as MCP tools
- Real-time synchronization with API changes
- Supports all API parameters and response formats
- Direct database connection for API discovery

## Installation

```bash
pip install -e .
```

## Configuration

Create a `.env` file with the following variables:

```env
# Legacy-Use database connection
DATABASE_URL=postgresql://legacy_use:password@localhost:5432/legacy_use

# MCP server settings (optional)
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=3000

# Sync interval in seconds (default: 30)
SYNC_INTERVAL=30
```

## Usage

### Running the Server

```bash
python -m legacy_use_mcp_server
```

### Using with Claude Desktop

Add the following to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "legacy-use": {
      "command": "python",
      "args": ["-m", "legacy_use_mcp_server"],
      "cwd": "/path/to/mcp-server"
    }
  }
}
```

## Architecture

The MCP server consists of three main components:

1. **Database Monitor**: Watches for changes to API definitions
2. **API-to-Tool Converter**: Transforms Legacy-Use APIs into MCP tools
3. **MCP Server**: Exposes tools via the Model Context Protocol

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
ruff check src/
```