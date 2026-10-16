# GCP Vertex Agent Engine

The reference SDK connector: `ml-engine/src/ml_engine/discovery/cloud/gcp_vertex/connector.py`.

## Record

- `external_id`: the reasoning engine's resource name, `projects/<n>/locations/<r>/reasoningEngines/<id>`.
- `address.instance` is the project, `address.scope` the location, `address.resource_id` the engine id.
- `observations.service_names`: Vertex's stored key is the full resource path, to match the keys the older Vertex poller wrote; its spans carry the bare engine id. So an agent instrumented after discovery gets a second task. Do not copy this mapping; a new connector carries the form the spans carry (and the older form too, if an older integration's keys must still match).

## Connection

- Least privilege: a role with only `aiplatform.reasoningEngines.list`.
- Application Default Credentials are opt-in through `ARTHUR_ENGINE_GCP_VERTEX_ALLOW_ADC`.
- SDK faults carry their HTTP status through `with_vendor_status`, re-raised unwrapped.
- Its missing-`project_id` path raises a plain `ValueError`; do not copy that. New code raises `DiscoveryConfigurationError`.
