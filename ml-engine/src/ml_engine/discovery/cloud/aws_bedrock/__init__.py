"""AWS Bedrock: a cloud source that lists agents and reads who calls models.

Two readings of one account, per region: the agents Bedrock and Bedrock AgentCore list
(an inventory), and the IAM roles CloudTrail saw calling Bedrock's model APIs (a log).
Both are cloud records, addressed by account and region.
"""
