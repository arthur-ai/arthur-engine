---
name: arthur-onboard-platform-token
description: Arthur onboarding helper — Refresh Arthur Platform OAuth2 token using arthur_client. Reads CLIENT_ID/SECRET from .arthur-engine.env, writes ARTHUR_PLATFORM_TOKEN back to state.
allowed-tools: Bash
version: 1.0.0
---

# Arthur Onboard — Platform Token Refresh

**Goal:** Write a fresh `ARTHUR_PLATFORM_TOKEN` to `.arthur-engine.env` using stored service account credentials.

```bash
python3 -c "import arthur_client" 2>/dev/null || pip install arthur-client -q
```

```bash
ARTHUR_PLATFORM_URL=$(grep '^ARTHUR_PLATFORM_URL=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
CLIENT_ID=$(grep '^ARTHUR_PLATFORM_CLIENT_ID=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)
CLIENT_SECRET=$(grep '^ARTHUR_PLATFORM_CLIENT_SECRET=' .arthur-engine.env 2>/dev/null | cut -d= -f2-)

if [ -z "$CLIENT_SECRET" ]; then
  echo "TOKEN_REFRESH=MISSING_CREDENTIALS"
else
  export _AE_URL="$ARTHUR_PLATFORM_URL"
  export _AE_CLIENT_ID="$CLIENT_ID"
  export _AE_CLIENT_SECRET="$CLIENT_SECRET"

  ARTHUR_PLATFORM_TOKEN=$(python3 - <<'PYEOF'
import sys, os
try:
    from arthur_client.auth import ArthurClientCredentialsAPISession, ArthurOIDCMetadata
    metadata = ArthurOIDCMetadata(os.environ["_AE_URL"])
    session = ArthurClientCredentialsAPISession(
        client_id=os.environ["_AE_CLIENT_ID"],
        client_secret=os.environ["_AE_CLIENT_SECRET"],
        metadata=metadata,
    )
    print(session.token()["access_token"])
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
  )
  if [ -n "$ARTHUR_PLATFORM_TOKEN" ]; then
    grep -v '^ARTHUR_PLATFORM_TOKEN=' .arthur-engine.env > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp .arthur-engine.env
    echo "ARTHUR_PLATFORM_TOKEN=$ARTHUR_PLATFORM_TOKEN" >> .arthur-engine.env
    echo "TOKEN_REFRESH=OK"
  else
    echo "TOKEN_REFRESH=FAILED"
  fi
fi
```

- `TOKEN_REFRESH=OK` → token acquired and saved to `.arthur-engine.env`; exit this skill
- `TOKEN_REFRESH=MISSING_CREDENTIALS` → `CLIENT_ID` or `CLIENT_SECRET` not in state; caller must invoke `arthur-onboard-platform-access` first
- `TOKEN_REFRESH=FAILED` → `arthur_client` raised an error (invalid credentials, network error, etc.); caller should re-invoke `arthur-onboard-platform-access` to re-authenticate
