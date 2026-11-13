"""Wiz: Wiz's inventory of a customer's AI resources, read through its GraphQL API.

Vendor-specific here: the OAuth client-credentials token, the `cloudResourcesV2` and
`hostedTechnologies` queries and their cursors, and Wiz's GraphQL error codes, which
arrive in the body of an HTTP 200 as often as in a non-2xx status.
"""
