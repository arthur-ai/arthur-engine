---
name: arthur-onboard-task
description: Arthur onboarding sub-skill — Step 3: Set up an Arthur Task (create or select). Reads/writes .arthur-engine.env.
allowed-tools: Bash, Read, Write, Edit
---

# Arthur Onboard — Step 3: Set Up Arthur Task

**Goal:** Establish `ARTHUR_TASK_ID` in `.arthur-engine.env`.

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, and `ARTHUR_TASK_ID` from the output.

**State write helper:**
```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_TASK_ID=' "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_TASK_ID=$TASK_ID" >> "$STATE_FILE"
```

---

## If ARTHUR_TASK_ID Exists

Confirm reuse with user and exit this skill (task step done).

---

## Select or Create a Task

List existing tasks:
```bash
curl -s \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v2/tasks" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
tasks = d.get('tasks') or d.get('data') or []
tasks = [t for t in tasks if not t.get('is_system_task')]
for t in tasks:
    print(f'  {t[\"id\"]}: {t[\"name\"]}')
"
```

Show the list and ask: "Select an existing task, or create a new one?"

To create a task:
```bash
TASK_ID=$(curl -s -X POST \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$TASK_NAME\"}" \
  "$ARTHUR_ENGINE_URL/api/v2/tasks" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
echo "TASK_ID=$TASK_ID"
```

Save the task ID to the state file.
