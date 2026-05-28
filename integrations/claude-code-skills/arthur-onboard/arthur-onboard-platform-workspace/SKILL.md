---
name: arthur-onboard-platform-workspace
description: Arthur onboarding sub-skill — Platform Step 3: Select or create a workspace in Arthur Platform. Reads/writes .arthur-engine.env.
allowed-tools: Bash, Read, Write
---

# Arthur Onboard — Platform Step 3: Select or Create Workspace

**Goal:** Establish `ARTHUR_PLATFORM_WORKSPACE_ID` and `ARTHUR_PLATFORM_WORKSPACE_NAME` in `.arthur-engine.env`.

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_PLATFORM_URL`, `ARTHUR_PLATFORM_TOKEN`, `ARTHUR_PLATFORM_WORKSPACE_ID`, and `ARTHUR_PLATFORM_WORKSPACE_NAME` from the output.

**State write helper:**
```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_PLATFORM_WORKSPACE_ID=\|^ARTHUR_PLATFORM_WORKSPACE_NAME=' \
  "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_PLATFORM_WORKSPACE_ID=$WS_ID" >> "$STATE_FILE"
echo "ARTHUR_PLATFORM_WORKSPACE_NAME=$WS_NAME" >> "$STATE_FILE"
```

---

## Ensure Token is Valid

Invoke the `arthur-onboard-platform-token` sub-skill to get a fresh token.

If it outputs `TOKEN_REFRESH=MISSING_CREDENTIALS` or `TOKEN_REFRESH=FAILED`: re-invoke `arthur-onboard-platform-access` to re-authenticate, then resume this skill.

---

## If ARTHUR_PLATFORM_WORKSPACE_ID Exists

Verify the workspace still exists and is accessible:
```bash
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/workspaces/${ARTHUR_PLATFORM_WORKSPACE_ID}" 2>/dev/null || echo "000")
echo "WS_STATUS=$HTTP_STATUS"
```

- `200` → confirm reuse with user ("Use workspace '<ARTHUR_PLATFORM_WORKSPACE_NAME>'?"); if yes, exit this skill
- `401` → token expired; tell user to re-run `arthur-onboard-platform-access` to refresh it, then retry this skill
- `404` → workspace no longer exists; proceed to list/create below
- anything else → warn user, proceed to list/create below

---

## List Existing Workspaces

```bash
WS_RESPONSE=$(curl -s \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/organization/workspaces")
WS_LIST=$(echo "$WS_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
workspaces = d.get('records') or d.get('resources') or d.get('data') or d.get('workspaces') or (d if isinstance(d, list) else [])
for ws in workspaces:
    print(f'  {ws[\"id\"]}: {ws[\"name\"]}')
if not workspaces:
    print('  (no workspaces found)')
" 2>/dev/null || echo "  (error parsing response)")
echo "$WS_LIST"
```

If the response is a 404 or error, try the alternate path:
```bash
WS_RESPONSE=$(curl -s \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/workspaces")
```

Show the list to the user and ask:
> "Which workspace would you like to use? Enter the workspace name or ID, or type **new** to create one."

---

## If User Selects an Existing Workspace

Find the matching workspace from the response and extract its ID and name:
```bash
WS_ID=$(echo "$WS_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
workspaces = d.get('records') or d.get('resources') or d.get('data') or d.get('workspaces') or (d if isinstance(d, list) else [])
for ws in workspaces:
    if ws.get('name') == '$USER_SELECTION' or ws.get('id') == '$USER_SELECTION':
        print(ws['id'])
        break
" 2>/dev/null)
WS_NAME=$(echo "$WS_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
workspaces = d.get('records') or d.get('resources') or d.get('data') or d.get('workspaces') or (d if isinstance(d, list) else [])
for ws in workspaces:
    if ws.get('name') == '$USER_SELECTION' or ws.get('id') == '$USER_SELECTION':
        print(ws['name'])
        break
" 2>/dev/null)
echo "WS_ID=$WS_ID"
echo "WS_NAME=$WS_NAME"
```

Proceed to "Save Workspace to State".

---

## Create New Workspace

Ask the user for the workspace name.

```bash
NEW_WS_RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$WS_NAME\"}" \
  "${ARTHUR_PLATFORM_URL}/api/v1/organization/workspaces")
WS_ID=$(echo "$NEW_WS_RESPONSE" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
WS_NAME=$(echo "$NEW_WS_RESPONSE" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null)
echo "WS_ID=$WS_ID"
echo "WS_NAME=$WS_NAME"
```

If `WS_ID` is empty: show the raw response to debug. If the path returned 404, try `POST /api/v1/workspaces` instead. If creation still fails, ask the user to create the workspace in the platform UI and provide its ID.

---

## Save Workspace to State

```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_PLATFORM_WORKSPACE_ID=\|^ARTHUR_PLATFORM_WORKSPACE_NAME=' \
  "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_PLATFORM_WORKSPACE_ID=$WS_ID" >> "$STATE_FILE"
echo "ARTHUR_PLATFORM_WORKSPACE_NAME=$WS_NAME" >> "$STATE_FILE"
```

Confirm to the user: "Workspace set: **<WS_NAME>** (`<WS_ID>`)"

Exit this skill.
