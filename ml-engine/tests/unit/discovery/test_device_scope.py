"""Device-group scope: which managed devices a scan may use (UP-4991, D-19)."""

from typing import Optional

import pytest

from discovery.endpoint.device import ManagedDevice
from discovery.endpoint.scope import (
    DeviceGroup,
    DeviceGroupError,
    DeviceScope,
    parse_group_names,
)

GROUPS = [
    DeviceGroup(id="1", name="All Managed Clients"),
    DeviceGroup(id="7", name="Engineering"),
    DeviceGroup(id="8", name="Contractors"),
    DeviceGroup(id="9", name="Executives"),
]


def device(*group_ids: str, key: str = "m1") -> ManagedDevice:
    return ManagedDevice(device_key=key, group_ids=frozenset(group_ids))


def scope(include: tuple[str, ...] = (), exclude: tuple[str, ...] = ()) -> DeviceScope:
    return DeviceScope.resolve(include, exclude, GROUPS)


# --- the source field -------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, ()),
        ("", ()),
        (" , ,", ()),
        ("Engineering", ("Engineering",)),
        (" Contractors , Executives ", ("Contractors", "Executives")),
        ("Executives,Executives", ("Executives",)),
    ],
)
def test_group_names_are_split_trimmed_and_deduplicated(
    value: Optional[str],
    expected: tuple[str, ...],
) -> None:
    assert parse_group_names(value) == expected


# --- resolving names --------------------------------------------------------------


def test_a_name_that_matches_no_group_fails_rather_than_matching_nothing() -> None:
    """An exclude rule that silently matched nothing would scan exactly the Macs policy
    said to leave out."""
    with pytest.raises(DeviceGroupError, match="'Executive Devices' not found"):
        scope(exclude=("Executive Devices",))


def test_every_unresolved_name_is_named_at_once() -> None:
    with pytest.raises(DeviceGroupError) as err:
        scope(include=("Engneering",), exclude=("Contractor",))
    assert "'Engneering' not found" in str(err.value)
    assert "'Contractor' not found" in str(err.value)


def test_names_are_matched_exactly_not_case_insensitively() -> None:
    with pytest.raises(DeviceGroupError, match="'executives' not found"):
        scope(exclude=("executives",))


def test_a_name_the_mdm_holds_twice_is_refused_rather_than_guessed() -> None:
    doubled = [*GROUPS, DeviceGroup(id="99", name="Executives")]
    with pytest.raises(DeviceGroupError, match="'Executives' matches 2 groups"):
        DeviceScope.resolve((), ("Executives",), doubled)


def test_names_resolve_to_ids() -> None:
    resolved = scope(include=("Engineering",), exclude=("Contractors", "Executives"))
    assert resolved.include == {"7": "Engineering"}
    assert resolved.exclude == {"8": "Contractors", "9": "Executives"}


# --- admitting devices -------------------------------------------------------------


def test_with_no_groups_every_device_is_in_scope() -> None:
    everything = DeviceScope.everything()
    coverage = everything.new_coverage()
    assert not everything.is_restricted
    assert everything.admit(device(), coverage)
    assert everything.admit(device("8"), coverage)
    assert (coverage.devices_read, coverage.devices_in_scope) == (2, 2)


def test_exclude_wins_over_include() -> None:
    """An executive's Mac that is also in Engineering is still an executive's."""
    resolved = scope(include=("Engineering",), exclude=("Executives",))
    coverage = resolved.new_coverage()
    assert not resolved.admit(device("7", "9"), coverage)
    assert coverage.devices_excluded == 1
    assert coverage.included_by_group == {"Engineering": 0}


def test_include_groups_limit_the_scan_to_their_members() -> None:
    resolved = scope(include=("Engineering",))
    coverage = resolved.new_coverage()
    assert resolved.admit(device("1", "7"), coverage)
    assert not resolved.admit(device("1"), coverage)
    assert coverage.devices_outside_included_groups == 1
    assert coverage.included_by_group == {"Engineering": 1}


def test_a_device_in_two_excluded_groups_counts_toward_both_but_once_overall() -> None:
    resolved = scope(exclude=("Contractors", "Executives"))
    coverage = resolved.new_coverage()
    resolved.admit(device("8", "9"), coverage)
    assert coverage.devices_excluded == 1
    assert coverage.excluded_by_group == {"Contractors": 1, "Executives": 1}


def test_a_rule_that_kept_nothing_out_still_reports_a_zero() -> None:
    """Visibly excluded with counts means the zero is shown, not dropped."""
    resolved = scope(exclude=("Contractors", "Executives"))
    coverage = resolved.new_coverage()
    resolved.admit(device("8"), coverage)
    resolved.admit(device("1"), coverage)
    assert coverage.excluded_by_group == {"Contractors": 1, "Executives": 0}
    assert (coverage.devices_read, coverage.devices_in_scope) == (2, 1)


def test_the_scope_describes_itself_for_the_scan_log() -> None:
    assert DeviceScope.everything().describe() == "all devices"
    assert (
        scope(include=("Engineering",), exclude=("Contractors",)).describe()
        == "include Engineering; exclude Contractors"
    )
