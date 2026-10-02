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
