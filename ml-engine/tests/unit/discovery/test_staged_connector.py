"""The A&G demo's staged connectors (UP-5124), against a small staged file."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import RunsOn

import discovery  # noqa: F401  (registers the connectors)
from discovery.staged.connector import (
    STAGED_RECORDS_ENV_VAR,
    StagedComputeEngineConnector,
    StagedFalconConnector,
    StagedSecOpsConnector,
)
from job_executors.discovery_scan import (
    SOURCE_CONNECTORS,
    DiscoveryConfigurationError,
)

LOG = logging.getLogger("staged-test")
GENERATED_AT = "2026-10-08T00:00:00+00:00"
ONE_OFF = "2026-10-14T04:31:00+00:00"


def record(vendor: str, kind: str, external_id: str, last_seen: str) -> dict[str, Any]:
    address: dict[str, Any] = {"instance": "7341905528816223401", "resource_id": "x"}
    if kind == "SIEM":
        address["scope"] = "GCP_DNS"
    return {
        "external_id": external_id,
        "name": "ClaimSoft Smart Triage",
        "last_seen": last_seen,
        "runs_on": "gcp",
        "platform": "linux",
        "creation_source": {
            "type": kind,
            "vendor": vendor,
            "address": address,
            "observations": {
                "host_name": "claimsoft-worker-01",
                "service_names": ["claimsoft-worker-01/claimsoft-smart-triage"],
            },
        },
    }


@pytest.fixture
def staged_file(tmp_path: Path) -> Path:
    path = tmp_path / "records.json"
    path.write_text(
        json.dumps(
            {
                "generated_at": GENERATED_AT,
                "records": {
                    "crowdstrike_falcon": [
                        record(
                            "crowdstrike_falcon", "ENDPOINT", "aid:cs", GENERATED_AT
                        ),
                    ],
                    "google_secops": [
                        record("google_secops", "SIEM", "vm:dns", GENERATED_AT),
                        record("google_secops", "SIEM", "bastion:dns", ONE_OFF),
                    ],
                    "gcp_compute_engine": [],
                },
            },
        ),
    )
    return path


def config(vendor: str) -> Any:
    return DiscoverySourceConfigSpec.model_construct(vendor=vendor)


def scan(connector: Any, vendor: str) -> list[Any]:
    return [
        r for batch in connector.scan(config(vendor), 24, {}, {}, LOG) for r in batch
    ]


def test_each_staged_vendor_is_registered() -> None:
    assert SOURCE_CONNECTORS["crowdstrike_falcon"] is StagedFalconConnector
    assert SOURCE_CONNECTORS["google_secops"] is StagedSecOpsConnector
    assert SOURCE_CONNECTORS["gcp_compute_engine"] is StagedComputeEngineConnector


def test_a_connector_returns_only_its_own_vendor(staged_file: Path) -> None:
    records = scan(StagedSecOpsConnector(staged_file), "google_secops")
    assert {r.creation_source.vendor for r in records} == {"google_secops"}
    assert {r.runs_on for r in records} == {RunsOn.GCP}
    assert scan(StagedComputeEngineConnector(staged_file), "gcp_compute_engine") == []


def test_current_records_are_restamped_and_one_off_sightings_kept(
    staged_file: Path,
) -> None:
    before = datetime.now(timezone.utc)
    records = {r.external_id: r for r in scan(StagedSecOpsConnector(staged_file), "")}
    assert records["vm:dns"].last_seen >= before
    assert records["bastion:dns"].last_seen == datetime.fromisoformat(ONE_OFF)


def test_the_three_sources_share_a_service_name(staged_file: Path) -> None:
    """What lands them on one task in GenAI Engine's resolver."""
    falcon = scan(StagedFalconConnector(staged_file), "")[0]
    secops = scan(StagedSecOpsConnector(staged_file), "")[0]
    assert set(falcon.service_names) & set(secops.service_names)


def test_an_engine_without_staged_records_says_how_to_fix_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(STAGED_RECORDS_ENV_VAR, raising=False)
    with pytest.raises(DiscoveryConfigurationError, match=STAGED_RECORDS_ENV_VAR):
        scan(StagedFalconConnector(), "crowdstrike_falcon")
