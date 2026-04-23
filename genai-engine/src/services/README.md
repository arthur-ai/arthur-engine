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
- **`TRACE_RETENTION_INTERVAL_HOURS`** – Environment variable controlling how often the background loop enqueues a retention run, expressed in whole hours. Default: **24**. Minimum: **1** hour — sub-minimum values are clamped up, non-integer values fall back to the default, and both cases emit a `WARNING`. Set this to `1` for hourly cleanup on high-volume deployments. The value is read once at service construction, so changing it requires a process restart.

### Behavior

- A background thread runs one retention pass at startup, then re-enqueues a job every `TRACE_RETENTION_INTERVAL_HOURS` (default **24 hours**).
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

### Observability

All log records below are emitted under the `services.trace_retention_service` logger. Operators can grep for the literal strings to confirm service health:

| Log string | When emitted | Level |
|---|---|---|
| `Trace retention interval: N hour(s)` | Once, when the background thread starts — confirms the resolved `TRACE_RETENTION_INTERVAL_HOURS`. | INFO |
| `Acquired trace retention leader lock` | When this replica wins leader election. | INFO |
| `Another replica holds the trace retention leader lock, standing by; next leadership check at <ISO>` | On a standby replica each time it fails to acquire the lock. | INFO |
| `Next trace retention enqueue scheduled at <ISO>` | After every successful enqueue (initial and subsequent). The timestamp is when the *next* enqueue will occur, one interval from now — the job just enqueued runs immediately. | INFO |
| `Trace retention run complete: deleted N traces (cutoff=<ISO>, retention=N days)` | At the end of every run on the success path, **including runs that deleted zero traces**. The absence of this line for longer than the configured interval indicates the service is not running. | INFO |
| `Trace retention batch failed after deleting N traces` | A batch raised; the run is rolled back and counted toward the circuit breaker. | ERROR |
| `Trace retention run failed (N consecutive)` | The outer run raised (e.g. session acquisition failed). | ERROR |
| `Trace retention latch tripped: <reason>` | Runaway cap or circuit breaker tripped; the service halts until the process restarts. | CRITICAL |

### Lifecycle

- **Start** – In `server.py` lifespan: `initialize_trace_retention_service()`.
- **Stop** – Before lifespan exit: `shutdown_trace_retention_service()` (stops the background thread and sets the global to `None`).

### Code references

- Service: [trace_retention_service.py](trace_retention_service.py)
- Repository: [../repositories/trace_retention_repository.py](../repositories/trace_retention_repository.py)

---

## Other services

- **Currency conversion** – In-app exchange rates and USD→target conversion. See [currency/README.md](currency/README.md).
