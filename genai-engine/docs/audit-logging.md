# Audit Logging

Arthur GenAI Engine includes built-in audit logging that records every authenticated API request as a structured JSON event. Logs are written to rotating files on disk.

## Enabling Audit Logging

Audit logging is **enabled by default**. Control it with these environment variables:

| Variable | Default | Description |
|---|---|---|
| `AUDIT_LOG_ENABLED` | `"true"` | Set to `"false"` to disable audit logging entirely |
| `AUDIT_LOG_RETENTION_DAYS` | `365` | Number of daily log files to retain before rotation deletes them |
| `AUDIT_LOG_OVERRIDE_PATH` | *(unset)* | Custom directory for audit log files. Defaults to `<project-root>/audit_logs/` |
| `AUDIT_LOG_INCLUDE_AI_ACTIVITY` | `"false"` | Set to `"true"` to append the engine's own model invocations to each entry (see [AI Processing Activity](#ai-processing-activity-model-invocations)). Opt-in; only consulted when `AUDIT_LOG_ENABLED` is on. |

When enabled, the server automatically:
1. Creates the audit log directory
2. Writes one JSON object per line to `audit.log`, rotating daily

### Skipped Endpoints

The following paths are **not** audit-logged:

- `/health`
- `/docs`, `/redoc`, `/openapi.json`
- `**/tasks/{id}/chatbot/stream` (streaming responses)
- `**/completions`

Unauthenticated requests (no `user_id` resolved) are also skipped.

## Payload Schema

Each line in `audit.log` is a JSON object with the following fields:

| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Unique identifier for this audit log entry |
| `user_id` | `string` | The authenticated user or API key that performed the request |
| `timestamp` | `datetime` (ISO 8601, UTC) | When the request was processed |
| `request_method` | `string` | HTTP method in lowercase (`"get"`, `"post"`, `"put"`, `"patch"`, `"delete"`) |
| `request_path` | `string` | The request URL path (e.g., `/api/v2/tasks/abc-123`) |
| `path_params` | `array` | Path parameters extracted from the URL (see below) |
| `response_ids` | `array` | IDs of resources returned or affected (see below) |
| `status_code` | `integer` | HTTP response status code |
| `organization_id` | `string \| null` | Organization context, if applicable |
| `audit_log_meta_version` | `string` | Always `"ArthurAuditLogEventV1"` |

### `path_params` entries

| Field | Type | Description |
|---|---|---|
| `param_name` | `string` | The URL parameter name (e.g., `"task_id"`) |
| `param_value` | `UUID \| string` | The parameter value |

### `response_ids` entries

Populated only for 2xx responses. Empty for error responses.

| Field | Type | Description |
|---|---|---|
| `response_type` | `string` | The response model type name (e.g., `"TaskResponse"`, `"TraceMetadataResponse"`) |
| `id_field` | `string` | Which field the ID was extracted from (defaults to `"id"`) |
| `response_id` | `UUID \| string` | The ID of the returned/affected resource |

## Examples

### Creating a task (POST)

```json
{
  "id": "dcb8288f-b42b-4c9b-87fc-678c733c3a7f",
  "user_id": "950e225a-b8aa-4546-95d2-d90ec81547c1",
  "timestamp": "2026-04-27T20:02:53.817861Z",
  "request_method": "post",
  "request_path": "/api/v2/tasks",
  "path_params": [],
  "response_ids": [
    {
      "response_type": "TaskResponse",
      "id_field": "id",
      "response_id": "d4b3a415-5cb0-4f2f-bf31-c5eadf1faced"
    }
  ],
  "status_code": 200,
  "audit_log_meta_version": "ArthurAuditLogEventV1"
}
```

### Getting a task by ID (GET)

```json
{
  "id": "98b08ced-81a1-4b01-b3e3-10892e8dcc0d",
  "user_id": "950e225a-b8aa-4546-95d2-d90ec81547c1",
  "timestamp": "2026-04-27T20:02:53.903564Z",
  "request_method": "get",
  "request_path": "/api/v2/tasks/d4b3a415-5cb0-4f2f-bf31-c5eadf1faced",
  "path_params": [
    {
      "param_name": "task_id",
      "param_value": "d4b3a415-5cb0-4f2f-bf31-c5eadf1faced"
    }
  ],
  "response_ids": [
    {
      "response_type": "TaskResponse",
      "id_field": "id",
      "response_id": "d4b3a415-5cb0-4f2f-bf31-c5eadf1faced"
    }
  ],
  "status_code": 200,
  "audit_log_meta_version": "ArthurAuditLogEventV1"
}
```

### Resource not found (404)

Error responses have an empty `response_ids` array since no resource was returned.

```json
{
  "id": "81dbf29c-c998-437b-82d9-d52a77ca73ad",
  "user_id": "master-key",
  "timestamp": "2026-04-17T20:13:30.900670Z",
  "request_method": "get",
  "request_path": "/api/v1/tasks/fcba8383-55ce-42ec-a5c3-528f3492ea8a/prompts/__chatbot_prompt__/versions/2",
  "path_params": [
    {
      "param_name": "task_id",
      "param_value": "fcba8383-55ce-42ec-a5c3-528f3492ea8a"
    },
    {
      "param_name": "prompt_name",
      "param_value": "__chatbot_prompt__"
    },
    {
      "param_name": "prompt_version",
      "param_value": "2"
    }
  ],
  "response_ids": [],
  "status_code": 404,
  "audit_log_meta_version": "ArthurAuditLogEventV1"
}
```

### Deleting a task (DELETE)

```json
{
  "id": "be45e7c9-a186-4976-881a-1777d338d53e",
  "user_id":"master-key",
  "timestamp":"2026-05-18T16:04:49.820283Z",
  "request_method": "delete",
  "request_path": "/api/v2/tasks/17fcfc6a-39db-4f28-8655-6ff06b7b140a",
  "path_params": [
    {
      "param_name": "task_id",
      "param_value": "17fcfc6a-39db-4f28-8655-6ff06b7b140a"
    }
  ],
  "response_ids": [],
  "status_code": 204,
  "audit_log_meta_version": "ArthurAuditLogEventV1"
}
```

## AI Processing Activity (Model Invocations)

By default an audit entry records **who called which endpoint** — the access trail. When `AUDIT_LOG_INCLUDE_AI_ACTIVITY=true`, each entry is additionally annotated with **the AI models the engine itself invoked while serving that request** — the hosted LLM judge calls (hallucination, sensitive-data, relevance, tool-selection) and the on-box ML classifiers (prompt injection, toxicity, PII).

When enabled:

- `audit_log_meta_version` becomes `"ArthurAuditLogEventV2"` and a `model_invocations` array is added. When disabled, entries remain the V1 `AuditLog` unchanged.
- Records are **metadata only** — no prompt or response content is ever written, consistent with the rest of the audit log.

### `model_invocations` entries

| Field | Type | Description |
|---|---|---|
| `model_name` | `string \| null` | The model invoked (LLM deployment name, or local classifier model id). `null` when it cannot be resolved. |
| `provider` | `string` | `"azure"`, `"openai"`, `"proxy"`, or `"local"` (on-box model). |
| `model_type` | `string` | `"llm"` for hosted judge calls, `"ml_classifier"` for on-box models. |
| `operation` | `string` | The check/operation that issued the call (e.g. `"hallucination"`, `"toxicity"`, `"pii"`). |
| `prompt_tokens` | `integer \| null` | Prompt tokens consumed. `null` for local models (not LLM-tokenized). |
| `completion_tokens` | `integer \| null` | Completion tokens produced. `null` for local models. |
| `total_tokens` | `integer \| null` | Total tokens consumed. `null` for local models. |
| `latency_ms` | `integer` | Wall-clock duration of the invocation. |
| `success` | `boolean` | Whether the invocation completed without raising. |
| `error_type` | `string \| null` | Exception class name when the invocation failed, else `null`. |

### Example (validate call, feature enabled)

```json
{
  "id": "9f0d6f5e-6c9a-4d5f-8f3a-2c1b0e7d4a11",
  "user_id": "master-key",
  "timestamp": "2026-07-10T14:40:02.167675Z",
  "request_method": "post",
  "request_path": "/api/v2/validate_prompt",
  "path_params": [],
  "response_ids": [{ "response_type": "ValidationResult", "id_field": "id", "response_id": "…" }],
  "status_code": 200,
  "audit_log_meta_version": "ArthurAuditLogEventV2",
  "model_invocations": [
    { "provider": "local", "model_type": "ml_classifier", "operation": "prompt_injection", "latency_ms": 24, "success": true },
    { "model_name": "gpt-4o", "provider": "azure", "model_type": "llm", "operation": "hallucination", "prompt_tokens": 812, "completion_tokens": 41, "total_tokens": 853, "latency_ms": 1032, "success": true }
  ]
}
```

### Coverage notes

The audit log is **request-scoped**, so this captures only model calls made while serving an authenticated API request:

- Model calls made **outside a request** — e.g. background continuous-eval runs — are not attached to any entry.
- Endpoints excluded from audit logging (`/completions`, the chatbot `/stream`) are not annotated.
- `model_name` may be `null` for some LLM calls (sensitive-data, relevance, tool-selection) where the deployment name is not available at the call site; `provider`, `operation`, tokens, and latency are still recorded.

## File Rotation

Logs are rotated daily using Python's `TimedRotatingFileHandler`:

- **Active file**: `audit.log`
- **Rotated files**: `audit.log.2026-05-17`, `audit.log.2026-05-16`, etc.
- **Retention**: Controlled by `AUDIT_LOG_RETENTION_DAYS` (default 365 days)
- **Timestamps**: UTC

## Kubernetes Deployment

When running GenAI Engine via the `arthur-genai-engine` Helm chart, audit logs can be persisted to a `PersistentVolumeClaim` so that rotated files survive pod restarts and rescheduling. Audit logging in Kubernetes is opt-in via `arthurGenaiEngineDeployment.auditLog.enabled`.

### Enabling

Set `arthurGenaiEngineDeployment.auditLog.enabled: true`. When enabled the chart:

- Creates a PVC and mounts it into each pod at `auditLog.mountPath` (both the [deployment](../../deployment/helm/genai-engine/templates/arthur-genai-engine-deployment.yaml) and the GPU [daemonset](../../deployment/helm/genai-engine/templates/arthur-genai-engine-daemonset.yaml)).
- Sets `AUDIT_LOG_ENABLED=true` and `AUDIT_LOG_OVERRIDE_PATH=<mountPath>` on the container, so the rotating file handler writes onto the mounted volume.

The PVC itself is defined in [arthur-genai-engine-audit-logs-pvc.yaml](../../deployment/helm/genai-engine/templates/arthur-genai-engine-audit-logs-pvc.yaml) with access mode `ReadWriteMany` and storage class `auditLog.storageClassName`. Its name (`arthur-genai-engine-audit-logs`, suffixed with `arthurResourceNameSuffix` when set) is computed by the chart and used automatically for the mount. The storage class must be backed by a shared-filesystem provisioner that supports `ReadWriteMany` (NFS, AWS EFS, Azure Files, CephFS, etc). The default block storage classes (EBS, GCE PD, Azure Disk) do **not** support `ReadWriteMany`, so the PVC will fail to bind with one of those.

### Volume Permissions

The container runs as a non-root user. On platforms that mount volumes owned by root (e.g. OpenShift), the engine cannot create `audit.log` and crash-loops with a `PermissionError`. Set `auditLog.fsGroup` to a group ID that owns the mount and makes it group-writable.

### Helm Values

| Value | Default | Description |
|---|---|---|
| `arthurGenaiEngineDeployment.auditLog.enabled` | `false` | Mount the audit-log PVC and enable audit logging to it |
| `arthurGenaiEngineDeployment.auditLog.mountPath` | `/home/nonroot/app/audit_logs` | Path inside the container where audit logs are written |
| `arthurGenaiEngineDeployment.auditLog.storageSize` | `10Gi` | Size requested for the audit log PVC. Enforced as a quota only on backends that support it (Azure Files; CephFS with a quota-capable kernel/client); ignored on AWS EFS and most NFS provisioners, which grow elastically. |
| `arthurGenaiEngineDeployment.auditLog.storageClassName` | _(unset)_ | `ReadWriteMany` storage class to back the PVC |
| `arthurGenaiEngineDeployment.auditLog.fsGroup` | _(unset)_ | Pod `fsGroup` so the non-root container can write to the volume (required on OpenShift) |
