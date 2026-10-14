# OpenShell

OpenShell is an agent runtime: a gateway in front of sandboxes, each running an agent.

## Enforcement surface (not built)

The vendor documents (`how-it-works/gateways`, `policies/manage-policies`) that the gateway is the control plane for its sandboxes: it delivers network and filesystem policy, can delete sandboxes, and a global policy (`openshell policy set --global`) replaces every sandbox's policy until it is removed. A discovery connector calls none of this.
