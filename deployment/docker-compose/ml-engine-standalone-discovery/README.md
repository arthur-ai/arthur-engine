# ML Engine Standalone Agent Discovery — Docker Compose

Runs the ML Engine as a single-container agent discovery runner: it scans the sources in
`discovery.yaml` on an interval and sends what it finds to a SIEM or webhook, with no
Arthur Platform or GenAI Engine. The config file is documented in
[ml-engine/docs/standalone-discovery.md](../../../ml-engine/docs/standalone-discovery.md).

## Quick start

1. Copy the templates:
   ```bash
   cp discovery.example.yaml discovery.yaml
   cp .env.template .env
   mkdir -p secrets
   ```
2. Edit `discovery.yaml`: your sources and your destination.
3. Put the secrets it reads:
   - values it references as `${NAME}` go in `.env`;
   - files it references as `{file: secrets/...}` go in `secrets/`, e.g. a GCP service
     account key at `secrets/gcp-key.json`.
4. Start it and watch the first scan:
   ```bash
   docker compose up --pull always
   ```
   Each scan logs `Starting discovery scan of '<source>/<config>'`, then a
   `discovery_scan_outcome` line saying how many agents it sent.

`discovery.yaml`, `.env` and `secrets/` are gitignored.

## Notes

- The container runs as UID `65532`, which must be able to read `discovery.yaml` and
  everything in `secrets/`. On Linux hosts, `chmod` or `chown` them accordingly; keep
  them unreadable to anyone else.
- A config the engine cannot use stops the container at startup with a message naming
  the problem. `docker compose logs ml-engine` shows it.
- `stop_grace_period` is 30s so running scans get the engine's 15-second drain before the
  container is killed.
- To switch the engine back to polling the Arthur Platform, set `enabled: false` in
  `discovery.yaml` (and supply the Platform credentials from
  [../ml-engine](../ml-engine/README.md)), or use that compose file instead.
