"""Discovery connectors, and the one list of them.

`source_connectors()` is the vendor -> connector map that `DiscoverAgentsExecutor` and
`DiscoverySourceTestExecutor` build when they are initialized, and that a standalone
engine checks its config file's sources against. A connector class is itself the
zero-argument factory that map holds, so each run gets its own instance. The list lives
here rather than in `job_executors/discovery_scan.py` so that adding a connector touches
only this package: that module owns the seam, not the list of things plugged into it.

A connector class also declares `SENSITIVE_FIELDS`, the keys among its source's fields
that are credentials. A Platform job never needs it -- the Platform splits a source's
fields before they arrive -- but a standalone engine reads them as one list from its
config file, and a connector that does not say which are secret cannot be run there.

A vendor with no entry fails its own job with that reason, which is the right answer for
an unsupported source and is reported per job rather than per engine.

Adding an MDM is one more entry here and one more package under `discovery.endpoint`;
adding a SIEM is the same under `discovery.siem`, a cloud provider product under
`discovery.cloud`, and a network log source under `discovery.network`. A package goes
where its vendor's source class is, which is also the record type it emits.
Everything the new MDM shares with Jamf -- the `arthur1.` frame, the six-column rows,
matching, the record shape -- is already neutral and is not touched. A cloud product
whose VMs carry that payload (Compute Engine, EC2) reuses it too, from `discovery.cloud`,
with what such clouds share among themselves in `discovery.cloud.vm_inventory`.
"""

from discovery.cloud.aws_bedrock.connector import VENDOR as AWS_BEDROCK_VENDOR
from discovery.cloud.aws_bedrock.connector import BedrockConnector
from discovery.cloud.aws_containers.connector import VENDOR as AWS_CONTAINERS_VENDOR
from discovery.cloud.aws_containers.connector import AwsContainersConnector
from discovery.cloud.ec2.connector import VENDOR as AWS_EC2_VENDOR
from discovery.cloud.ec2.connector import Ec2Connector
from discovery.cloud.gce.connector import VENDOR as GCP_COMPUTE_ENGINE_VENDOR
from discovery.cloud.gce.connector import ComputeEngineConnector
from discovery.cloud.gcp_containers.connector import VENDOR as GCP_CONTAINERS_VENDOR
from discovery.cloud.gcp_containers.connector import GcpContainersConnector
from discovery.cloud.gcp_vertex.connector import VENDOR as GCP_VERTEX_VENDOR
from discovery.cloud.gcp_vertex.connector import VertexAgentEngineConnector
from discovery.cloud.wiz.connector import VENDOR as WIZ_VENDOR
from discovery.cloud.wiz.connector import WizConnector
from discovery.endpoint.jamf.connector import VENDOR as JAMF_VENDOR
from discovery.endpoint.jamf.connector import JamfConnector
from discovery.network.cloudwatch_logs.connector import VENDOR as CLOUDWATCH_LOGS_VENDOR
from discovery.network.cloudwatch_logs.connector import CloudWatchLogsConnector
from discovery.network.gcp_logging.connector import VENDOR as GCP_NETWORK_VENDOR
from discovery.network.gcp_logging.connector import GcpNetworkConnector
from discovery.siem.elastic_security.connector import VENDOR as ELASTIC_SECURITY_VENDOR
from discovery.siem.elastic_security.connector import ElasticSecurityConnector
from discovery.siem.splunk.connector import VENDOR as SPLUNK_VENDOR
from discovery.siem.splunk.connector import SplunkConnector
from job_executors.discovery_scan import DiscoveryConnectorFactory


def source_connectors() -> dict[str, DiscoveryConnectorFactory]:
    """Vendor -> connector factory, keyed on DiscoverySourceVendor values.

    A new dict on every call, so a caller that changes its own -- a test swapping in a
    fake -- cannot change what any other executor resolves a vendor against.
    """
    return {
        JAMF_VENDOR: JamfConnector,
        GCP_COMPUTE_ENGINE_VENDOR: ComputeEngineConnector,
        AWS_EC2_VENDOR: Ec2Connector,
        AWS_BEDROCK_VENDOR: BedrockConnector,
        AWS_CONTAINERS_VENDOR: AwsContainersConnector,
        GCP_VERTEX_VENDOR: VertexAgentEngineConnector,
        GCP_CONTAINERS_VENDOR: GcpContainersConnector,
        WIZ_VENDOR: WizConnector,
        SPLUNK_VENDOR: SplunkConnector,
        ELASTIC_SECURITY_VENDOR: ElasticSecurityConnector,
        CLOUDWATCH_LOGS_VENDOR: CloudWatchLogsConnector,
        GCP_NETWORK_VENDOR: GcpNetworkConnector,
    }


__all__ = [
    "source_connectors",
    "JamfConnector",
    "JAMF_VENDOR",
    "ComputeEngineConnector",
    "GCP_COMPUTE_ENGINE_VENDOR",
    "Ec2Connector",
    "AWS_EC2_VENDOR",
    "BedrockConnector",
    "AWS_BEDROCK_VENDOR",
    "AwsContainersConnector",
    "AWS_CONTAINERS_VENDOR",
    "VertexAgentEngineConnector",
    "GCP_VERTEX_VENDOR",
    "GcpContainersConnector",
    "GCP_CONTAINERS_VENDOR",
    "WizConnector",
    "WIZ_VENDOR",
    "SplunkConnector",
    "SPLUNK_VENDOR",
    "ElasticSecurityConnector",
    "ELASTIC_SECURITY_VENDOR",
    "CloudWatchLogsConnector",
    "CLOUDWATCH_LOGS_VENDOR",
    "GcpNetworkConnector",
    "GCP_NETWORK_VENDOR",
]
