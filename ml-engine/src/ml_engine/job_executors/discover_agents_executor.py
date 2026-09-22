"""
Executor for the DISCOVER_AGENTS job.

Two shapes of job arrive here. A job carrying a materialized discovery source config
(D-06) is a scan of that one source: it runs through the connector seams in
`discovery_scan`, publishing each batch as it arrives so a mid-scan failure keeps what
it already collected. A job carrying no config is the older GCP data-plane sweep,
which triggers synchronous polling in GenAI Engine and syncs the enriched agent tasks
to the Agents API. Both shapes are live until D-14 migrates GCP onto a source config.
"""

import logging
from math import ceil
from typing import List, NoReturn, Optional

from arthur_client.api_bindings import Agent as ScopeAgent
from arthur_client.api_bindings import (
    AgentsV1Api,
    DiscoverAgentsJobSpec,
    DiscoverySourceConfigSpec,
    DiscoverySourcesV1Api,
    Job,
    PutAgents,
)
from genai_client import (
    AgentDiscoveryApi,
    ApiClient,
    Configuration,
    EnrichedTaskResponse,
    TasksApi,
)

from job_executors.discovery_scan import (
    SOURCE_SCANNERS,
    DiscoveryRecordSink,
    DiscoveryScanOutcome,
    DiscoverySourceScanner,
    UnsupportedDiscoveryVendorError,
    finalize_outcome,
    run_source_scan,
)


class DiscoverAgentsExecutor:
    def __init__(
        self,
        agents_client: AgentsV1Api,
        logger: logging.Logger,
        genai_engine_url: str,
        genai_engine_api_key: str,
        discovery_sources_client: Optional[DiscoverySourcesV1Api] = None,
        record_sink: Optional[DiscoveryRecordSink] = None,
        scanners: Optional[dict[str, DiscoverySourceScanner]] = None,
    ) -> None:
        self.agents_client = agents_client
        self.logger = logger
        self.genai_engine_url = genai_engine_url
        self.genai_engine_api_key = genai_engine_api_key
        self.discovery_sources_client = discovery_sources_client
        self.record_sink = record_sink
        self.scanners = SOURCE_SCANNERS if scanners is None else scanners

    def execute(self, job: Job, job_spec: DiscoverAgentsJobSpec) -> None:
        """Run the job, on whichever of the two shapes it carries."""
        if (
            job_spec.discovery_source_config is not None
            or job_spec.discovery_source_config_id is not None
        ):
            self._execute_source_scan(job, job_spec)
            return

        self._execute_gcp_sweep(job_spec)

    def _execute_source_scan(
        self,
        job: Job,
        job_spec: DiscoverAgentsJobSpec,
    ) -> None:
        """Scan the single source config this job was dispatched for.

        The config is read from the job rather than fetched by ID: D-06 snapshots it at
        dispatch so the run stays reproducible and the query that ran is the query
        recorded, even if the config is edited or deleted afterwards.
        """
        try:
            config = self._require_source_config(job_spec)
        except ValueError as e:
            self._fail_before_scan(self._unscannable_outcome(job, job_spec), e)

        workspace_id = str(job_spec.workspace_id)
        data_plane_id = str(job_spec.data_plane_id)
        lookback_hours = self._lookback_hours(job_spec, config)

        outcome = DiscoveryScanOutcome(
            discovery_source_config_id=str(job_spec.discovery_source_config_id),
            discovery_source_config_name=config.name,
            discovery_source_id=str(config.discovery_source_id),
            vendor=config.vendor,
            job_id=str(job.id),
            scan_id=str(job_spec.scan_id) if job_spec.scan_id else None,
            lookback_hours=lookback_hours,
        )

        self.logger.info(
            f"Starting discovery scan of source config '{config.name}' "
            f"({config.vendor}) over the last {lookback_hours}h",
            extra={
                "workspace_id": workspace_id,
                "data_plane_id": data_plane_id,
                "discovery_source_config_id": outcome.discovery_source_config_id,
                "vendor": config.vendor,
            },
        )

        scanner = self.scanners.get(config.vendor)
        if scanner is None:
            self._fail_before_scan(
                outcome,
                UnsupportedDiscoveryVendorError(
                    f"No discovery connector is registered for vendor "
                    f"'{config.vendor}' (source config '{config.name}')",
                ),
            )

        if self.record_sink is None:
            self._fail_before_scan(
                outcome,
                RuntimeError(
                    "No discovery record sink is configured; discovery records cannot "
                    "be published until task resolution (D-08) lands.",
                ),
            )

        credentials = self._source_credentials(outcome)

        run_source_scan(
            config=config,
            lookback_hours=lookback_hours,
            workspace_id=workspace_id,
            data_plane_id=data_plane_id,
            outcome=outcome,
            scanner=scanner,
            sink=self.record_sink,
            logger=self.logger,
            credentials=credentials,
        )

        self.logger.info(
            f"Discovery scan of source config '{config.name}' published "
            f"{outcome.records_published} record(s)",
            extra={
                "discovery_source_config_id": outcome.discovery_source_config_id,
                "records_published": outcome.records_published,
            },
        )

    def _source_credentials(
        self,
        outcome: DiscoveryScanOutcome,
    ) -> dict[str, Optional[str]]:
        """Read this config's sensitive fields, once, at the point of the scan.

        Deliberately not carried in the job spec -- the route says as much -- so it is
        fetched here rather than dispatched with the job. The values serve twice: the
        scanner authenticates with them, and anything this job writes to the job log
        has them removed by exact match, which is the only form of redaction that does
        not depend on guessing how a vendor SDK formats its errors.
        """
        if self.discovery_sources_client is None:
            self._fail_before_scan(
                outcome,
                RuntimeError(
                    "No discovery sources client is configured; source credentials "
                    "cannot be read.",
                ),
            )

        config_id = outcome.discovery_source_config_id
        try:
            credentials: dict[str, Optional[str]] = (
                self.discovery_sources_client.retrieve_discovery_source_credentials(
                    config_id,
                )
            )
            return credentials
        except Exception as e:
            # Reported without a scrub set: nothing was returned, so there is no
            # credential to take back out, and the failure names only the config.
            self._fail_before_scan(outcome, e)

    def _unscannable_outcome(
        self,
        job: Job,
        job_spec: DiscoverAgentsJobSpec,
    ) -> DiscoveryScanOutcome:
        """The outcome for a job too malformed to say what it meant to scan.

        Whichever half of the config pair the dispatcher left out is reported as null
        rather than filled in with a placeholder: the run store aggregates per source,
        and a stand-in vendor or name would land there as though a real source had
        been scanned. What the record is for is that the run is accounted for at all.
        """
        config = job_spec.discovery_source_config
        return DiscoveryScanOutcome(
            discovery_source_config_id=(
                str(job_spec.discovery_source_config_id)
                if job_spec.discovery_source_config_id is not None
                else None
            ),
            discovery_source_config_name=config.name if config is not None else None,
            discovery_source_id=(
                str(config.discovery_source_id) if config is not None else None
            ),
            vendor=config.vendor if config is not None else None,
            job_id=str(job.id),
            scan_id=str(job_spec.scan_id) if job_spec.scan_id else None,
            lookback_hours=(
                self._lookback_hours(job_spec, config)
                if config is not None
                else (
                    int(job_spec.lookback_hours)
                    if job_spec.lookback_hours is not None
                    else None
                )
            ),
        )

    def _fail_before_scan(
        self,
        outcome: DiscoveryScanOutcome,
        error: Exception,
    ) -> NoReturn:
        """End a run that failed before the source was ever contacted.

        These failures owe the Platform the same outcome record as a scan that got as
        far as the vendor, so they close the run through the shared finalization rather
        than raising straight out and leaving the run unreported.
        """
        outcome.record_failure(error)
        self.logger.error(
            outcome.error,
            extra={"vendor": outcome.vendor},
        )
        finalize_outcome(outcome, self.logger)
        raise error

    @staticmethod
    def _require_source_config(
        job_spec: DiscoverAgentsJobSpec,
    ) -> DiscoverySourceConfigSpec:
        """Hold the dispatcher to one config per job.

        D-06 guarantees this on the Platform side; failing loudly here is what keeps a
        half-populated spec from being scanned as though it named a source. A job
        missing either half is a dispatch bug, and guessing the other half would scan
        something nobody asked for.
        """
        if job_spec.discovery_source_config_id is None:
            raise ValueError(
                "Discovery scan job carries a source config with no "
                "discovery_source_config_id.",
            )
        if job_spec.discovery_source_config is None:
            raise ValueError(
                f"Discovery scan job names source config "
                f"{job_spec.discovery_source_config_id} but carries no materialized "
                f"config to scan.",
            )
        return job_spec.discovery_source_config

    @staticmethod
    def _lookback_hours(
        job_spec: DiscoverAgentsJobSpec,
        config: DiscoverySourceConfigSpec,
    ) -> int:
        """The window to scan, in whole hours.

        D-06 already rounds the config's window up into `lookback_hours`; recomputing
        it from the config is the fallback for a job dispatched before that landed, and
        keeps the two from disagreeing about which window actually ran.
        """
        if job_spec.lookback_hours is not None:
            return int(job_spec.lookback_hours)
        # Rounded up, like D-06 does: a 90-minute window scans 2 hours rather than 1.
        return ceil(int(config.lookback_window_seconds) / 3600)

    def _execute_gcp_sweep(self, job_spec: DiscoverAgentsJobSpec) -> None:
        """Trigger synchronous polling then sync enriched agent-tasks to the Agents API."""
        workspace_id = str(job_spec.workspace_id)
        data_plane_id = str(job_spec.data_plane_id)

        self.logger.info(
            f"Starting agent discovery for workspace {workspace_id}, "
            f"data plane {data_plane_id}",
            extra={
                "workspace_id": workspace_id,
                "data_plane_id": data_plane_id,
            },
        )

        try:
            self._trigger_synchronous_polling()
            enriched_tasks = self._fetch_enriched_agent_tasks()
            self._publish_to_agents_api(workspace_id, data_plane_id, enriched_tasks)
        except Exception as e:
            self.logger.error(
                f"Agents API sync failed for data plane {data_plane_id}: {e}",
                extra={"data_plane_id": data_plane_id, "error": str(e)},
                exc_info=True,
            )
            raise

        self.logger.info(
            f"Agent discovery completed for data plane {data_plane_id}",
            extra={"workspace_id": workspace_id, "data_plane_id": data_plane_id},
        )

    def _trigger_synchronous_polling(self) -> None:
        """Trigger synchronous polling to ensure trace data is fetched before querying agent-tasks."""
        self.logger.info("Triggering synchronous agent polling")

        config = Configuration(
            host=self.genai_engine_url,
            access_token=self.genai_engine_api_key,
        )

        with ApiClient(config) as api_client:
            api = AgentDiscoveryApi(api_client)
            response = (
                api.execute_all_agent_polling_api_v1_agent_polling_execute_all_post(
                    wait_for_completion=True,
                    timeout=120,  # 2 minute timeout
                )
            )

        self.logger.info(
            f"Synchronous polling completed: discovered={response.discovered}, "
            f"traces_fetched={response.traces_fetched}",
            extra={
                "discovered": response.discovered,
                "traces_fetched": response.traces_fetched,
            },
        )

    def _fetch_enriched_agent_tasks(self) -> List[EnrichedTaskResponse]:
        """Fetch enriched agent tasks from the GenAI Engine agent-tasks endpoint."""
        config = Configuration(
            host=self.genai_engine_url,
            access_token=self.genai_engine_api_key,
        )

        with ApiClient(config) as api_client:
            api = TasksApi(api_client)
            enriched_tasks: List[EnrichedTaskResponse] = (
                api.get_agent_tasks_api_v2_agent_tasks_get()
            )

        self.logger.info(
            f"Fetched {len(enriched_tasks)} enriched agent task(s) from GenAI Engine",
            extra={"num_tasks": len(enriched_tasks)},
        )
        return enriched_tasks

    def _publish_to_agents_api(
        self,
        workspace_id: str,
        data_plane_id: str,
        enriched_tasks: List[EnrichedTaskResponse],
    ) -> None:
        """Convert enriched tasks to Agent objects and upsert via the Agents API."""
        if not enriched_tasks:
            self.logger.info("No enriched tasks to publish to Agents API")
            return

        agent_objects = [
            self._convert_enriched_task_to_agent(task, data_plane_id)
            for task in enriched_tasks
        ]

        put_request = PutAgents(agents=agent_objects)
        response = self.agents_client.put_agents(
            workspace_id=workspace_id,
            put_agents=put_request,
        )

        self.logger.info(
            f"Published {len(response.agents)} agent(s) to Agents API",
            extra={"workspace_id": workspace_id, "num_upserted": len(response.agents)},
        )

    @staticmethod
    def _convert_enriched_task_to_agent(
        enriched_task: EnrichedTaskResponse,
        data_plane_id: str,
    ) -> ScopeAgent:
        """Convert a genai_client EnrichedTaskResponse to an arthur_client Agent.

        Bridges between the two auto-generated client libraries by converting
        via dict representation and remapping fields.
        """
        task_dict = enriched_task.to_dict()

        agent_dict = {
            "name": task_dict.get("name"),
            "task_id": task_dict.get("id"),
            "data_plane_id": data_plane_id,
            "creation_source": task_dict.get("creation_source"),
            "model_id": None,
            "num_spans": task_dict.get("num_spans") or 0,
            "is_autocreated": task_dict.get("is_autocreated", True),
            "rules": task_dict.get("rules") or [],
            "last_fetched": task_dict.get("last_fetched"),
            "tools": task_dict.get("tools") or [],
            "sub_agents": task_dict.get("sub_agents") or [],
            "llm_models": task_dict.get("models") or [],
            "data_sources": task_dict.get("data_sources") or [],
        }

        return ScopeAgent.from_dict(agent_dict)
