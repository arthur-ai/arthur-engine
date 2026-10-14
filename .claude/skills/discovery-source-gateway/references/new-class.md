# Adding the `network_gateway` source class (first gateway vendor only)

A source class is a contract shared by arthur-common, arthur-engine, the Platform and the UI. An arthur-common release gates everything, so open every half as a draft early; merge arthur-common first, then the engine repin, then the halves that consume it.

The wire value is fixed by shipped code: the Platform's coverage summary and the UI's coverage grid use `network_gateway` (label "Network & Gateway"). Until the Platform half lands, the summary always reports it as `no_sensor` and does not treat the class as configurable.

## Rules that outlive the release

- **A field added to a creation source is optional with a default**, or ships with a data migration in the same release. The GenAI Engine keeps a task's first creation source forever and re-validates stored tasks when it lists them, so one stale task fails the whole list, and with it the fetch.
- **External ids are global, permanent join keys** in the GenAI Engine: records from any source with the same `external_id` join the same task. Namespace gateway ids by vendor and instance.

## 1. arthur-common

GitHub `arthur-ai/arthur-common`, base `main`, public: keep internal references out of the PR.

In `src/arthur_common/models/agent_governance_schemas.py`:

- `SourceClass.NETWORK_GATEWAY = "network_gateway"`, added to `DISCOVERY_SOURCE_CLASSES`.
- `IdentityBasis`, with these definitions in its docstrings:
  - `registered_agent`: the request's agent id equals the agent its own credential is bound to;
  - `claimed_agent`: any other agent id on the request;
  - `credential`: no agent id; requests grouped by credential;
  - `client_address`: no credential either; grouped by source address.
- `NetworkGatewayAgentCreationSource(DiscoveryAgentCreationSource)`: `type: Literal["NETWORK_GATEWAY"]`, `SOURCE_CLASS`, `DETECTION=Detection.INFERRED`, `VISIBILITY_CEILING=Visibility.LIMITED`, `OBSERVABLE_FIELDS=frozenset({"client_addresses", "host_group", "assigned_user"})`, a required `identity_basis: IdentityBasis`, and a docstring giving the address convention (instance = gateway host, scope = team or workspace, resource_id = the id `external_id` is built from, query absent). No validator beyond the base: `scope` is optional for gateways without teams.
- `client_addresses` on `AgentObservations`, optional with a default (rule above).
- The class in `AgentCreationSourceUnion` and `DiscoveryCreationSourceUnion`; update the module comment that names Network & Gateway as the known fourth class.

Tests: `tests/unit/models/test_agent_governance_schemas.py` (class facts, round trip through both unions by `type`) and `test_agent_discovery_schemas.py` (a `DiscoveredAgentRecord` with the new source validates). Adding `client_addresses` breaks tests that assert no observation field is unreachable, or that pin the exact observation field set as a privacy allow-list (arthur-common's schema tests, the Jamf connector tests in arthur-engine). Update them deliberately; the allow-list is a privacy review.

Release is automatic: after the merge to `main` and a green "Arthur Common CI", `arthur-common-version-bump.yml` commits `Bump version: X → Y` and `arthur-common-release.yml` publishes to PyPI. Read the version off the bump commit and wait for it: `curl -s https://pypi.org/pypi/arthur-common/json | jq -r .info.version`.

## 2. arthur-engine

- Pins: `arthur-common==<new>` in `ml-engine/pyproject.toml` and `genai-engine/pyproject.toml`, then `uv lock --directory ml-engine` and `uv lock --directory genai-engine`; commit both locks. With no release yet, leave the pins unchanged and say so in the draft PR.
- `genai-engine/staging.openapi.json` and the changelog: from `genai-engine/`, `uv sync --group dev` then `uv run generate_changelog` (needs `oasdiff` on PATH; exits 1 when the spec changed, which is expected). The app must import, so set the env vars it reads at import to dummy values. The regenerated spec carries unrelated drift: review the diff and keep only what the class changed. CI job `run-genai-engine-changelog-cop` fails without it. Precedents: #2399, #2402.
- `_CREATION_SOURCE_TYPES["network_gateway"] = "NETWORK_GATEWAY"` in `ml-engine/src/ml_engine/job_executors/fetch_discovered_agents_executor.py`; without it a gateway agent's evidence is silently skipped on fetch.
- `ml-engine/src/ml_engine/discovery/network_gateway/__init__.py` (what the class observes) and `records.py`; list the class in the `discovery/__init__.py` module docstring.
- **Three generated or pinned things must know the new `type`.** The scan publishes each batch to the GenAI Engine (`job_executors/discovery_record_sink.py:_as_wire` → `genai_client`), and the fetch reads it back with `arthur-client`, the Platform's published Python client. With only arthur-common changed, the publish fails with `No match found when deserializing ... CreationSource with oneOf schemas: CloudAgentCreationSource, EndpointAgentCreationSource, SIEMAgentCreationSource`. All three are needed:
  1. `genai-engine` repins arthur-common and regenerates `staging.openapi.json`;
  2. `ml-engine`'s `genai_client` is generated from that spec (CI generates it from the committed spec, so step 1 lands in the same PR or earlier);
  3. `ml-engine` bumps `arthur-client` to a Platform release whose spec carries the class.
- Bump tests that count the union (`len(oneOf) == 6`, per-class parametrizations, found-by tags); grep for the old member list.

## 3. Fetch

- The fetch rebuilds each record's evidence from the GenAI Engine task's provenance, and provenance carries no observations. The only observations it can send are the ones on the task's stored creation source, attached to the record that created the task. Every other record's observations, and any later change, never reach the Platform. A field counts as observable only if it is carried through provenance and the fetch. Whether provenance should carry observations is an open question for the GenAI Engine and Platform owners; raise it in the PR.
- Provenance also lacks `identity_basis`. The fetch must copy it from the task's creation source.

## 4. Platform and UI

The Platform repins the arthur-common release, adds the class to its catalog's class list, and makes the coverage summary treat Network & Gateway as configurable once a gateway vendor is in the catalog. The UI refreshes its generated types and adds the class to its class order, labels and exhaustive class map. Both are covered by Arthur's internal discovery integration process skill.

## 5. Local proof before a release exists

- Tests: `uv sync`, then `uv pip install --no-deps -e <arthur-common checkout>` into each venv, and set `UV_NO_SYNC=1` on every `uv run`; otherwise uv re-syncs to the pinned release and the class vanishes.
- Lint: `ml-engine/scripts/lint.sh` starts with `uv sync --frozen`, which removes the editable arthur-common. Run the linters it lists directly, with `UV_NO_SYNC=1`.
- Stack: bind-mount the local arthur-common into the Platform, GenAI Engine and ml-engine containers, and mount `genai_client` and `arthur_client` bindings regenerated from the running GenAI Engine and Platform specs into the ml-engine container (the process skill's local end-to-end recipe).
