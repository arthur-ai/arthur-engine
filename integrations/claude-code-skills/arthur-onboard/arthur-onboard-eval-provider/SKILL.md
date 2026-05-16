---
name: arthur-onboard-eval-provider
description: Arthur onboarding sub-skill — Step 8: Configure an LLM provider for continuous evals (OpenAI, Anthropic, Gemini, Bedrock, or Vertex AI). Reads/writes .arthur-engine.env.
allowed-tools: Bash, Read, Write
---

# Arthur Onboard — Step 8: Configure Eval Model Provider

## Read State

```bash
cat .arthur-engine.env 2>/dev/null || echo "(no state file)"
```

Parse `ARTHUR_ENGINE_URL` and `ARTHUR_API_KEY`.

---

## Check Existing Providers

```bash
curl -s \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  "$ARTHUR_ENGINE_URL/api/v1/model_providers" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
for p in d.get('providers', []):
    print(f'{p[\"provider\"]}: enabled={p[\"enabled\"]}')
"
```

**If an enabled provider exists:** Use it (prefer OpenAI > Anthropic > Gemini > Bedrock > Vertex AI). Write `ARTHUR_EVAL_PROVIDER` and `ARTHUR_EVAL_MODEL` to the state file, then exit this skill.

---

## If No Provider Enabled

Ask user to choose:
- `openai` → model `gpt-4o`
- `anthropic` → model `claude-3-5-haiku-20241022`
- `gemini` → model `gemini-1.5-flash`
- `bedrock` → model `anthropic.claude-3-haiku-20240307-v1:0`
- `vertex_ai` → model `gemini-1.5-flash`
- Skip → configure in the Arthur Engine UI later (write `ARTHUR_EVAL_PROVIDER=none` to state, then exit)

If a provider is chosen, show the user this message and wait for their confirmation (do **not** ask them to type the key in chat; do **not** run getpass via the Bash tool — it has no TTY):
> Please run this to securely enter your `<Provider>` API key (replace `<Provider>` with the actual provider name in the prompt):
>
> `! python3 -c "import getpass, os, stat; p=os.path.expanduser('~/.ae_tmp_key'); key=getpass.getpass('<Provider> API key (hidden): '); open(p,'w').write(key); os.chmod(p, 0o600); print('Key saved.')"`
>
> Let me know when done.

Then read the key from the temp file and configure:
```bash
PROVIDER_API_KEY=$(cat ~/.ae_tmp_key && rm -f ~/.ae_tmp_key)
curl -s -X PUT \
  -H "Authorization: Bearer $ARTHUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"api_key\": \"$PROVIDER_API_KEY\"}" \
  "$ARTHUR_ENGINE_URL/api/v1/model_providers/$PROVIDER"
```

Write `ARTHUR_EVAL_PROVIDER` and `ARTHUR_EVAL_MODEL` to `.arthur-engine.env`:
```bash
STATE_FILE=".arthur-engine.env"
grep -v '^ARTHUR_EVAL_PROVIDER=\|^ARTHUR_EVAL_MODEL=' \
  "$STATE_FILE" 2>/dev/null > /tmp/ae_env_tmp && mv /tmp/ae_env_tmp "$STATE_FILE" || true
echo "ARTHUR_EVAL_PROVIDER=$PROVIDER" >> "$STATE_FILE"
echo "ARTHUR_EVAL_MODEL=$MODEL" >> "$STATE_FILE"
```
