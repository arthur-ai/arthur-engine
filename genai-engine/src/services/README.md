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
  2. Fetches expired trace IDs in batches (see `get_expired_trace_ids` in the repository).
  3. For each batch, deletes related rows in order and commits (see `delete_trace_batch` in the repository).

### Lifecycle

- **Start** – In `server.py` lifespan: `initialize_trace_retention_service()`.
- **Stop** – Before lifespan exit: `shutdown_trace_retention_service()` (stops the background thread and sets the global to `None`).

### Code references

- Service: [trace_retention_service.py](trace_retention_service.py)
- Repository: [../repositories/trace_retention_repository.py](../repositories/trace_retention_repository.py)

---

## Other services

- **Currency conversion** – In-app exchange rates and USD→target conversion. See [currency/README.md](currency/README.md).
