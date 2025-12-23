#!/bin/bash

# Script to create unregistered agents from traces
# Usage: ./create_unregistered_agent.sh <trace_id> [--bearer-token <token>]
#
# Examples:
#   ./create_unregistered_agent.sh "550e8400-e29b-41d4-a716-446655440000"
#   ./create_unregistered_agent.sh "550e8400-e29b-41d4-a716-446655440000" --bearer-token "eyJhbGc..."
#
# Configuration is loaded from .env file in the same directory

set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

# Load .env file
if [ ! -f "${ENV_FILE}" ]; then
  echo "Error: .env file not found at ${ENV_FILE}" >&2
  echo "Please create a .env file based on .env.example" >&2
  exit 1
fi

# Source the .env file
set -a
source "${ENV_FILE}"
set +a

# Validate required environment variables
REQUIRED_VARS=(
  "ARTHUR_BASE_URL"
  "ARTHUR_API_KEY"
  "ARTHUR_CLIENT_ID"
  "ARTHUR_CLIENT_SECRET"
  "WORKSPACE_ID"
  "DATA_PLANE_ID"
  "API_BASE_URL"
  "INFRASTRUCTURE"
)

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "Error: Required environment variable ${var} is not set in .env file" >&2
    exit 1
  fi
done

# Parse arguments
TRACE_ID=""
BEARER_TOKEN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bearer-token)
      BEARER_TOKEN="$2"
      shift 2
      ;;
    *)
      if [ -z "${TRACE_ID}" ]; then
        TRACE_ID="$1"
        shift
      else
        echo "Error: Unknown argument: $1" >&2
        exit 1
      fi
      ;;
  esac
done

if [ -z "${TRACE_ID}" ]; then
  echo "Usage: $0 <trace_id> [--bearer-token <token>]" >&2
  echo "" >&2
  echo "Examples:" >&2
  echo "  $0 550e8400-e29b-41d4-a716-446655440000" >&2
  echo "  $0 550e8400-e29b-41d4-a716-446655440000 --bearer-token \"eyJhbGc...\"" >&2
  exit 1
fi

UNREGISTERED_AGENTS_URL="${API_BASE_URL}/api/v1/workspaces/${WORKSPACE_ID}/unregistered_agents"

get_platform_token() {
  # Get bearer token for Arthur Platform API using OIDC
  echo "Fetching platform authentication token..." >&2
  
  # First, get the OIDC configuration to find the token endpoint
  local oidc_config
  oidc_config=$(curl -s "${API_BASE_URL}/api/v1/auth/oidc/.well-known/openid-configuration")
  
  local token_endpoint
  token_endpoint=$(echo "${oidc_config}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token_endpoint', ''))" 2>/dev/null)
  
  if [ -z "${token_endpoint}" ]; then
    echo "Error: Failed to get OIDC token endpoint" >&2
    echo "Response: ${oidc_config}" >&2
    exit 1
  fi
  
  # If running in Docker and token_endpoint uses localhost, replace with host.docker.internal
  if [[ "${token_endpoint}" =~ localhost ]] && [[ "${API_BASE_URL}" =~ host\.docker\.internal ]]; then
    token_endpoint="${token_endpoint//localhost/host.docker.internal}"
    echo "Adjusted token endpoint for Docker: ${token_endpoint}" >&2
  fi
  
  # Get the access token using client credentials grant
  local token_response
  token_response=$(curl -s -X POST "${token_endpoint}" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials&client_id=${ARTHUR_CLIENT_ID}&client_secret=${ARTHUR_CLIENT_SECRET}")
  
  local token
  token=$(echo "${token_response}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
  
  if [ -z "${token}" ]; then
    echo "Error: Failed to get platform authentication token" >&2
    echo "Response: ${token_response}" >&2
    exit 1
  fi
  
  echo "${token}"
}

fetch_trace() {
  local trace_id="$1"
  
  echo "Fetching trace ${trace_id} from Arthur Engine..." >&2
  
  local trace_response
  trace_response=$(curl -s -X GET "${ARTHUR_BASE_URL}/api/v1/traces/${trace_id}" \
    -H "Authorization: Bearer ${ARTHUR_API_KEY}" \
    -H "Content-Type: application/json")
  
  if [ -z "${trace_response}" ] || echo "${trace_response}" | grep -q '"detail".*"Not Found"'; then
    echo "Error: Failed to fetch trace ${trace_id}" >&2
    echo "Response: ${trace_response}" >&2
    exit 1
  fi
  
  echo "${trace_response}"
}

fetch_spans_by_task() {
  local task_id="$1"
  local trace_id="$2"
  
  echo "Fetching spans for trace ${trace_id} (task ${task_id}) from Arthur Engine..." >&2
  
  # Encode parameters for the URL
  local encoded_task_id encoded_trace_id
  encoded_task_id=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$task_id'))")
  encoded_trace_id=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$trace_id'))")
  
  # Fetch with larger page_size to ensure we get all spans (including tools)
  # Default page_size is 10 which often misses tool spans
  local spans_response
  spans_response=$(curl -s -X GET "${ARTHUR_BASE_URL}/api/v1/traces/spans?task_ids=${encoded_task_id}&trace_id=${encoded_trace_id}&page_size=1000" \
    -H "Authorization: Bearer ${ARTHUR_API_KEY}" \
    -H "Content-Type: application/json")
  
  if [ -z "${spans_response}" ] || echo "${spans_response}" | grep -q '"detail"'; then
    echo "Error: Failed to fetch spans for trace ${trace_id}" >&2
    echo "Response: ${spans_response}" >&2
    exit 1
  fi
  
  # Filter to only spans for the specific trace_id and report statistics
  local filtered_response
  filtered_response=$(echo "${spans_response}" | python3 -c "
import sys, json
from collections import Counter

data = json.load(sys.stdin)
all_spans = data.get('spans', [])
trace_id = '${trace_id}'

# Filter to only spans for this specific trace
trace_spans = [s for s in all_spans if s.get('trace_id') == trace_id]

# Report statistics
kinds = Counter(s.get('span_kind') for s in trace_spans)
print(f'Found {len(trace_spans)} spans for trace:', file=sys.stderr)
for kind, count in sorted(kinds.items()):
    print(f'  {kind}: {count}', file=sys.stderr)

# Output filtered data in the same format
output = {'spans': trace_spans, 'count': len(trace_spans)}
print(json.dumps(output))
")
  
  echo "${filtered_response}"
}

build_span_agent_payload_from_spans() {
  # Reads a spans JSON blob on stdin and emits the PUT body JSON on stdout.
  python3 -c "$(cat <<'PY'
import json
import os
import sys
from datetime import datetime, timezone

raw = sys.stdin.read().strip()
if not raw:
  raise SystemExit("No spans JSON provided on stdin")

data = json.loads(raw)
spans = data.get("spans") or []

def parse_dt(s: str):
  # Accept "2025-12-05T18:42:57.049000" or "...Z"
  if not s:
    return None
  try:
    if s.endswith("Z"):
      return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
  except Exception:
    return None

span_ids = {s.get("span_id") for s in spans if s.get("span_id")}

root_candidates = []
for s in spans:
  parent = s.get("parent_span_id")
  # root if parent is missing OR parent not in the set we were given
  if not parent or parent not in span_ids:
    root_candidates.append(s)

def sort_key(s):
  dt = parse_dt(s.get("start_time") or "")
  return (dt or datetime.max.replace(tzinfo=timezone.utc), s.get("span_id") or "")

root = None
if root_candidates:
  root = sorted(root_candidates, key=sort_key)[0]
elif spans:
  root = sorted(spans, key=sort_key)[0]

top_level_span_name = (root or {}).get("span_name") or "unknown"

def normalize_quoted(prefix: str, name: str):
  # e.g. "tool: 'generateGraphTool'" -> "generateGraphTool"
  if not name:
    return None
  n = name.strip()
  if n.startswith(prefix):
    n = n[len(prefix):].strip()
  if (len(n) >= 2) and ((n[0] == "'" and n[-1] == "'") or (n[0] == '"' and n[-1] == '"')):
    n = n[1:-1]
  return n.strip() or None

def dedupe_preserve_order(items):
  seen = set()
  out = []
  for x in items:
    if not x or x in seen:
      continue
    seen.add(x)
    out.append(x)
  return out

agent_names = []
tool_names = []
tool_args_by_name = {}
for s in spans:
  kind = (s.get("span_kind") or "").upper()
  span_name = s.get("span_name") or ""

  if kind == "AGENT" or span_name.startswith("agent run:"):
    n = span_name
    if span_name.startswith("agent run:"):
      n = normalize_quoted("agent run:", span_name)
    agent_names.append(n or span_name)

  if kind == "TOOL" or span_name.startswith("tool:"):
    n = span_name
    if span_name.startswith("tool:"):
      n = normalize_quoted("tool:", span_name)
    tool_name = n or span_name
    tool_names.append(tool_name)

    # Try to derive tool argument names from input_content when available.
    raw_input = s.get("input_content")
    args_obj = None
    if isinstance(raw_input, str) and raw_input.strip():
      try:
        parsed = json.loads(raw_input)
        if isinstance(parsed, dict):
          if isinstance(parsed.get("args"), dict):
            args_obj = parsed.get("args")
          elif isinstance(parsed.get("toolInput"), dict):
            args_obj = parsed.get("toolInput")
          else:
            args_obj = parsed
      except Exception:
        args_obj = None

    if isinstance(args_obj, dict):
      tool_args_by_name.setdefault(tool_name, {})
      for k, v in args_obj.items():
        if not isinstance(k, str):
          continue
        if v is None:
          t = "null"
        elif isinstance(v, bool):
          t = "boolean"
        elif isinstance(v, (int, float)):
          t = "number"
        elif isinstance(v, str):
          t = "string"
        elif isinstance(v, list):
          t = "array"
        elif isinstance(v, dict):
          t = "object"
        else:
          t = "unknown"
        tool_args_by_name[tool_name].setdefault(k, t)

agent_names = dedupe_preserve_order(agent_names)
tool_names = dedupe_preserve_order(tool_names)

first_detected = (root or {}).get("start_time")
if first_detected and not str(first_detected).endswith("Z"):
  first_detected = f"{first_detected}Z"
if not first_detected:
  first_detected = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

num_spans = len(spans)

infrastructure = os.environ.get("INFRASTRUCTURE") or "Kubernetes"
data_plane_id = os.environ.get("DATA_PLANE_ID") or "00000000-0000-0000-0000-000000000000"

payload = {
  "unregistered_agents": [
    {
      "name": f"Unregistered Agent: {top_level_span_name}",
      "creation_source": {"top_level_span_name": top_level_span_name},
      "first_detected": first_detected,
      "infrastructure": infrastructure,
      "data_plane_id": data_plane_id,
      "num_spans": num_spans,
      "tools": [
        {
          "name": t,
          "arguments": [
            {"name": arg_name, "type": arg_type}
            for arg_name, arg_type in sorted(tool_args_by_name.get(t, {}).items())
          ],
        }
        for t in tool_names
      ],
      "sub_agents": [{"name": a} for a in agent_names],
    }
  ]
}

print(json.dumps(payload))
PY
)"
}

create_agent_from_trace() {
  local trace_id="$1"
  local bearer_token="$2"
  
  # Fetch trace data
  local trace_data
  trace_data=$(fetch_trace "${trace_id}")
  
  # Extract task_id from trace
  local task_id
  task_id=$(echo "${trace_data}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # Check if task_id is in the root_spans
    if data.get('root_spans') and len(data['root_spans']) > 0:
        task_id = data['root_spans'][0].get('task_id')
        if task_id:
            print(task_id)
        else:
            print('', file=sys.stderr)
            sys.exit(1)
    else:
        print('', file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1)
  
  if [ -z "${task_id}" ] || [ "${task_id}" = "None" ]; then
    echo "Error: Could not extract task_id from trace" >&2
    echo "Trace data: ${trace_data}" >&2
    exit 1
  fi
  
  echo "Task ID: ${task_id}" >&2
  
  # Fetch spans data using task_id
  local spans_data
  spans_data=$(fetch_spans_by_task "${task_id}" "${trace_id}")
  
  echo "Building unregistered agent payload from spans..." >&2
  
  # Build the payload from spans
  local body
  if ! body="$(printf "%s" "${spans_data}" | build_span_agent_payload_from_spans)"; then
    echo "Error: Failed to build unregistered agent payload from spans" >&2
    exit 1
  fi
  
  # Set task_id as the creation source (remove top_level_span_name since we can only have one)
  body=$(echo "${body}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('unregistered_agents') and len(data['unregistered_agents']) > 0:
    creation_source = data['unregistered_agents'][0]['creation_source']
    # API requires exactly one of task_id or top_level_span_name
    # Since this trace has a task_id, use that as the primary source
    creation_source['task_id'] = '${task_id}'
    # Remove top_level_span_name since we can't have both
    if 'top_level_span_name' in creation_source:
        del creation_source['top_level_span_name']
    # Note: trace_id can be included if supported, but it's optional
    creation_source['trace_id'] = '${trace_id}'
print(json.dumps(data))
")
  
  if [ "${DRY_RUN:-0}" = "1" ]; then
    echo "DRY RUN - Would create agent with payload:" >&2
    printf "%s\n" "${body}"
    echo -e "\n"
    return 0
  fi
  
  echo "Creating unregistered agent in platform..." >&2
  
  local response
  response=$(curl -s -w "\n%{http_code}" -X PUT "${UNREGISTERED_AGENTS_URL}" \
    -H "Authorization: Bearer ${bearer_token}" \
    -H "Content-Type: application/json" \
    -d "${body}")
  
  local http_code
  http_code=$(echo "${response}" | tail -n1)
  local response_body
  response_body=$(echo "${response}" | sed '$d')
  
  if [ "${http_code}" -ge 200 ] && [ "${http_code}" -lt 300 ]; then
    echo "✓ Successfully created unregistered agent!" >&2
    echo "${response_body}"
  else
    echo "Error: Failed to create unregistered agent (HTTP ${http_code})" >&2
    echo "Response: ${response_body}" >&2
    exit 1
  fi
}

# Main execution
echo "=== Creating Unregistered Agent from Trace ===" >&2
echo "Trace ID: ${TRACE_ID}" >&2
echo "Engine: ${ARTHUR_BASE_URL}" >&2
echo "Platform: ${API_BASE_URL}" >&2
echo "Workspace: ${WORKSPACE_ID}" >&2
echo "" >&2

# Get platform authentication token (if not provided)
if [ -z "${BEARER_TOKEN}" ]; then
  BEARER_TOKEN=$(get_platform_token)
else
  echo "Using provided bearer token" >&2
fi

# Create the agent
create_agent_from_trace "${TRACE_ID}" "${BEARER_TOKEN}"

echo "" >&2
echo "=== Done ===" >&2
