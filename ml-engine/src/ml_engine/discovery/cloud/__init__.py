"""Cloud discovery: agents found through a cloud provider's list API.

Two kinds of package, one per provider product. An agent runtime's (`gcp_vertex`) lists
the agents themselves; each provider's list API is its own, so there is no shared
payload format to factor out, and what it shares with the others is only the record
shape, `CloudAgentCreationSource`, which arthur_common already owns. A VM product's
(`gce`) lists machines that carry the endpoint collector's `arthur1.` payload, so it
reuses `discovery.endpoint`'s decoding and matching and names the cloud record type
when it builds its records.
"""
