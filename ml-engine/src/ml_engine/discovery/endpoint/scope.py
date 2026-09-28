"""Which managed devices a scan may use, by the MDM's own device groups.

True of any MDM: Jamf has smart and static computer groups, Intune has device groups,
and each can say which groups a device is in. What is vendor-specific -- listing the
tenant's groups so a name can be resolved -- stays in the vendor's package, which hands
this the list.

EXCLUDE WINS. A device in an included group and an excluded one is out. Exclusion is how
policy keeps a class of machine out of scope ("Executive devices"), and an executive's
Mac that is also in "Engineering" is still an executive's.

A NAME THAT DOES NOT RESOLVE FAILS THE SCAN. Group names are unique within an MDM but
can be renamed. An exclude group that silently matched nothing would scan exactly the
Macs policy said not to, and an include group that matched nothing would publish an
empty fleet that reads as clean. Both are configuration faults someone has to see.

AN OUT-OF-SCOPE DEVICE IS DROPPED BEFORE ITS PAYLOAD IS DECODED. Jamf returns a device's
group memberships in the same inventory page as its payload, so the engine does receive
it; nothing from that device is decoded, logged or published. Keeping it from ever
arriving would mean resolving every group's membership up front and filtering on device
ids, which costs a membership call per group and a filter that grows with the fleet.
"""

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence

from discovery.endpoint.device import ManagedDevice
from job_executors.discovery_scan import DeviceCoverage


class DeviceGroupError(ValueError):
    """A configured device group cannot be resolved to exactly one group in the MDM."""


@dataclass(frozen=True)
class DeviceGroup:
    """One of the MDM's device groups, by its own id."""

    id: str
    name: str


def parse_group_names(value: Optional[str]) -> tuple[str, ...]:
    """Group names from a comma-separated source field, trimmed and de-duplicated.

    A name that itself contains a comma cannot be written here. It splits into fragments
    that resolve to no group, so the scan fails rather than quietly scoping to something
    else.
    """
    names = (part.strip() for part in (value or "").split(","))
    return tuple(dict.fromkeys(name for name in names if name))


@dataclass(frozen=True)
class DeviceScope:
    """The resolved include and exclude groups, as group id -> name."""

    include: Mapping[str, str]
    exclude: Mapping[str, str]

    @classmethod
    def everything(cls) -> "DeviceScope":
        """No groups configured: every device the MDM returns is in scope."""
        return cls(include={}, exclude={})

    @classmethod
    def resolve(
        cls,
        include_names: Sequence[str],
        exclude_names: Sequence[str],
        groups: Iterable[DeviceGroup],
    ) -> "DeviceScope":
        """Resolve configured names against the MDM's groups, or raise naming each fault.

        Matched exactly. A case-insensitive match would be friendlier until the day it
        picks the wrong one of two groups differing only in case, and an exclude rule is
        the wrong place to guess.
        """
        ids_by_name: dict[str, list[str]] = {}
        for group in groups:
            ids_by_name.setdefault(group.name, []).append(group.id)

        faults = []
        for name in dict.fromkeys((*include_names, *exclude_names)):
            ids = ids_by_name.get(name, [])
            if not ids:
                faults.append(f"{name!r} not found")
            elif len(ids) > 1:
                faults.append(f"{name!r} matches {len(ids)} groups")
        if faults:
            raise DeviceGroupError(
                "Device group scope cannot be applied: "
                + "; ".join(faults)
                + ". Names are matched exactly against the MDM's computer groups, so a "
                "group renamed in the MDM has to be renamed in the source too.",
            )

        return cls(
            include={ids_by_name[name][0]: name for name in include_names},
            exclude={ids_by_name[name][0]: name for name in exclude_names},
        )

    @property
    def is_restricted(self) -> bool:
        return bool(self.include or self.exclude)

    def new_coverage(self) -> DeviceCoverage:
        """A tally with every configured group present, so a rule that kept nothing out
        this run still shows as a zero rather than going missing from the report."""
        return DeviceCoverage(
            excluded_by_group={name: 0 for name in self.exclude.values()},
            included_by_group={name: 0 for name in self.include.values()},
        )

    def admit(self, device: ManagedDevice, coverage: DeviceCoverage) -> bool:
        """Whether the scan may use this device, tallied into `coverage` either way."""
        coverage.devices_read += 1

        excluded_by = [
            name for gid, name in self.exclude.items() if gid in device.group_ids
        ]
        if excluded_by:
            coverage.devices_excluded += 1
            for name in excluded_by:
                coverage.excluded_by_group[name] += 1
            return False

        if self.include:
            included_by = [
                name for gid, name in self.include.items() if gid in device.group_ids
            ]
            if not included_by:
                coverage.devices_outside_included_groups += 1
                return False
            for name in included_by:
                coverage.included_by_group[name] += 1

        coverage.devices_in_scope += 1
        return True

    def describe(self) -> str:
        """The scope in one phrase, for the line that opens a scan."""
        if not self.is_restricted:
            return "all devices"
        parts = []
        if self.include:
            parts.append("include " + ", ".join(self.include.values()))
        if self.exclude:
            parts.append("exclude " + ", ".join(self.exclude.values()))
        return "; ".join(parts)
