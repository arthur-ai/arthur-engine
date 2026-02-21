---
name: start-genai-frontend
description: Start the GenAI Engine frontend UI dev server. Use when you need to launch the React app locally.
allowed-tools: Bash, Task
---

# Start GenAI Engine Frontend

Spawn a Task sub-agent with subagent_type="Bash" and the following self-contained prompt:

---
Set up and start the GenAI Engine frontend dev server. Report success or failure for each step.

**Step 1 — Check the backend is reachable (optional, non-blocking):**
```bash
curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer changeme123" http://localhost:3030/health
```
If the response is not 200, warn the user that the backend may not be running and suggest running `/start-genai-backend` first, but continue anyway.

**Step 2 — Install dependencies:**
```bash
cd genai-engine/ui && yarn install
```

**Step 3 — Generate API client bindings:**
```bash
cd genai-engine/ui && yarn generate-api:clean
```

**Step 4 — Start the dev server and capture the URL:**
```bash
cd genai-engine/ui && yarn dev 2>&1 | tee /tmp/vite-fe.log &
sleep 3 && grep -m1 "Local:" /tmp/vite-fe.log
```

Report the Local URL that Vite printed (e.g. `http://localhost:3000`). If the default port was taken, Vite will have chosen a different one.
---
