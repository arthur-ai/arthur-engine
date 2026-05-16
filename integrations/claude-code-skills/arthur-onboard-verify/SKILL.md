---
name: arthur-onboard-verify
description: Arthur onboarding sub-skill — Step 7: Verify that traces are flowing from the instrumented application to Arthur Engine. Reads credentials from .arthur-engine.env.
allowed-tools: Bash, Read
---

# Arthur Onboard — Step 7: Verify Instrumentation

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_ENGINE_URL`, `ARTHUR_API_KEY`, `ARTHUR_TASK_ID`.

---

## Tell the User to Run Their Application

Show the required env vars for their platform:

```
# Mac / Linux:
  export ARTHUR_API_KEY=<ARTHUR_API_KEY>
  export ARTHUR_BASE_URL=<ARTHUR_ENGINE_URL>
  export ARTHUR_TASK_ID=<ARTHUR_TASK_ID>

# Windows PowerShell:
  $env:ARTHUR_API_KEY  = "<ARTHUR_API_KEY>"
  $env:ARTHUR_BASE_URL = "<ARTHUR_ENGINE_URL>"
  $env:ARTHUR_TASK_ID  = "<ARTHUR_TASK_ID>"

# Windows CMD:
  set ARTHUR_API_KEY=<ARTHUR_API_KEY>
  set ARTHUR_BASE_URL=<ARTHUR_ENGINE_URL>
  set ARTHUR_TASK_ID=<ARTHUR_TASK_ID>
```

---

## Poll for Traces

Once the user confirms they've run the app, poll for traces (up to 60 seconds):
```bash
for i in $(seq 1 20); do
  COUNT=$(curl -s \
    -H "Authorization: Bearer $ARTHUR_API_KEY" \
    "$ARTHUR_ENGINE_URL/api/v1/traces?task_ids=$ARTHUR_TASK_ID&page_size=5" | \
    python3 -c "
import sys, json
d = json.load(sys.stdin)
print(len(d.get('traces') or d.get('data') or []))
" 2>/dev/null || echo "0")
  if [ "$COUNT" -gt "0" ]; then
    echo "TRACES_FOUND=$COUNT"; break
  fi
  echo "No traces yet... attempt $i/20"
  sleep 3
done
```

**Traces found:** Confirm success and exit this skill.

**No traces after 60s:** Provide troubleshooting guidance:
1. Check env vars are set correctly in the app
2. Confirm the app made actual LLM calls during the test run
3. Verify Arthur Engine is running: `curl $ARTHUR_ENGINE_URL/health`
4. Check the app logs for errors related to OpenTelemetry or Arthur SDK

Offer to retry. This step is non-blocking.
