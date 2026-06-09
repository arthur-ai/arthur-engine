---
name: arthur-onboard-platform-access
description: Arthur onboarding sub-skill — Platform Step 2: Authenticate to Arthur Platform using service account credentials (OAuth2 client credentials). Reads/writes .arthur-engine.env.
allowed-tools: Bash, Read, Write
version: 1.0.0
---

# Arthur Onboard — Platform Step 2: Authenticate to Arthur Platform

**Goal:** Establish `ARTHUR_PLATFORM_CLIENT_ID` and `ARTHUR_PLATFORM_TOKEN` in `.arthur-engine.env`.

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_PLATFORM_URL`, `ARTHUR_PLATFORM_CLIENT_ID`, `ARTHUR_PLATFORM_CLIENT_SECRET`, and `ARTHUR_PLATFORM_TOKEN` from the output.

**State write helper** — use this pattern to update individual values without clobbering others:
```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_PLATFORM_TOKEN=' "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_PLATFORM_TOKEN=$TOKEN" >> "$STATE_FILE"
```

---

## If Stored Credentials Exist — Verify or Auto-Refresh

If both `ARTHUR_PLATFORM_CLIENT_ID` and `ARTHUR_PLATFORM_CLIENT_SECRET` are present in state, invoke the `arthur-onboard-platform-token` sub-skill to get a fresh token, then verify it:

```bash
ARTHUR_PLATFORM_URL=$(grep '^ARTHUR_PLATFORM_URL=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
ARTHUR_PLATFORM_TOKEN=$(grep '^ARTHUR_PLATFORM_TOKEN=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)

ME_RESPONSE=$(curl -s -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" "${ARTHUR_PLATFORM_URL}/api/v1/users/me")
ME_HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" "${ARTHUR_PLATFORM_URL}/api/v1/users/me" 2>/dev/null || echo "000")
ME_EMAIL=$(echo "$ME_RESPONSE" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('email', d.get('username','unknown')))" 2>/dev/null || echo "unknown")
echo "ME_HTTP=$ME_HTTP"
echo "ME_EMAIL=$ME_EMAIL"
```

- Sub-skill `TOKEN_REFRESH=OK` and `ME_HTTP=200` → confirm reuse with user ("Still authenticated as <ME_EMAIL>?"); if yes, exit this skill
- Sub-skill `TOKEN_REFRESH=MISSING_CREDENTIALS` or `TOKEN_REFRESH=FAILED`, or `ME_HTTP` not 200 → credentials invalid; proceed to "Collect Client Credentials" below

If `ARTHUR_PLATFORM_CLIENT_ID` or `ARTHUR_PLATFORM_CLIENT_SECRET` is missing from state, skip this section entirely and proceed to "Guide Service Account Creation".

---

## Guide Service Account Creation

Tell the user:
> "To connect to Arthur Platform programmatically, we need a service account. Here is how to create one:
>
> 1. Log in to **<ARTHUR_PLATFORM_URL>** in your browser (If you need to create a new SaaS account, go to https://platform.arthur.ai/signup)
> 2. Click the **grid icon** at the top-right of the UI next to your profile icon with user name initials
> 3. Select **Identity & Access** from the menu
> 4. On the Identity & Access page, click the **Users** tab
> 5. Click **+ USER** and choose **Service Account**
> 6. Fill in a name and (optional) description
> 7. After creation, the platform will display a **Client ID** and **Client Secret** — copy both now; the secret will not be shown again"
> 8. For role assignment, practice the **least-privilege** model:
>    - First-time setup / full onboarding: assign the **Organization Admin** role
>    - Adding a single application to an existing workspace: assign only workspace member + project contributor
> 9. If there are existing workspaces you want the service account to have access to, go to the "User Management" menu and configure accordingly

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

## Acquire Token

After the user confirms they ran the command above, save the secret to state in one Bash call (the secret must be read and deleted in the same call to avoid it persisting on disk):

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

# Save secret to state file
grep -v '^ARTHUR_PLATFORM_CLIENT_SECRET=' .arthur-engine.env 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp .arthur-engine.env || true
echo "ARTHUR_PLATFORM_CLIENT_SECRET=$CLIENT_SECRET" >> .arthur-engine.env
echo "SECRET_SAVED=true"
```

- `SECRET_READ=EMPTY` → ask the user to re-run the getpass command above, then retry
- `SECRET_SAVED=true` → proceed

Invoke the `arthur-onboard-platform-token` sub-skill to acquire the token. If it outputs `TOKEN_REFRESH=FAILED`, show any error and ask the user to verify their credentials; do not retry more than twice.

Then verify the token and get the user identity:

```bash
ARTHUR_PLATFORM_URL=$(grep '^ARTHUR_PLATFORM_URL=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
ARTHUR_PLATFORM_TOKEN=$(grep '^ARTHUR_PLATFORM_TOKEN=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)

ME_RESPONSE=$(curl -s -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" "${ARTHUR_PLATFORM_URL}/api/v1/users/me")
ME_HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $ARTHUR_PLATFORM_TOKEN" "${ARTHUR_PLATFORM_URL}/api/v1/users/me" 2>/dev/null || echo "000")
ME_EMAIL=$(echo "$ME_RESPONSE" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('email', d.get('username','unknown')))" 2>/dev/null || echo "unknown")
echo "ME_HTTP=$ME_HTTP"
echo "ME_EMAIL=$ME_EMAIL"
```

- `ME_HTTP=200` → report "Authenticated as: <ME_EMAIL>" and exit this skill
- `ME_HTTP=401` → token acquired but rejected by the API; check service account permissions
- anything else → unexpected error; show raw `ME_RESPONSE`; exit with warning

---

## Token Expiry Note

Platform tokens expire after ~5 minutes. Because `ARTHUR_PLATFORM_CLIENT_ID` and `ARTHUR_PLATFORM_CLIENT_SECRET` are stored in `.arthur-engine.env`, downstream platform sub-skills can refresh the token automatically using `arthur_client` without asking the user again. If a sub-skill reports auth failure, re-invoke this skill to re-authenticate.
