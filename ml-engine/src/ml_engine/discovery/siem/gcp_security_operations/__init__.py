"""Google Security Operations: one SIEM's query API, and nothing else.

What every SIEM shares -- checking a result's columns against the contract and turning
its rows into records -- lives one level up in `discovery.siem`, and loading a Google
service account key lives in `discovery.gcp_credentials`. What is here is the regional
host, the `dashboardQueries:execute` call that runs a YARA-L statistics query, turning
its columnar answer into rows, and reading how complete that answer is.
"""
