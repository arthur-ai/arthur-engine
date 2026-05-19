---
name: arthur-onboard-platform-engine
description: Arthur onboarding sub-skill — Platform Step 4: Ensure an Arthur Engine (data plane) is registered and active in the selected workspace. Reads/writes .arthur-engine.env.
allowed-tools: Bash, Read, Write, Task
---

# Arthur Onboard — Platform Step 4: Ensure Arthur Engine Is Registered

**Goal:** Establish `ARTHUR_PLATFORM_ENGINE_ID` and `ARTHUR_PLATFORM_ENGINE_URL` in `.arthur-engine.env`.

> **Important:** Arthur GenAI Engines installed with `arthur-onboard-oss` are **not compatible** with the Arthur Platform. Platform engines must be deployed with platform-issued data plane credentials (distinct from the service account credentials used to authenticate to the platform).

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_PLATFORM_URL`, `ARTHUR_PLATFORM_TOKEN`, `ARTHUR_PLATFORM_WORKSPACE_ID`, `ARTHUR_PLATFORM_ENGINE_ID`, and `ARTHUR_PLATFORM_ENGINE_URL` from the output.

**State write helper:**
```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_PLATFORM_ENGINE_ID=\|^ARTHUR_PLATFORM_ENGINE_URL=' \
  "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_PLATFORM_ENGINE_ID=$ENGINE_ID" >> "$STATE_FILE"
echo "ARTHUR_PLATFORM_ENGINE_URL=$ENGINE_URL" >> "$STATE_FILE"
```

---

## If ARTHUR_PLATFORM_ENGINE_ID Exists

Verify the engine is known by the platform:
```bash
ENGINE_RESPONSE=$(curl -s \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/data_planes/${ARTHUR_PLATFORM_ENGINE_ID}")
ENGINE_NAME=$(echo "$ENGINE_RESPONSE" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('name', d.get('id','NOT_FOUND')))" 2>/dev/null || echo "NOT_FOUND")
echo "ENGINE_KNOWN=$ENGINE_NAME"
```

If the engine exists, confirm reuse with user and exit this skill.
If `ENGINE_NAME=NOT_FOUND`: warn the user and proceed to list/deploy below.

---

## List Registered Engines for Workspace

```bash
ENGINES_RESPONSE=$(curl -s \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/workspaces/${ARTHUR_PLATFORM_WORKSPACE_ID}/data_planes")
ENGINE_LIST=$(echo "$ENGINES_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
engines = d.get('resources') or d.get('data') or d.get('data_planes') or (d if isinstance(d, list) else [])
for e in engines:
    last_seen = e.get('last_check_in_time') or 'never checked in'
    print(f'  {e[\"id\"]}: {e.get(\"name\",\"(unnamed)\")} — last check-in: {last_seen}')
if not engines:
    print('  (no engines registered to this workspace)')
" 2>/dev/null || echo "  (error parsing response)")
echo "$ENGINE_LIST"
```

Show the list to the user and ask:
> "Do you want to use one of these existing engines, or deploy a new one?"

If the user selects an existing engine:
- Save its ID to `ARTHUR_PLATFORM_ENGINE_ID`
- Ask for (or confirm) the engine's external URL and save to `ARTHUR_PLATFORM_ENGINE_URL`
- Exit this skill

---

## Deploy a New Engine

Tell the user:
> "We'll register a new engine with the platform and deploy it. The platform will issue
> dedicated credentials for the engine — these are different from your service account."

### Step 1 — Register the Engine with the Platform

Ask the user for an engine name (e.g., "Production Engine", "Dev Machine").

```bash
DP_CREATE_RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$ENGINE_NAME\"}" \
  "${ARTHUR_PLATFORM_URL}/api/v1/workspaces/${ARTHUR_PLATFORM_WORKSPACE_ID}/data_planes")
DATA_PLANE_ID=$(echo "$DP_CREATE_RESPONSE" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
DATA_PLANE_CLIENT_ID=$(echo "$DP_CREATE_RESPONSE" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('client_id',''))" 2>/dev/null)
DATA_PLANE_CLIENT_SECRET=$(echo "$DP_CREATE_RESPONSE" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('client_secret',''))" 2>/dev/null)
echo "DATA_PLANE_ID=$DATA_PLANE_ID"
echo "DATA_PLANE_CLIENT_ID=$DATA_PLANE_CLIENT_ID"
echo "HAS_SECRET=$([ -n "$DATA_PLANE_CLIENT_SECRET" ] && echo 'yes' || echo 'no')"
```

> **Critical:** The `client_secret` is only returned once. Save it immediately:

```bash
python3 -c "
import os, stat
p = os.path.expanduser('~/.ae_dp_secret')
open(p, 'w').write('$DATA_PLANE_CLIENT_SECRET')
os.chmod(p, 0o600)
print('Data plane secret saved to ~/.ae_dp_secret')
"
```

If `DATA_PLANE_ID` is empty or `HAS_SECRET=no`: show the raw response; report the error.
If the secret was lost, you can regenerate it later: `POST /api/v1/data_planes/{id}/credential_set`.

### Step 2 — Choose Deployment Method

Ask the user which deployment method they want:
- **A) Docker Compose** — recommended for single-machine setups (Mac, Linux, Windows)
- **B) AWS CloudFormation** — for AWS deployments
- **C) Kubernetes (Helm)** — for Kubernetes clusters

Also ask:
> "What is the external URL where this engine will be reachable by your applications?
> For a local Docker install this is typically `http://localhost:7072` or `http://localhost:3030`.
> For cloud deployments, this is your load balancer or ingress URL."

Save this as the engine ingress URL.

---

### Option A — Docker Compose

Detect the OS:
```bash
OS_TYPE=$(uname -s 2>/dev/null || echo "Windows_NT")
echo "OS_TYPE=$OS_TYPE"
```
`Darwin` = Mac, `Linux` = Linux, anything else = Windows.

**Mac/Linux** — delegate to a Task sub-agent. Tell the user:
> "Starting the Arthur Engine installer now. The first run downloads Docker images and AI models — this can take 10–15 minutes. I'll keep you updated."

Capture the current timestamp before launching:
```bash
date -u "+%Y-%m-%dT%H:%M:%SZ"
```
Remember this as `PRE_INSTALL_TIME`.

**Mac/Linux sub-agent prompt:**
```
Run the Arthur Platform Engine installer for Mac/Linux.

DATA_PLANE_CLIENT_ID: <DATA_PLANE_CLIENT_ID>
ARTHUR_PLATFORM_URL: <ARTHUR_PLATFORM_URL>

Step 1 — Read the data plane secret (read once and delete):
  DP_SECRET=$(cat ~/.ae_dp_secret && rm -f ~/.ae_dp_secret)

Step 2 — Run the installer non-interactively:
  bash <(curl -sSL https://engine.arthur.ai/mac) \
    --arthur-client-id="$DATA_PLANE_CLIENT_ID" \
    --arthur-client-secret="$DP_SECRET" \
    --arthur-api-host="<ARTHUR_PLATFORM_URL>" \
    --fetch-raw-data-enabled=true \
    --default-genai-config=false

Report: installer exit code (0=success), any errors shown.
```

**Windows** — show this command for the user to run manually in PowerShell:
```powershell
$DP_SECRET = Get-Content -Path "$env:USERPROFILE\.ae_dp_secret" -Raw
Remove-Item -Path "$env:USERPROFILE\.ae_dp_secret" -Force
& ([scriptblock]::Create((Invoke-WebRequest "https://engine.arthur.ai/win" -UseBasicParsing).Content)) `
  --arthur-client-id="<DATA_PLANE_CLIENT_ID>" `
  --arthur-client-secret="$DP_SECRET" `
  --arthur-api-host="<ARTHUR_PLATFORM_URL>" `
  --fetch-raw-data-enabled=true `
  --default-genai-config=false
```

Note: For Windows, first save the secret to `$env:USERPROFILE\.ae_dp_secret` using the same getpass technique:
> `! python3 -c "import getpass, os, stat; p=os.path.expanduser('~/.ae_dp_secret'); s=getpass.getpass('Data plane secret (hidden): '); open(p,'w').write(s); os.chmod(p, 0o600); print('Saved.')"`

Poll for engine startup after install — make **individual Bash calls one per check cycle, NOT a single long loop**. Each call is ~10s apart using `PRE_INSTALL_TIME` as the initial `--since` value:

```bash
COMPOSE_DIR="$HOME/.arthur-engine/local-stack/genai-engine"
sleep 10
if [ -f "$COMPOSE_DIR/docker-compose.yml" ]; then
  docker compose -f "$COMPOSE_DIR/docker-compose.yml" logs --no-color \
    --since="<LAST_LOG_SINCE>" 2>&1 | tail -20 || true
fi
echo "NEXT_LOG_SINCE=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "http://localhost:3030/api/v2/tasks?page=0&page_size=1" 2>/dev/null || echo "000")
echo "ENGINE_STATUS=$STATUS"
```

Stop when `ENGINE_STATUS=200` or `ENGINE_STATUS=401`. Max 60 calls (~10 min). If not ready after 60 calls: inform the user and ask if they want to keep waiting.

---

### Option B — AWS CloudFormation

Show the user the quick-create URL for CPU deployment:
```
https://us-east-2.console.aws.amazon.com/cloudformation/home?region=us-east-2#/stacks/quickcreate?templateURL=https://arthur-cft.s3.us-east-2.amazonaws.com/arthur-engine/templates/0.0.9-lts/root-arthur-engine-cpu.yml&stackName=arthur-engine&param_MLEngineClientId=<DATA_PLANE_CLIENT_ID>
```

For GPU deployment:
```
https://us-east-2.console.aws.amazon.com/cloudformation/home?region=us-east-2#/stacks/quickcreate?templateURL=https://arthur-cft.s3.us-east-2.amazonaws.com/arthur-engine/templates/0.0.9-lts/root-arthur-engine-gpu.yml&stackName=arthur-engine&param_MLEngineClientId=<DATA_PLANE_CLIENT_ID>
```

Tell the user:
> "The `MLEngineClientId` parameter is pre-filled with your data plane client ID.
> You will also need to supply the **client secret** (`<DATA_PLANE_CLIENT_SECRET>` from `~/.ae_dp_secret`) in the CloudFormation parameters.
> After the stack completes, provide the engine's public URL (load balancer DNS) as the engine ingress URL."

Ask the user to complete the CloudFormation deployment and confirm when done.

---

### Option C — Kubernetes (Helm)

Generate the Helm deployment script with platform credentials filled in. Show the user the script with `<DATA_PLANE_CLIENT_ID>` already substituted and remaining placeholders marked:

```bash
#!/bin/bash

K8S_NAMESPACE=arthur
ARTHUR_ENGINE_VERSION=0.0.9-lts
POSTGRES_USER=arthur_genai_engine
POSTGRES_PASSWORD=<changeme_pg_password>
POSTGRES_ENDPOINT=<mydb>
GENAI_ENGINE_ADMIN_KEY=<changeme_genai_engine_admin_key>
GENAI_ENGINE_OPENAI_PROVIDER=<Azure_or_OpenAI>
GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS=<model_name::https://service.openai.azure.com/::api_key>
GENAI_ENGINE_INGRESS_URL=<YOUR_INGRESS_URL>
ML_ENGINE_CLIENT_ID=<DATA_PLANE_CLIENT_ID>
ML_ENGINE_CLIENT_SECRET=<DATA_PLANE_CLIENT_SECRET>

kubectl -n $K8S_NAMESPACE create secret generic postgres-secret \
    --from-literal=username=$POSTGRES_USER \
    --from-literal=password=$POSTGRES_PASSWORD
kubectl -n $K8S_NAMESPACE create secret generic genai-engine-secret-admin-key \
    --from-literal=key=$GENAI_ENGINE_ADMIN_KEY
kubectl -n $K8S_NAMESPACE create secret generic genai-engine-secret-open-ai-gpt-model-names-endpoints-keys \
    --from-literal=keys=$GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS
kubectl -n arthur create secret generic ml-engine-client-secret \
    --from-literal=client_id=$ML_ENGINE_CLIENT_ID \
    --from-literal=client_secret=$ML_ENGINE_CLIENT_SECRET

mkdir -p tmp
curl -o "tmp/values.yaml" "https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/helm/arthur-engine/values.yaml.template"
curl -o "tmp/Chart.yaml" "https://raw.githubusercontent.com/arthur-ai/arthur-engine/refs/heads/main/deployment/helm/arthur-engine/Chart.yaml"
cd tmp
helm dependency update
helm upgrade --install -n $K8S_NAMESPACE -f values.yaml arthur-engine . \
  --set arthur-genai-engine.genaiEngineVersion=$ARTHUR_ENGINE_VERSION \
  --set arthur-genai-engine.postgresBYOEndpoint=$POSTGRES_ENDPOINT \
  --set arthur-genai-engine.genaiEngineIngressURL=$GENAI_ENGINE_INGRESS_URL \
  --set arthur-genai-engine.genaiEngineOpenAIProvider=$GENAI_ENGINE_OPENAI_PROVIDER \
  --set arthur-ml-engine.mlEngine.deployment.genaiEngineInternalIngressHost=$GENAI_ENGINE_INGRESS_URL
```

Ask the user to fill in the remaining values. Offer to run the completed script via a Task sub-agent.

---

## Poll Platform for Engine Check-in

After any deployment method, poll the platform to confirm the engine is reporting active.
Make **individual Bash calls one per check cycle**:

```bash
CHECKIN_RESPONSE=$(curl -s \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/data_planes/${DATA_PLANE_ID}")
LAST_CHECKIN=$(echo "$CHECKIN_RESPONSE" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('last_check_in_time') or 'null')" \
  2>/dev/null || echo "null")
echo "LAST_CHECKIN=$LAST_CHECKIN"
```

Run up to 24 checks, ~10 seconds apart. Stop when `LAST_CHECKIN` is not `null`.

If the engine never checks in after ~4 minutes:
- Guide the user to check Docker/CloudFormation/Helm logs for errors
- Verify the data plane `client_id` matches the one used in deployment
- Verify the engine host can reach `ARTHUR_PLATFORM_URL` (network/firewall)
- Offer to regenerate credentials: `POST /api/v1/data_planes/{id}/credential_set`

---

## Save Engine to State

```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_PLATFORM_ENGINE_ID=\|^ARTHUR_PLATFORM_ENGINE_URL=' \
  "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_PLATFORM_ENGINE_ID=$DATA_PLANE_ID" >> "$STATE_FILE"
echo "ARTHUR_PLATFORM_ENGINE_URL=$ENGINE_INGRESS_URL" >> "$STATE_FILE"
```

Confirm to the user: "Engine registered and active: `<ENGINE_INGRESS_URL>` (`<DATA_PLANE_ID>`)"

Exit this skill.
