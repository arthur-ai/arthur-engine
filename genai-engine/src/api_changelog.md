The intention of this changelog is to document API changes as they happen to effectively communicate them to customers.

---

# 07/16/2025
- **BREAKING CHANGE** for **URL**: /v1/spans/query  api path removed without deprecation
- **CHANGE** for Component/Schema:  removed the schema 'QuerySpansResponse'
- **CHANGE** for Component/Schema:  removed the schema 'SpanResponse'
- **CHANGE** for **URL**: /api/v2/tasks  added the required property '/items/metrics' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/tasks  added the required property 'metrics' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/tasks/search  added the required property 'tasks/items/metrics' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}  added the required property 'metrics' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}/metrics  endpoint added
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}/metrics/{metric_id}  endpoint added
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}/metrics/{metric_id}  endpoint added
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}/rules/{rule_id}  added the required property 'metrics' to the response with the '200' status
- **CHANGE** for **URL**: /v1/span/{span_id}/metrics  endpoint added
- **CHANGE** for **URL**: /v1/traces/metrics/  endpoint added
- **CHANGE** for **URL**: /v1/traces/query  endpoint added

# 06/11/2025
- **CHANGE** for **URL**: /v1/spans/query  endpoint added
- **CHANGE** for **URL**: /v1/traces  endpoint added

# 03/25/2025
- **CHANGE** for **URL**: /api/v2/usage/tokens  added the required property '/items/count/eval_completion' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/usage/tokens  added the required property '/items/count/eval_prompt' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/usage/tokens  added the required property '/items/count/inference' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/usage/tokens  added the required property '/items/count/user_input' to the response with the '200' status
# 03/03/2025
- OSS version changelog started
