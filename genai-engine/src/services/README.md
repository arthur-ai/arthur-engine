# Background services

This directory contains long-running or scheduled background services used by the GenAI Engine. Each service is typically started in FastAPI lifespan and shut down on app exit.

## Trace retention service

Deletes trace data (and related spans, annotations, metric results, trace metadata, and orphan resource metadata) older than the configured retention period.

### Purpose

- Keeps storage under control by removing trace and span rows whose `end_time` is before the retention cutoff.
- Deletes in FK-safe order: agentic annotations → metric results → spans → trace metadata → resource metadata that are no longer referenced by any remaining span or trace.

### Configuration

- **`trace_retention_days`** – Application configuration (GET/POST `/api/v2/configuration`). Allowed values: **7, 14, 30, 90, 120, 365**. Default: **90** (see `DEFAULT_TRACE_RETENTION_DAYS` in `utils.constants`).
- The service reads this value on each run from `ConfigurationRepository.get_configurations()`.

### Behavior

- A background thread runs one retention pass at startup, then re-enqueues a job every **24 hours**.
- Each pass:
  1. Loads application configuration and computes `cutoff = now - timedelta(days=trace_retention_days)`.
  2. Fetches expired trace IDs in batches (see `get_expired_trace_ids` in the repository). Uses `SELECT … FOR UPDATE SKIP LOCKED` so concurrent nodes claim disjoint batches.
  3. For each batch, deletes related rows in order and commits (see `delete_trace_batch` in the repository).
  4. Waits `INTER_BATCH_DELAY_SECONDS` (1 second) between batches to reduce sustained DB pressure.

### Safety mechanisms

Three guards protect against runaway deletion and persistent failures:

| Guard | Constant | Behavior |
|---|---|---|
| **Runaway deletion cap** | `MAX_TRACES_PER_RUN = 100,000` | If a single run deletes this many traces, the latch trips and the service halts. Protects against misconfigured `trace_retention_days`. |
| **Circuit breaker** | `CIRCUIT_BREAKER_THRESHOLD = 3` | After 3 consecutive failed runs (e.g. DB unreachable), the latch trips. A successful run resets the counter. |
| **Inter-batch throttle** | `INTER_BATCH_DELAY_SECONDS = 1` | A 1-second pause between batches, yielding to shutdown signals. |

When the latch trips, it logs at `CRITICAL` and signals shutdown. The service will not perform any more deletions until the process is restarted.

**First-rollout note:** If retention is enabled for the first time on a deployment with more than 100k stale traces, the runaway cap will trip on the first run. The operator can either restart the process repeatedly (each run deletes up to 100k) or temporarily raise `MAX_TRACES_PER_RUN` before the initial deployment.

### Lifecycle

- **Start** – In `server.py` lifespan: `initialize_trace_retention_service()`.
- **Stop** – Before lifespan exit: `shutdown_trace_retention_service()` (stops the background thread and sets the global to `None`).

### Code references

- Service: [trace_retention_service.py](trace_retention_service.py)
- Repository: [../repositories/trace_retention_repository.py](../repositories/trace_retention_repository.py)

---

## Other services

- **Currency conversion** – In-app exchange rates and USD→target conversion. See [currency/README.md](currency/README.md).
