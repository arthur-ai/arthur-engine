"""Unit tests for the legacy agent-metadata mapping in internal_schemas."""

import pytest
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    EndpointAgentCreationSource,
    GCPAgentCreationSource,
    ManualAgentCreationSource,
    OTELAgentCreationSource,
    SIEMAgentCreationSource,
    SourceAddress,
)
from pydantic import ValidationError

from schemas.internal_schemas import _legacy_gcp_metadata

VERTEX_ADDRESS = SourceAddress(
    instance="proj-a",
    resource_id="eng-1",
    scope="us-central1",
)


@pytest.mark.unit_tests
def test_deprecated_gcp_shape_maps_to_gcp_metadata():
    metadata = _legacy_gcp_metadata(
        GCPAgentCreationSource(
            gcp_project_id="proj-a",
            gcp_region="us-central1",
            gcp_reasoning_engine_id="eng-1",
        ),
    )
    assert metadata is not None
    assert (metadata.project_id, metadata.region, metadata.resource_id) == (
        "proj-a",
        "us-central1",
        "eng-1",
    )


@pytest.mark.unit_tests
def test_migrated_vertex_shape_maps_identically():
    """The D-14 regression guard.

    A Vertex finding is a CLOUD source with vendor gcp_vertex once its stored rows
    are migrated off the deprecated variant. Without this branch it falls through to
    EXTERNAL, and because the old code's `else` swallowed everything, CI stays green
    while every Vertex task quietly stops reporting as GCP.
    """
    deprecated = _legacy_gcp_metadata(
        GCPAgentCreationSource(
            gcp_project_id="proj-a",
            gcp_region="us-central1",
            gcp_reasoning_engine_id="eng-1",
        ),
    )
    migrated = _legacy_gcp_metadata(
        CloudAgentCreationSource(vendor="gcp_vertex", address=VERTEX_ADDRESS),
    )
    assert migrated == deprecated


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "creation_source",
    [
        CloudAgentCreationSource(vendor="aws_bedrock", address=VERTEX_ADDRESS),
        SIEMAgentCreationSource(vendor="splunk_enterprise", address=VERTEX_ADDRESS),
        EndpointAgentCreationSource(vendor="jamf_pro", address=VERTEX_ADDRESS),
        OTELAgentCreationSource(),
        ManualAgentCreationSource(),
    ],
)
def test_everything_else_has_no_gcp_metadata(creation_source):
    """Which the caller renders as EXTERNAL.

    Not a loss: the legacy RegisteredAgentProvider has exactly two values, so a
    Bedrock or Splunk finding has no truer answer available in this response shape.
    """
    assert _legacy_gcp_metadata(creation_source) is None


@pytest.mark.unit_tests
def test_a_cloud_source_from_another_vendor_is_not_treated_as_vertex():
    """The vendor, not the class, is what makes it GCP."""
    assert (
        _legacy_gcp_metadata(
            CloudAgentCreationSource(vendor="aws_bedrock", address=VERTEX_ADDRESS),
        )
        is None
    )


@pytest.mark.unit_tests
def test_a_region_less_cloud_source_cannot_reach_this_mapping():
    """The upstream guarantee the region cast depends on.

    _legacy_gcp_metadata narrows `address.scope` to str with no runtime check,
    which is sound only while arthur_common rejects a CLOUD source that carries no
    region. Asserted here, in the repo that relies on it, so a downgrade or a
    loosened validator fails as this test rather than as a region of "" on the
    wire -- the shape the `or ""` fallback used to produce.
    """
    with pytest.raises(ValidationError):
        CloudAgentCreationSource(
            vendor="gcp_vertex",
            address=SourceAddress(instance="proj-a", resource_id="eng-1"),
        )


@pytest.mark.unit_tests
def test_an_empty_region_is_rejected_too():
    """The exact value the old fallback substituted."""
    with pytest.raises(ValidationError):
        CloudAgentCreationSource(
            vendor="gcp_vertex",
            address=SourceAddress(instance="proj-a", resource_id="eng-1", scope=""),
        )
