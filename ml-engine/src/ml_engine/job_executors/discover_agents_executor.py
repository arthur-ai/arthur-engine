"""
Executor for the DISCOVER_AGENTS job.

Two shapes of job arrive here. A job carrying a materialized discovery source config
(D-06) is a scan of that one source: it runs through the connector seams in
`discovery_scan`, publishing each batch as it arrives so a mid-scan failure keeps what
it already collected, and then chains a FETCH_DISCOVERED_AGENTS job (D-10) that surfaces
what it found to the Platform. A job carrying no config is the older GCP data-plane
sweep, which triggers synchronous polling in GenAI Engine and syncs the enriched agent
tasks to the Agents API. Both shapes are live until D-14 migrates GCP onto a source
config.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, NoReturn, Optional

from arthur_client.api_bindings import (
    AgentsV1Api,
    DiscoverAgentsJobSpec,
    DiscoverySourceConfigSpec,
    DiscoverySourcesV1Api,
    FetchDiscoveredAgentsJobSpec,
    Job,
    JobsV1Api,
    PostJob,
    PostJobBatch,
    PostJobKind,
    PostJobSpec,
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
    DiscoveryScannerFactory,
    DiscoveryScanOutcome,
    UnsupportedDiscoveryVendorError,
    finalize_outcome,
    run_source_scan,
)
from job_executors.fetch_discovered_agents_executor import publish_enriched_tasks
from log_redaction import register_secrets, secret_values

# How far before the scan started its chained fetch reads from. GenAI Engine stamps a
# report with its own clock and this engine records the start with its own, so the
# window opens early by enough to absorb skew between the two. Re-reading a task the
# previous fetch already uploaded costs an upsert; missing one costs an agent that
# stays invisible until the standalone fetch.
CHAINED_FETCH_SKEW = timedelta(minutes=10)


class DiscoverAgentsExecutor:
    def __init__(
        self,
        agents_client: AgentsV1Api,
        logger: logging.Logger,
        genai_engine_url: str,
        genai_engine_api_key: str,
        discovery_sources_client: Optional[DiscoverySourcesV1Api] = None,
        record_sink: Optional[DiscoveryRecordSink] = None,
        scanners: Optional[dict[str, DiscoveryScannerFactory]] = None,
        jobs_client: Optional[JobsV1Api] = None,
    ) -> None:
        self.agents_client = agents_client
        self.logger = logger
        self.genai_engine_url = genai_engine_url
        self.genai_engine_api_key = genai_engine_api_key
        self.discovery_sources_client = discovery_sources_client
        self.record_sink = record_sink
        self.jobs_client = jobs_client
        # A copy, so registering a scanner on one executor cannot change the registry
        # every other executor in the process reads.
        self.scanners = dict(SOURCE_SCANNERS if scanners is None else scanners)

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
            lookback_hours = self._lookback_hours(job_spec)
        except ValueError as e:
            self._fail_before_scan(self._unscannable_outcome(job, job_spec), e)

        workspace_id = str(job_spec.workspace_id)
        data_plane_id = str(job_spec.data_plane_id)

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

        scanner_factory = self.scanners.get(config.vendor)
        if scanner_factory is None:
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
                    "No discovery record sink is configured, so this scan has nowhere "
                    "to publish. The job runner supplies one; an executor built without "
                    "it can scan a source and then discard everything it read.",
                ),
            )

        credentials = self._source_credentials(outcome)
        source_fields = self._source_fields(config, outcome)

        scan_started_at = datetime.now(timezone.utc)
        try:
            run_source_scan(
                config=config,
                lookback_hours=lookback_hours,
                workspace_id=workspace_id,
                data_plane_id=data_plane_id,
                outcome=outcome,
                scanner=scanner_factory(),
                sink=self.record_sink,
                logger=self.logger,
                credentials=credentials,
                source_fields=source_fields,
            )
        except Exception:
            # A failed scan keeps what it published before it failed, and those
            # records are only visible once something fetches them.
            if outcome.records_published:
                self._chain_fetch_after_failed_scan(job, job_spec, scan_started_at)
            raise
        self._chain_fetch(job, job_spec, scan_started_at)

        self.logger.info(
            f"Discovery scan of source config '{config.name}' published "
            f"{outcome.records_published} record(s)",
            extra={
                "discovery_source_config_id": outcome.discovery_source_config_id,
                "records_published": outcome.records_published,
            },
        )

    def _chain_fetch(
        self,
        job: Job,
        job_spec: DiscoverAgentsJobSpec,
        scan_started_at: datetime,
    ) -> None:
        """Enqueue the fetch that surfaces this scan's findings to the Platform.

        Submitted by this job rather than dispatched by the Platform, the way the
        metrics job submits its alert check: there is no DAG runner to express "after
        this scan", so the scan says so itself. Scoped to the source rather than this
        config, because the fetch reads by source, and windowed to reports since this
        scan began, because the standalone fetch already covers everything older.

        No nonce. A retried scan chains again, and the second fetch is an upsert of
        the same agents, so nothing needs deduplicating -- whereas a nonce keyed on
        this job would refuse the fetch after a retry that published more.

        A failure to enqueue fails the job even though the scan succeeded, as a failed
        alert-check submission fails a metrics job: the retry rescans, which is
        idempotent, and chains again.
        """
        config = job_spec.discovery_source_config
        if config is None:  # pragma: no cover -- checked before the scan ran
            raise ValueError("Cannot chain a fetch for a job with no source config.")
        if self.jobs_client is None:
            raise RuntimeError(
                "No jobs client is configured, so this scan cannot chain the fetch that "
                "surfaces its findings. The job runner supplies one.",
            )

        fetch_spec = FetchDiscoveredAgentsJobSpec(
            workspace_id=job_spec.workspace_id,
            data_plane_id=job_spec.data_plane_id,
            discovery_source_id=config.discovery_source_id,
            reported_since=scan_started_at - CHAINED_FETCH_SKEW,
        )
        spawned = self.jobs_client.post_submit_jobs_batch(
            project_id=str(job.project_id),
            post_job_batch=PostJobBatch(
                jobs=[
                    PostJob(
                        kind=PostJobKind.FETCH_DISCOVERED_AGENTS,
                        job_spec=PostJobSpec(fetch_spec),
                    ),
                ],
            ),
        )
        self.logger.info(
            f"Chained fetch job {spawned.jobs[0].id if spawned.jobs else None} for "
            f"discovery source {config.discovery_source_id}",
            extra={"discovery_source_id": str(config.discovery_source_id)},
        )

    def _chain_fetch_after_failed_scan(
        self,
        job: Job,
        job_spec: DiscoverAgentsJobSpec,
        scan_started_at: datetime,
    ) -> None:
        """Chain the fetch for a scan that is already failing, without masking why.

        The scan's own error is what the job reports, so a chaining failure on top of
        it is logged rather than raised; the standalone fetch picks the records up.
        """
        try:
            self._chain_fetch(job, job_spec, scan_started_at)
        except Exception as e:
            self.logger.error(
                f"Could not chain a fetch after the failed scan; its published records "
                f"surface at the next standalone fetch instead: {e}",
                exc_info=True,
            )

    def _source_credentials(
        self,
        outcome: DiscoveryScanOutcome,
    ) -> dict[str, Optional[str]]:
        """Read this config's sensitive fields, once, at the point of the scan.

        Deliberately not carried in the job spec -- the route says as much -- so it is
        fetched here rather than dispatched with the job. The values serve twice: the
        scanner authenticates with them, and they are registered with the job's logger,
        which removes them by exact match from everything it ships -- the message, the
        traceback and the job error alike. Exact removal is the only form of redaction
        that does not depend on guessing how a vendor SDK formats its errors.
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
        except Exception as e:
            # Reported without a scrub set: nothing was returned, so there is no
            # credential to take back out, and the failure names only the config.
            self._fail_before_scan(outcome, e)

        register_secrets(self.logger, secret_values(credentials))
        return credentials

    def _source_fields(
        self,
        config: DiscoverySourceConfigSpec,
        outcome: DiscoveryScanOutcome,
    ) -> dict[str, str]:
        """The source's non-sensitive configuration: where to connect, not how to auth.

        `retrieve_discovery_source_credentials` returns sensitive fields only, so without
        this a vendor's endpoint URL has no route to its scanner and a source has to
        declare it as a secret to work at all -- which then scrubs it from the logs that
        exist to say which host failed.

        Read from the job: the Platform snapshots them with the config at dispatch,
        because reading the source takes an organization-level role and the engine's
        account is bound to its workspace. The source read below serves only jobs
        dispatched before the Platform snapshotted them.

        A failure here is reported like any other pre-scan failure rather than degrading
        to an empty mapping: a scanner given no address would fail further away, naming a
        missing field instead of the fetch that could not answer.
        """
        if config.source_fields is not None:
            return dict(config.source_fields)

        if self.discovery_sources_client is None:
            self._fail_before_scan(
                outcome,
                RuntimeError(
                    "No discovery sources client is configured; source fields cannot "
                    "be read.",
                ),
            )
        try:
            source = self.discovery_sources_client.get_discovery_source(
                str(outcome.discovery_source_id),
            )
        except Exception as e:
            self._fail_before_scan(outcome, e)
        return {f.key: f.value for f in (source.fields or [])}

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
            lookback_hours=job_spec.lookback_hours,
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
    def _lookback_hours(job_spec: DiscoverAgentsJobSpec) -> int:
        """The window to scan, in whole hours, exactly as D-06 dispatched it.

        D-06 rounds the config's window up into `lookback_hours`, and that is the only
        window read here -- the config's own `lookback_window_seconds` is never
        consulted, so the window that ran is always the one the Platform recorded. The
        wire format cannot deliver a null (the binding substitutes its 720-hour default
        for a missing or null field), so the check below guards only a spec built in
        Python, and fails the job rather than guessing a window.
        """
        if job_spec.lookback_hours is None:
            raise ValueError("Discovery scan job carries no lookback_hours.")
        return int(job_spec.lookback_hours)

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

        num_upserted = publish_enriched_tasks(
            self.agents_client,
            self.logger,
            workspace_id,
            data_plane_id,
            enriched_tasks,
        )

        self.logger.info(
            f"Published {num_upserted} agent(s) to Agents API",
            extra={"workspace_id": workspace_id, "num_upserted": num_upserted},
        )
