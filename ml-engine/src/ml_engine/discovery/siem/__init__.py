"""SIEM discovery: agents inferred from a customer-authored query over their logs.

What every SIEM shares is that the customer's query, not Arthur, names the output
columns -- SPL's `table`/`rename`, ES|QL's `RENAME`/`KEEP`, KQL's `project`. So the
shared half is turning a result's columns and rows into records, which lives in
`discovery.siem.records`. Each vendor package holds only how its query is run and
paged. One package per vendor product.
"""
