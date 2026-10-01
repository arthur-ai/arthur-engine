"""Discovery connectors, and the registry entry that makes them reachable.

Importing this package registers every connector it ships into `SOURCE_CONNECTORS`, the
registry `DiscoverAgentsExecutor` resolves a source's vendor against. A connector class is
itself the zero-argument factory that registry holds, so each run gets its own instance. Registration
lives here rather than in `job_executors/discovery_scan.py` so that adding a connector
touches only this package: that module owns the seam, not the list of things plugged into
it.

A vendor with no entry fails its own job with that reason, which is the right answer for
an unsupported source and is reported per job rather than per engine.

Adding an MDM is one more line here and one more package under `discovery.endpoint`;
adding a SIEM is the same under `discovery.siem`.
Everything the new MDM shares with Jamf -- the `arthur1.` frame, the six-column rows,
matching, the record shape -- is already neutral and is not touched.
"""

from discovery.endpoint.jamf.connector import VENDOR as JAMF_VENDOR
from discovery.endpoint.jamf.connector import JamfConnector
from discovery.siem.elastic_security.connector import VENDOR as ELASTIC_SECURITY_VENDOR
from discovery.siem.elastic_security.connector import ElasticSecurityConnector
from job_executors.discovery_scan import SOURCE_CONNECTORS

SOURCE_CONNECTORS[JAMF_VENDOR] = JamfConnector
SOURCE_CONNECTORS[ELASTIC_SECURITY_VENDOR] = ElasticSecurityConnector

__all__ = [
    "JamfConnector",
    "JAMF_VENDOR",
    "ElasticSecurityConnector",
    "ELASTIC_SECURITY_VENDOR",
]
