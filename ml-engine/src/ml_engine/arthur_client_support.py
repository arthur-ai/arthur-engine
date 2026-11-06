"""What the installed arthur-client can do, for job kinds that arrive ahead of it.

An executor written against a Platform API that has not been published in an
arthur-client yet must not take the rest of the engine down with it: `job_executor`
imports every executor at module load, so one missing model would fail every job kind.
Such an executor is imported and dispatched only when the client it needs is installed.
"""

import arthur_client.api_bindings as api_bindings
from arthur_client.api_bindings import (
    DiscoverySourcesV1Api,
    JobDequeueParameters,
    JobKind,
)
from arthur_common.models import task_job_specs

# The wire value of JobKind.TEST_DISCOVERY_SOURCE, compared by value so a job of this
# kind can be named even by a client whose JobKind does not have the member.
TEST_DISCOVERY_SOURCE_JOB_KIND = "test_discovery_source"

_TEST_DISCOVERY_SOURCE_MODELS = (
    "TestDiscoverySourceJobSpec",
    "PutDiscoverySourceTestResult",
    "DiscoverySourceReachability",
    "DiscoverySourceTestError",
    "DiscoverySourceTestErrorCategory",
    "DiscoverySourceTestOutcome",
    "OutputColumnCheckResult",
)

TEST_DISCOVERY_SOURCE_UNSUPPORTED_MESSAGE = (
    "This engine's arthur-client does not support test-connection "
    f"({TEST_DISCOVERY_SOURCE_JOB_KIND}) jobs; upgrade arthur-client."
)


def client_supports_test_discovery_source() -> bool:
    """Whether the installed client has D-12's job spec, result models and route."""
    return (
        all(hasattr(api_bindings, name) for name in _TEST_DISCOVERY_SOURCE_MODELS)
        and hasattr(DiscoverySourcesV1Api, "put_discovery_source_test_result")
        and any(kind.value == TEST_DISCOVERY_SOURCE_JOB_KIND for kind in JobKind)
    )


TEST_DISCOVERY_SOURCE_SUPPORTED = client_supports_test_discovery_source()

# Whether this client's dequeue request can say the engine runs Test Connection jobs.
# The Platform hands TEST_DISCOVERY_SOURCE jobs only to an engine whose last dequeue said
# so, which is what keeps them away from engines that would fail to read them. A client
# without the field cannot say it, and an engine on one is correctly left out.
DEQUEUE_DECLARES_DISCOVERY_SOURCE_TEST = (
    "discovery_source_test" in JobDequeueParameters.model_fields
)

# The wire values of JobKind.KILL_AGENT and JobKind.REENABLE_AGENT, compared by value
# for the same reason as TEST_DISCOVERY_SOURCE_JOB_KIND.
KILL_AGENT_JOB_KIND = "kill_agent"
REENABLE_AGENT_JOB_KIND = "reenable_agent"

_KILL_SWITCH_JOB_SPECS = ("KillAgentJobSpec", "ReenableAgentJobSpec")

KILL_SWITCH_UNSUPPORTED_MESSAGE = (
    "This engine's arthur-client or arthur-common does not support kill switch "
    f"({KILL_AGENT_JOB_KIND}, {REENABLE_AGENT_JOB_KIND}) jobs; upgrade both."
)


def client_supports_kill_switch() -> bool:
    """Whether the installed client knows both kill switch kinds, and arthur-common
    has the job specs the executors parse them with.

    arthur-common is checked here too: like the other task management kinds, these
    specs are read from the raw job with its models, which arrive in a release of
    their own.
    """
    kinds = {kind.value for kind in JobKind}
    return (
        KILL_AGENT_JOB_KIND in kinds
        and REENABLE_AGENT_JOB_KIND in kinds
        and all(hasattr(task_job_specs, name) for name in _KILL_SWITCH_JOB_SPECS)
    )


KILL_SWITCH_SUPPORTED = client_supports_kill_switch()
