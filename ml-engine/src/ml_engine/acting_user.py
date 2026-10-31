"""The Platform user a job is running for, so GenAI Engine changes are attributed to them.

The job executor sets it for the duration of each job from `job.triggered_by_user`.
Connectors that call the GenAI Engine with the deployment's admin key read it and
send it as the X-Arthur-On-Behalf-Of header, which the engine records as the
author of the change. Scheduled jobs have no triggering user, so nothing is sent.
"""

from contextvars import ContextVar

from arthur_client.api_bindings import Job

ON_BEHALF_OF_HEADER = "X-Arthur-On-Behalf-Of"

ACTING_USER: ContextVar[str | None] = ContextVar("acting_user", default=None)


def acting_user_of(job: Job) -> str | None:
    """The email of the user who triggered the job, or their id when there is none."""
    user = job.triggered_by_user
    if user is None:
        return None
    return str(user.email) if user.email else str(user.id)
