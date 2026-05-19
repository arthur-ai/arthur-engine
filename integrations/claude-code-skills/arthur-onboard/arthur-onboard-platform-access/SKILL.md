---
name: arthur-onboard-platform-access
description: Arthur onboarding sub-skill — Platform Step 2: Authenticate to Arthur Platform using service account credentials (OAuth2 client credentials). Reads/writes .arthur-engine.env.
allowed-tools: Bash, Read, Write
---

# Arthur Onboard — Platform Step 2: Authenticate to Arthur Platform

**Goal:** Establish `ARTHUR_PLATFORM_CLIENT_ID` and `ARTHUR_PLATFORM_TOKEN` in `.arthur-engine.env`.

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_PLATFORM_URL`, `ARTHUR_PLATFORM_CLIENT_ID`, and `ARTHUR_PLATFORM_TOKEN` from the output.

**State write helper** — use this pattern to update individual values without clobbering others:
```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_PLATFORM_TOKEN=' "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_PLATFORM_TOKEN=$TOKEN" >> "$STATE_FILE"
```

---

## If ARTHUR_PLATFORM_TOKEN Exists — Verify or Auto-Refresh

Platform tokens expire after ~5 minutes. If the token is expired but credentials are stored, refresh silently without asking the user again (all in one Bash call):

```bash
ARTHUR_PLATFORM_URL=$(grep '^ARTHUR_PLATFORM_URL=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
ARTHUR_PLATFORM_TOKEN=$(grep '^ARTHUR_PLATFORM_TOKEN=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
STORED_SECRET=$(grep '^ARTHUR_PLATFORM_CLIENT_SECRET=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)

AUTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/users/me" 2>/dev/null || echo "000")
echo "AUTH_STATUS=$AUTH_STATUS"

if [ "$AUTH_STATUS" = "200" ]; then
  echo "TOKEN_VALID=yes"
elif [ -n "$STORED_SECRET" ]; then
  echo "Token expired — auto-refreshing with stored credentials..."
  CLIENT_ID=$(grep '^ARTHUR_PLATFORM_CLIENT_ID=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
  TOKEN_ENDPOINT=$(curl -s "${ARTHUR_PLATFORM_URL}/api/v1/auth/oidc/.well-known/openid-configuration" | \
    python3 -c "import sys,json; print(json.load(sys.stdin).get('token_endpoint',''))" 2>/dev/null)
  NEW_TOKEN=$(curl -s -X POST "$TOKEN_ENDPOINT" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "client_id=$CLIENT_ID" \
    --data-urlencode "client_secret=$STORED_SECRET" \
    --data-urlencode "scope=openid email profile" | \
    python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
  if [ -n "$NEW_TOKEN" ]; then
    grep -v '^ARTHUR_PLATFORM_TOKEN=' .arthur-engine.env > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp .arthur-engine.env
    echo "ARTHUR_PLATFORM_TOKEN=$NEW_TOKEN" >> .arthur-engine.env
    echo "TOKEN_REFRESHED=yes"
  else
    echo "TOKEN_REFRESH=FAILED"
  fi
else
  echo "TOKEN_VALID=no — no stored credentials; must collect them"
fi
```

- `TOKEN_VALID=yes` → confirm reuse with user ("Still authenticated to Arthur Platform?"); if yes, exit this skill
- `TOKEN_REFRESHED=yes` → token refreshed silently; exit this skill
- `TOKEN_REFRESH=FAILED` or `TOKEN_VALID=no` → proceed to "Collect Client Credentials" below
- `AUTH_STATUS` is not `200` and no stored secret → warn the user and proceed to collect credentials

---

## Guide Service Account Creation

Tell the user:
> "To connect to Arthur Platform programmatically, we need a service account. Here is how to create one:
>
> 1. Log in to **<ARTHUR_PLATFORM_URL>** in your browser
> 2. Click the **grid icon** at the top-right of the UI (next to your profile icon with user name initials)
> 3. Select **Identity & Access** from the menu
> 4. On the Identity & Access page, click the **Users** tab
> 5. Click **+ USER** and choose **Service Account**
> 6. Fill in a name and (optional) description
> 7. For role assignment, practice the **least-privilege** model:
>    - First-time setup / full onboarding: assign the **Organization Admin** role
>    - Adding a single application to an existing workspace: assign only workspace member + project contributor
> 8. After creation, the platform will display a **Client ID** and **Client Secret** — copy both now; the secret will not be shown again"

Ask: "Do you already have a service account Client ID and Client Secret?"

If not: wait for the user to create one and confirm before continuing.

---

## Collect Client Credentials

Ask the user for their **Client ID** (non-sensitive — can be typed in chat):
> "Please enter your service account Client ID (e.g., `arthur-sa-<uuid>`):"

Save the Client ID to the state file:
```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_PLATFORM_CLIENT_ID=' "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_PLATFORM_CLIENT_ID=$CLIENT_ID" >> "$STATE_FILE"
```

For the **Client Secret** (sensitive), show the user this message and wait for their confirmation before proceeding (do **not** ask them to type the secret in chat; do **not** run getpass via the Bash tool — it has no TTY):
> To keep your Client Secret secure, please run this command directly in your terminal (the `!` prefix runs it in your shell where input is masked):
>
> `! python3 -c "import getpass, os, stat; p=os.path.expanduser('~/.ae_tmp_secret'); s=getpass.getpass('Client Secret (hidden): '); open(p,'w').write(s); os.chmod(p, 0o600); print('Secret saved.')"`
>
> Let me know once you've run it and I'll continue.

---

## Acquire Token (single Bash call — do NOT split into multiple steps)

After the user confirms they ran the command above, execute **all of the following in one Bash call**: read the secret, discover the token endpoint, acquire the token, verify it, and save it to state. Shell variables do not persist between Bash calls, so splitting this into multiple steps will lose the secret.

```bash
# Read state file for URL and client ID
ARTHUR_PLATFORM_URL=$(grep '^ARTHUR_PLATFORM_URL=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
CLIENT_ID=$(grep '^ARTHUR_PLATFORM_CLIENT_ID=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)

# Read and immediately delete the secret temp file
CLIENT_SECRET=$(cat ~/.ae_tmp_secret 2>/dev/null)
rm -f ~/.ae_tmp_secret
echo "SECRET_READ=$([ -n "$CLIENT_SECRET" ] && echo 'OK' || echo 'EMPTY')"

if [ -z "$CLIENT_SECRET" ]; then
  echo "ERROR: Secret file not found or empty — ask user to re-run the getpass command"
  exit 0
fi

# Save secret to state file for automatic token refresh (tokens expire in ~5 minutes)
grep -v '^ARTHUR_PLATFORM_CLIENT_SECRET=' .arthur-engine.env 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp .arthur-engine.env || true
echo "ARTHUR_PLATFORM_CLIENT_SECRET=$CLIENT_SECRET" >> .arthur-engine.env

# Discover token endpoint via OIDC
TOKEN_ENDPOINT=$(curl -s "${ARTHUR_PLATFORM_URL}/api/v1/auth/oidc/.well-known/openid-configuration" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('token_endpoint',''))" 2>/dev/null)
echo "TOKEN_ENDPOINT=$TOKEN_ENDPOINT"

if [ -z "$TOKEN_ENDPOINT" ]; then
  echo "ERROR: Could not discover token endpoint — check ARTHUR_PLATFORM_URL"
  exit 0
fi

# Acquire access token using client credentials flow
TOKEN_RESPONSE=$(curl -s -X POST "$TOKEN_ENDPOINT" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=client_credentials" \
  --data-urlencode "client_id=$CLIENT_ID" \
  --data-urlencode "client_secret=$CLIENT_SECRET" \
  --data-urlencode "scope=openid email profile")
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
TOKEN_ERROR=$(echo "$TOKEN_RESPONSE" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error_description', d.get('error','')))" 2>/dev/null)
echo "TOKEN_STATUS=$([ -n "$ACCESS_TOKEN" ] && echo 'OK' || echo 'FAILED')"
[ -n "$TOKEN_ERROR" ] && echo "TOKEN_ERROR=$TOKEN_ERROR"

if [ -z "$ACCESS_TOKEN" ]; then
  exit 0
fi

# Verify token and get user identity
ME_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "${ARTHUR_PLATFORM_URL}/api/v1/users/me")
ME_HTTP=$(echo "$ME_RESPONSE" | python3 -c "import sys; print('unknown')" 2>/dev/null)
ME_HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ACCESS_TOKEN" "${ARTHUR_PLATFORM_URL}/api/v1/users/me" 2>/dev/null || echo "000")
ME_EMAIL=$(echo "$ME_RESPONSE" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('email', d.get('username','unknown')))" 2>/dev/null || echo "unknown")
echo "ME_HTTP=$ME_HTTP"
echo "ME_EMAIL=$ME_EMAIL"

# Save token to state file
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_PLATFORM_TOKEN=' "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_PLATFORM_TOKEN=$ACCESS_TOKEN" >> "$STATE_FILE"
echo "TOKEN_SAVED=true"
```

After running this single Bash call:
- `SECRET_READ=EMPTY` → ask the user to re-run the getpass command above, then retry
- `TOKEN_STATUS=FAILED` → show `TOKEN_ERROR` to the user; ask them to verify their credentials; do not retry more than twice
- `ME_HTTP=200` → report "Authenticated as: <ME_EMAIL>" and exit this skill
- `ME_HTTP=401` → token acquired but rejected by the API; check service account permissions
- anything else → unexpected error; show raw `ME_RESPONSE`; exit with warning

---

## Token Expiry Note

Platform tokens expire after ~5 minutes. Because `ARTHUR_PLATFORM_CLIENT_SECRET` is stored in `.arthur-engine.env`, all downstream platform sub-skills refresh the token automatically without asking the user again. If a sub-skill reports `TOKEN_REFRESH=FAILED`, re-invoke this skill to re-authenticate.
