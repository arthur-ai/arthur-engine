# Arthur Engine MCP Server

A Model Context Protocol (MCP) server that integrates Arthur Engine's LLM guardrails with development environments like Cursor IDE.

## Installation

```bash
# Clone the repository and navigate to the MCP server directory
cd mcp-server

poetry self add poetry-plugin-shell
poetry shell && poetry env use 3.12

# Install dependencies
poetry install
```

## Configuration

1. **Copy the environment template:**
   ```bash
   cp env.example .env
   ```

2. **Configure your environment variables in `.env`:**
   ```bash
   GENAI_ENGINE_API_KEY=your_api_key_here
   GENAI_ENGINE_BASEURL=http://localhost:3030
   GENAI_ENGINE_TASK_ID=your_task_id_here
   ```

## Usage

### Running the MCP Server

```bash
fastmcp run arthur_engine_mcp.py:mcp
```

### Use Inspector
# Install
```
npx @modelcontextprotocol/inspector@latest --help
```

Run
```
npx @modelcontextprotocol/inspector@latest python arthur_engine_mcp.py
```

## Integrations

### Cursor
1. Go to `Cursor` -> `Settings` -> `Cursor Settings` -> `Tools & Integrations` -> `New MCP Server` and add the below configuration.
```
{
  "mcpServers": {
    "Arthur Engine": {
      "command": "python",
      "args": ["/Users/nori/github/arthur-engine/mcp-server/arthur_engine_mcp.py"],
      "env": {
        "GENAI_ENGINE_API_KEY": "changeme123",
        "GENAI_ENGINE_BASEURL": "http://localhost:8000",
        "GENAI_ENGINE_TASK_ID": "my_task_id"
      },
      "transport": "stdio"
    }
  }
}
```
2. Make sure the "Arthur Engine" MCP is enabled with more than one tool enabled.
