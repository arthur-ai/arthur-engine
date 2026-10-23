"""EC2: a cloud source whose instances carry the endpoint collector's inventory.

Everything true of any carrier -- the `arthur1.` frame, the six-column rows, the scan-row
vocabulary, how a device's payload becomes records -- lives in `discovery.endpoint`, and
what every VM-carrying cloud does with a VM's values in `discovery.cloud.vm_inventory`.
What is here is listing a region's instances, reading their SSM custom inventory back
out of its parts, and EC2's shape of a machine: an instance id within an account and
region, and tags where an MDM has groups. Its records are cloud records, per
(software, instance).
"""
