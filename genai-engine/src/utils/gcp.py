import logging

logger = logging.getLogger(__name__)


def parse_gcp_resource_path(
    resource_id: str,
) -> tuple[str | None, str | None, str | None]:
    """Parse a GCP resource path into (project_id, region, reasoning_engine_id).

    Handles multiple resource path formats:
    - projects/{project}/locations/{location}/reasoningEngines/{id}
    - projects/{project}/locations/{location}/agentEngines/{id}
    - //aiplatform.googleapis.com/projects/{project}/locations/{location}/reasoningEngines/{id}

    Returns:
        Tuple of (gcp_project_id, gcp_region, gcp_reasoning_engine_id),
        or (None, None, None) if parsing fails.
    """
    try:
        path = resource_id
        if path.startswith("//"):
            parts = path.split("/", 3)
            if len(parts) > 3:
                path = parts[3]

        parts = path.split("/")

        gcp_project_id = None
        gcp_region = None
        gcp_reasoning_engine_id = None

        if "projects" in parts:
            idx = parts.index("projects")
            if len(parts) > idx + 1:
                gcp_project_id = parts[idx + 1]

        if "locations" in parts:
            idx = parts.index("locations")
            if len(parts) > idx + 1:
                gcp_region = parts[idx + 1]

        for engine_type in ("reasoningEngines", "agentEngines"):
            if engine_type in parts:
                idx = parts.index(engine_type)
                if len(parts) > idx + 1:
                    gcp_reasoning_engine_id = parts[idx + 1]
                    break

        return gcp_project_id, gcp_region, gcp_reasoning_engine_id

    except (IndexError, ValueError) as e:
        logger.warning(f"Failed to parse GCP resource path '{resource_id}': {str(e)}")
        return None, None, None
