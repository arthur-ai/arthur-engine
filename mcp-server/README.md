# Arthur Engine MCP Server

MCP server for [Arthur Engine](https://www.arthur.ai) — an AI/ML monitoring and governance platform.

For full documentation, visit [docs.arthur.ai](https://docs.arthur.ai/).

## Tools

### search_arthur_api
Search for Arthur Engine API endpoints by keyword. Use this to find the right endpoint and its required parameters before calling it.

### list_tasks
List and search tasks (use cases) in Arthur Engine. Supports filtering by name, IDs, agentic status, and archived status with pagination.

### call_arthur_api
Call an Arthur Engine API endpoint directly. Supports GET, POST, PUT, PATCH, and DELETE (DELETE restricted to tag endpoints only).

## Prerequisites
- Python version >= 3.12

## Setup

1. Install uv
- On Mac
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
- On Windows
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

1. In your `claude_desktop_config.json` file (likely located at `~/Library/Application Support/Claude/claude_desktop_config.json`) add this to the file:
```json
"mcpServers": {
   "arthur-engine": {
   "command": "uv",
   "args": ["run", "--script", "/full_path/to/arthur_engine_mcp.py"],
   "env": {
      "GENAI_ENGINE_MCP_API_KEY": "<your-api-key>",
      "GENAI_ENGINE_BASEURL": "<url_where_engine_is_hosted>"
   }
   }
}
```
making sure to update the values for GENAI_ENGINE_MCP_API_KEY and GENAI_ENGINE_BASEURL with the appropriate parameters

## Configuration

| Secret | Environment Variable | Description |
|--------|---------------------|-------------|
| API Key | `GENAI_ENGINE_MCP_API_KEY` | Your Arthur Engine API key |
| Base URL | `GENAI_ENGINE_BASEURL` | URL where Arthur Engine is hosted |
