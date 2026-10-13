# Adding the `network_gateway` source class (first gateway vendor only)

A source class is a contract shared by arthur-common, arthur-engine, the Platform and the UI. Adding one is the slowest path (an arthur-common release gates everything). Open every half as a draft early; merge arthur-common first, then the engine repin, then the halves that consume it.

The wire value is already decided by shipped code: the Platform coverage summary and the UI's coverage grid both use `network_gateway` (label "Network & Gateway"). Today that card is a permanent blind spot: the coverage summary always reports it as `no_sensor` and does not treat the class as configurable.

## 1. arthur-common (GitHub `arthur-ai/arthur-common`, base `main`; public repo: keep internal references out of the PR)

`src/arthur_common/models/agent_governance_schemas.py`:
- `SourceClass.NETWORK_GATEWAY = "network_gateway"` and add it to `DISCOVERY_SOURCE_CLASSES`.
- `class NetworkGatewayAgentCreationSource(DiscoveryAgentCreationSource)` with `type: Literal["NETWORK_GATEWAY"]`, `SOURCE_CLASS`, `DETECTION=Detection.INFERRED`, `VISIBILITY_CEILING=Visibility.LIMITED`, `OBSERVABLE_FIELDS=frozenset({"client_addresses", "host_group", "assigned_user"})` (add `client_addresses: List[str]` to `AgentObservations`), a required `identity_basis: IdentityBasis` (`registered_agent`, `claimed_agent`, `credential`, `client_address`; port the enum and docstrings from the earlier `network` design, rewording `REGISTERED_AGENT` to "bound to the request's credential"), and a docstring giving the address convention (instance = gateway host, scope = team/workspace, resource_id = caller id, query absent). No validator beyond the base: `scope` is optional for gateways without teams.
- Add it to `AgentCreationSourceUnion` and `DiscoveryCreationSourceUnion` (the comment there already anticipates "a fourth discovery category").
- Update the module comment that names "Network & Gateway the known fourth".

Tests: `tests/unit/models/test_agent_governance_schemas.py` (class facts, round trip through both unions by `type`), `test_agent_discovery_schemas.py` (a `DiscoveredAgentRecord` with the new source validates).

Release is automatic: after the merge to `main` and a green "Arthur Common CI", `arthur-common-version-bump.yml` patch-bumps and commits `Bump version: X → Y`, and `arthur-common-release.yml` builds, tags and publishes to PyPI. Read the new version off the bump commit and wait for it on PyPI (`curl -s https://pypi.org/pypi/arthur-common/json | jq -r .info.version`).

## 2. arthur-engine (both engines repin the release)

- `ml-engine/pyproject.toml` and `genai-engine/pyproject.toml`: `arthur-common==<new>` (exact pins); `uv lock --directory ml-engine` and `uv lock --directory genai-engine`, commit both locks.
- Regenerate `genai-engine/staging.openapi.json` and the changelog in one step: from `genai-engine/`, `uv sync --group dev` then `uv run generate_changelog`. It writes `new.openapi.json`, diffs it with `oasdiff` (must be on PATH), prepends to `src/api_changelog.md`, copies the new spec over `staging.openapi.json`, and exits 1 when it changed something (expected). Commit both files; delete `new.openapi.json`. CI job `run-genai-engine-changelog-cop` fails if you skip this. Precedents: #2399, #2402. Keep the consuming PR a draft until the release exists.
- `ml-engine/src/ml_engine/job_executors/fetch_discovered_agents_executor.py`: `_CREATION_SOURCE_TYPES["network_gateway"] = "NETWORK_GATEWAY"`. Without it a gateway agent's evidence is silently skipped on fetch.
- `ml-engine/src/ml_engine/discovery/network_gateway/__init__.py` (docstring: what the class observes) and `records.py` (shared builder).
- `discovery/__init__.py` module docstring lists the classes; add this one.
- **Records travel through the GenAI Engine, so three generated or pinned things must know the new `type`, not one.** The scan publishes each batch to GenAI (`job_executors/discovery_record_sink.py:_as_wire` → `genai_client` `DiscoveredAgentRecord.from_dict`), and the fetch job reads it back with `arthur-client`, the Platform's published Python client (`AgentCreationSource.from_dict`). Proven on a local stack: with only arthur-common changed, a scan found 2 callers and then failed with `No match found when deserializing ... CreationSource with oneOf schemas: CloudAgentCreationSource, EndpointAgentCreationSource, SIEMAgentCreationSource`, publishing 0 records. All three are needed:
  1. `genai-engine` repins the arthur-common release (its API parses the `AgentCreationSource` union) and regenerates `staging.openapi.json`;
  2. `ml-engine`'s `genai_client` is generated from that spec (CI does this from the committed spec, so step 1 must be in the same PR or earlier);
  3. `ml-engine` bumps `arthur-client` to a Platform release whose spec carries the class.
  Until then a gateway record fails the publish (scan) and one gateway task fails a fetch page.
- Existing tests that count the union (`len(oneOf) == 6`, per-class parametrizations, found-by tags) must be bumped; grep for the old member list.

## 3. Platform and UI

The Platform repins the arthur-common release, adds the class to its catalog's class list, and makes the coverage summary treat Network & Gateway as configurable once a gateway vendor is in the catalog, instead of the permanent no-sensor blind spot. The UI refreshes its generated types and adds the class to its class order, labels and exhaustive class map; both halves are covered by Arthur's internal discovery integration process skill.

## 4. Local proof before any PR

Before any release exists:
- **Tests:** `uv sync`, then `uv pip install --no-deps -e <common worktree>` into each venv, and set `UV_NO_SYNC=1` on every `uv run` / `./local-dev/run_tests.sh` / lint run (otherwise uv re-syncs back to the pinned release and the class vanishes).
- **Stack:** bind-mount the local arthur-common into the Platform, GenAI Engine and ml-engine containers, and mount a `genai_client` and `arthur_client` bindings regenerated from the running GenAI Engine and Platform specs into the ml-engine container (the process skill's local end-to-end recipe).
