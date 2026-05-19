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

## If ARTHUR_PLATFORM_TOKEN Exists — Verify It

```bash
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/users/me" 2>/dev/null || echo "000")
echo "AUTH_STATUS=$HTTP_STATUS"
```

- `200` → token still valid; confirm reuse with user ("Still authenticated to Arthur Platform?"); if yes, exit this skill
- `401` → token expired; proceed to "Acquire Token" section below (skip service account creation guidance if `ARTHUR_PLATFORM_CLIENT_ID` already exists)
- anything else → network or platform issue; warn the user and exit with an error message

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

After the user confirms, read and delete the temp file:
```bash
CLIENT_SECRET=$(cat ~/.ae_tmp_secret 2>/dev/null && rm -f ~/.ae_tmp_secret)
echo "SECRET_READ=$([ -n "$CLIENT_SECRET" ] && echo 'OK' || echo 'EMPTY')"
```

If `SECRET_READ=EMPTY`: ask the user to re-run the command above.

---

## Acquire OAuth2 Token

**Step 1 — Discover the token endpoint via OIDC:**
```bash
OIDC_RESPONSE=$(curl -s \
  "${ARTHUR_PLATFORM_URL}/api/v1/auth/oidc/.well-known/openid-configuration")
TOKEN_ENDPOINT=$(echo "$OIDC_RESPONSE" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('token_endpoint',''))" 2>/dev/null)
echo "TOKEN_ENDPOINT=$TOKEN_ENDPOINT"
```

If `TOKEN_ENDPOINT` is empty: the platform URL may be wrong or unreachable. Show the raw OIDC response and exit with an error.

**Step 2 — Acquire the access token:**
```bash
TOKEN_RESPONSE=$(curl -s -X POST "$TOKEN_ENDPOINT" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&scope=openid+email+profile")
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
echo "TOKEN_STATUS=$([ -n "$ACCESS_TOKEN" ] && echo 'OK' || echo 'FAILED')"
```

If `TOKEN_STATUS=FAILED`: show the error from `TOKEN_RESPONSE` (do NOT log the raw secret). Ask the user to verify their Client ID and Secret. Do not retry more than twice — exit and ask for human help.

---

## Verify Token

```bash
ME_RESPONSE=$(curl -s \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/users/me")
ME_HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "${ARTHUR_PLATFORM_URL}/api/v1/users/me" 2>/dev/null || echo "000")
ME_EMAIL=$(echo "$ME_RESPONSE" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('email', d.get('username','unknown')))" 2>/dev/null || echo "unknown")
echo "ME_HTTP=$ME_HTTP"
echo "ME_EMAIL=$ME_EMAIL"
```

- `200` → report: "Authenticated as: <ME_EMAIL>"
- `401` → token acquired but rejected; check service account permissions
- anything else → unexpected error; show raw response; exit with warning

---

## Save Token to State

```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_PLATFORM_TOKEN=' "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_PLATFORM_TOKEN=$ACCESS_TOKEN" >> "$STATE_FILE"
```

Exit this skill. The token is valid and ready for the next step.

---

## Token Expiry Note

OAuth2 access tokens typically expire after ~1 hour. If any downstream sub-skill receives a `401` response from the Platform API, re-invoke this skill to refresh the token before retrying.
