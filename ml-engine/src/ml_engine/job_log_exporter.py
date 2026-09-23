import logging
import traceback
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator

from arthur_client.api_bindings import (
    JobError,
    JobErrors,
    JobLog,
    JobLogLevel,
    JobLogs,
    JobsV1Api,
)

from log_redaction import SecretRedactingFilter

logger = logging.getLogger(__name__)

logging_to_scope_levels = {
    logging.DEBUG: JobLogLevel.DEBUG,
    logging.INFO: JobLogLevel.INFO,
    logging.WARNING: JobLogLevel.WARNING,
    logging.ERROR: JobLogLevel.ERROR,
    logging.CRITICAL: JobLogLevel.CRITICAL,
}


class ScopeJobLogExporter(logging.Handler):
    def __init__(self, job_id: str, job_run_id: str, jobs_client: JobsV1Api) -> None:
        self.job_id = job_id
        self.job_run_id = job_run_id
        self.job_client = jobs_client
        # Installed on the job's logger by ExportContextedLogger; held here too so the
        # payloads built below are scrubbed even if a record reaches this handler some
        # other way.
        self.redactor = SecretRedactingFilter()
        logging.Handler.__init__(self=self)

    def emit(self, record: logging.LogRecord) -> None:
        # TODO: add to queue here and export via async thread
        log = JobLog(
            log_level=logging_to_scope_levels[record.levelno],
            log=self.redactor.redact(record.getMessage()),
            log_timestamp=datetime.fromtimestamp(record.created),
        )
        try:
            self.job_client.post_job_logs(
                self.job_id,
                self.job_run_id,
                JobLogs(logs=[log]),
            )
        except Exception as exc:
            logger.error("Failed to export logs")
            logger.error(str(exc), exc_info=True)

        # The traceback and the error both carry the exception's own message, so they
        # need the same scrub as the log line -- a credential redacted from the message
        # alone would still ship twice here.
        if record.levelno == logging.ERROR and record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            formatted_traceback = record.exc_text or "".join(
                traceback.format_exception(
                    exc_type,
                    exc_value,
                    exc_traceback,
                ),
            )
            self.job_client.post_job_logs(
                self.job_id,
                self.job_run_id,
                JobLogs(
                    logs=[
                        JobLog(
                            log_level=JobLogLevel.ERROR,
                            log=self.redactor.redact(formatted_traceback),
                            log_timestamp=datetime.fromtimestamp(record.created),
                        ),
                    ],
                ),
            )
            self.job_client.post_job_errors(
                self.job_id,
                self.job_run_id,
                job_errors=JobErrors(
                    errors=[JobError(error=self.redactor.redact(str(exc_value)))]
                ),
            )


# Important thing here is to make sure handlers and removed and closed, otherwise they'll create a memory leak
@contextmanager
def ExportContextedLogger(
    logger: logging.Logger,
    handler: ScopeJobLogExporter,
) -> Generator[None, Any, Any]:
    logger.addFilter(handler.redactor)
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)
        logger.removeFilter(handler.redactor)
        handler.close()
