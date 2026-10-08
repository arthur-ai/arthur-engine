"""Elastic Security: one SIEM's query API, and nothing else.

What every SIEM shares -- checking a result's columns against the contract and turning
its rows into records -- lives one level up in `discovery.siem`. What is here is the
API key header, the ES|QL `_query` call, and reading how complete its answer is.
"""
