"""LiteLLM proxy: callers read from the proxy's own request log (spend logs).

What is LiteLLM's here: the admin routes a read-only key can call, how a request log
row names its caller, and which rows are not callers. The record shape is
`discovery.network.gateway_records`.
"""
