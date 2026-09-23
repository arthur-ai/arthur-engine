"""One managed device, in the shape every MDM can describe.

An MDM package's job is turning its own API's device record into one of these. Nothing
downstream sees Jamf's `managementId`, Intune's `azureADDeviceId` or Kandji's
`device_id`. A field only one vendor can fill belongs in that vendor's package, not here.
"""

from dataclasses import dataclass, field
from typing import Mapping, Optional


@dataclass(frozen=True)
class ManagedDevice:
    """A device as its MDM last saw it, plus the custom attributes it carries."""

    device_key: str
    """The MDM's own stable id.

    Never the hardware serial: VMs and refurbished units produce empty or duplicate
    serials, and an identity that churns mints a duplicate finding on every scan.
    """

    last_reported: Optional[str] = None
    """When the MDM last received inventory from this device.

    The freshness signal that belongs to the MDM rather than the payload, and the only
    thing that separates "reported, and collection is broken" from "has not reported at
    all" -- the second being invisible to a custom attribute by construction.
    """

    name: Optional[str] = None
    group: Optional[str] = None
    os_version: Optional[str] = None
    assigned_user: Optional[str] = None

    attributes: Mapping[str, Optional[str]] = field(default_factory=dict)
    """Custom attributes by display name, which is what an MDM admin sees."""

    def attribute(self, name: str) -> Optional[str]:
        return self.attributes.get(name)
