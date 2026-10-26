"""Amazon CloudWatch Logs: network log lines read from the source's log groups.

Any log group works -- Route 53 Resolver query logs and VPC Flow Logs are the two AWS
writes in a fixed shape and have presets -- because the line is read by the source's
extractor (`discovery.network.extractor`), not by anything here. What is here is paging
`FilterLogEvents` (`client`) and the scan that feeds its lines through the extractor
and the destination matcher (`connector`).
"""
