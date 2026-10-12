"""Splunk Enterprise: one SIEM's search API, and nothing else.

What every SIEM shares -- checking a result's columns against the contract and turning
its rows into records -- lives one level up in `discovery.siem`. What is here is
Splunk's token header, its search job lifecycle and its results paging.
"""
