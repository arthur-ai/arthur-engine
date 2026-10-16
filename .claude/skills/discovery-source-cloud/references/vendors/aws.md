# AWS (Bedrock agents, Bedrock AgentCore)

- `address.instance` is the AWS account id; `address.scope` the region (for example `us-east-1`).
- `runs_on` is `RunsOn.AWS`.
- Instance roles are ambient credentials: opt-in through an engine env flag, never the default.
- Least privilege: read-only list and describe actions on the agent resources only.
