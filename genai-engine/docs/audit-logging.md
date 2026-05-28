# Audit Logging

Arthur GenAI Engine includes built-in audit logging that records every authenticated API request as a structured JSON event. Logs are written to rotating files on disk.

## Enabling Audit Logging

Audit logging is **enabled by default**. Control it with these environment variables:

| Variable | Default | Description |
|---|---|---|
| `AUDIT_LOG_ENABLED` | `"true"` | Set to `"false"` to disable audit logging entirely |
| `AUDIT_LOG_RETENTION_DAYS` | `365` | Number of daily log files to retain before rotation deletes them |
| `AUDIT_LOG_OVERRIDE_PATH` | *(unset)* | Custom directory for audit log files. Defaults to `<project-root>/audit_logs/` |

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

## File Rotation

Logs are rotated daily using Python's `TimedRotatingFileHandler`:

- **Active file**: `audit.log`
- **Rotated files**: `audit.log.2026-05-17`, `audit.log.2026-05-16`, etc.
- **Retention**: Controlled by `AUDIT_LOG_RETENTION_DAYS` (default 365 days)
- **Timestamps**: UTC
