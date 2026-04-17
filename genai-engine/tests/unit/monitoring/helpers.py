import json
import os
from typing import Set

from arthur_common.models.audit_log_schemas import AuditLog

from tests.clients.base_test_client import TEST_AUDIT_LOG_DIR

AUDIT_LOG_FILE = os.path.join(TEST_AUDIT_LOG_DIR, "audit.log")


def read_audit_entries() -> list[AuditLog]:
    if not os.path.exists(AUDIT_LOG_FILE):
        return []

    with open(AUDIT_LOG_FILE) as f:
        return [AuditLog.model_validate(json.loads(line)) for line in f if line.strip()]


def get_audit_logs_with_ids(entries: list[AuditLog], ids: Set[str]) -> list[AuditLog]:
    """
    Filter audit log entries to those referencing any of the given IDs
    in path_params or response_ids.
    """
    result = []

    for entry in entries:
        path_param_values = {str(p.param_value) for p in entry.path_params}
        response_id_values = {str(r.response_id) for r in entry.response_ids}

        if (path_param_values | response_id_values) & ids:
            result.append(entry)

    return result
