# Azure AI Foundry

## Record

- `external_id`: Foundry has no single global agent name, so compose `azure://{ARM project resource id}/agents/{agent id}` and document it.
- `address.instance` is the subscription.

## Connection

- One credential, two token audiences: `management.azure.com` for ARM and `ai.azure.com` for the data plane. The per-account data-plane host is discovered through ARM, so there is no URL field and no fixed host; do not add an `https` URL field.
- Least privilege: the built-in Foundry User role grants `Microsoft.CognitiveServices/*` data actions and listkeys; too wide. Use Reader plus a custom role with only the agent read action.
- The narrowest agent action, `Microsoft.CognitiveServices/accounts/AIServices/agents/read`, is documented as "Read agents, threads, and messages". Call only `/agents`, never threads, conversations, messages or responses.

## Partial results

A project with `publicNetworkAccess=Disabled` is listed by ARM, and its agents call times out. Log it as unreachable before the first yield and keep the other projects' records.
