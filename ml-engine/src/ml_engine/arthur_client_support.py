"""What the installed arthur-client can do, for job kinds that arrive ahead of it.

An executor written against a Platform API that has not been published in an
arthur-client yet must not take the rest of the engine down with it: `job_executor`
imports every executor at module load, so one missing model would fail every job kind.
Such an executor is imported and dispatched only when the client it needs is installed.
"""

import arthur_client.api_bindings as api_bindings
from arthur_client.api_bindings import (
    DiscoverySourcesV1Api,
    FetchDiscoveredAgentsJobSpec,
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

# The wire value of the ONBOARDING_ANALYSIS job kind, compared by value: no published
# client has the member yet.
ONBOARDING_ANALYSIS_JOB_KIND = "onboarding_analysis"

# The Platform's result route for the job, as the generator names it: the "Onboarding
# V1" tag and the `put_onboarding_analysis_result` operation.
ONBOARDING_RESULT_API = "OnboardingV1Api"
ONBOARDING_RESULT_METHOD = "put_onboarding_analysis_result"
ONBOARDING_RESULT_MODEL = "PutOnboardingAnalysisResult"


def client_supports_onboarding_analysis() -> bool:
    """Whether the installed client has the job kind and the route its result goes to."""
    result_api = getattr(api_bindings, ONBOARDING_RESULT_API, None)
    return (
        any(kind.value == ONBOARDING_ANALYSIS_JOB_KIND for kind in JobKind)
        and hasattr(api_bindings, ONBOARDING_RESULT_MODEL)
        and result_api is not None
        and hasattr(result_api, ONBOARDING_RESULT_METHOD)
    )


ONBOARDING_ANALYSIS_SUPPORTED = client_supports_onboarding_analysis()

ONBOARDING_ANALYSIS_UNSUPPORTED_MESSAGE = (
    "This engine's arthur-client does not support onboarding analysis "
    f"({ONBOARDING_ANALYSIS_JOB_KIND}) jobs; upgrade arthur-client."
)

# Whether this client's dequeue request can say the engine runs onboarding analysis
# jobs. As with Test Connection, the Platform hands ONBOARDING_ANALYSIS jobs only to an
# engine whose last dequeue said so, and refuses to start an analysis on any other.
DEQUEUE_DECLARES_ONBOARDING_ANALYSIS = (
    "onboarding_analysis" in JobDequeueParameters.model_fields
)

# Whether this client can say the engine runs task syncs, fetches with no discovery
# source, and read one: a client whose fetch spec requires a source cannot. The Platform
# hands a task sync only to an engine whose last dequeue said so.
DEQUEUE_DECLARES_AGENT_TASK_SYNC = (
    "agent_task_sync" in JobDequeueParameters.model_fields
    and not FetchDiscoveredAgentsJobSpec.model_fields[
        "discovery_source_id"
    ].is_required()
)
