# LiteLLM proxy

Facts a LiteLLM connector depends on. Pin each one in the connector's tests with captured bodies, and name the proxy version those bodies came from in the test module's docstring.

## Identity

- **Binding**: `GET /key/list?return_full_object=true` reports each key's `agent_id`. A request from a bound key carries that `agent_id` on its usage row with no header. Row `agent_id` equal to the key's bound `agent_id` is `registered_agent`.
- **Claimed**: the `X-LiteLLM-Agent-Id` header on an unbound key, or a real agent's id sent from another key, is `claimed_agent`.
- **Registry**: `GET /v1/agents` with a `proxy_admin_viewer` key answers 200 with an empty list even when agents exist. Never grade against it.
- **Credential id**: the hashed key `token`. Never the raw key; never `key_alias`.

## Rows to skip or fold

- A request refused for the key's scope (model not in its allow-list, 403) is logged with `status: failure` and without the agent id: fold it into the key's record.
- A request rejected for an invalid caller key carries `metadata.error_information.error_code == "401"`: skip and count it. A Test Connection probe made with a wrong key adds such rows.

## Least privilege and probe order

- Role: a user with `proxy_admin_viewer` and a key for that user. That key gets 403 on `POST /key/generate`, which is the read-only check.
- A non-admin key gets **401** on the spend-log routes but a clean **403** on `/user/list`, so probe `GET /user/list?page_size=1` first.
- `GET /key/info` answers 200 for any valid key and cannot check the role.
- Auth errors echo a masked key fragment (`Received=` followed by the key's first and last characters around `****`). Never copy the error text.

## Usage API

- `/spend/logs/v2` and `/spend/logs/ui` are one handler in the proxy; `/ui` is left out of the OpenAPI schema. Page with `page` / `page_size` until `total_pages`.
- `start_date` / `end_date` are UTC `YYYY-MM-DD HH:MM:SS`; ISO 8601 gets 400.
- `page_size` maximum is 1000; larger gets 422.
- `start_date=1970-01-01 00:00:00` is accepted for "everything retained".
- Rows are written in batches 20-60 s after the request.

## Enforcement surface (not built)

Block or unblock a key or team (`/key/block`, `/key/unblock`, `/team/block`, `/team/unblock`), guardrail hooks (`/guardrails/list`), and per-key budgets and model allow-lists.

## End-to-end traffic

Send requests with two keys, one key bound to an agent registered via `/v1/agents`, an `X-LiteLLM-Agent-Id` header from an unbound key (one registered id, one never issued), an MCP tool call, a model the key is not allowed, and one key used from two client containers.
