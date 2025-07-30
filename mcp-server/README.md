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
