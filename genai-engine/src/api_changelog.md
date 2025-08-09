The intention of this changelog is to document API changes as they happen to effectively communicate them to customers.

---
# 08/09/2025
Made `bert_f_score` and `reranker_relevance_score` optional.

# 08/08/2025
- **CHANGE**: Made `is_agentic` optional

# 08/04/2025
- **CHANGE**: Forces toxicity threshold to float

# 07/23/2025
- **CHANGE** for **URL**: /v1/spans/{span_id}/metrics/ now returns the span object itself instead of a list of Span objects of len 1
- **CHANGE** for **URL**: /v1/traces/metrics/ and /v1/traces/query updated to return a nested traces object instead of a flat list of spans
# 07/22/2025
- **CHANGE** for **URL**: /api/v2/tasks Added optional metrics to the task response
- **CHANGE** for **URL**: /api/v2/tasks/search  Added optional metrics to the task response
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}  Added optional metrics to the task response
- **CHANGE** for **URL**: Added new endpoints for metrics management /api/v2/tasks/{task_id}/metrics and /api/v2/tasks/{task_id}/metrics/{metric_id}
- **CHANGE** for **URL**: Added new metrics compute endpoints. Span Level: `/v1/span/{span_id}/metrics` and trace level `/v1/traces/metrics/`
- **CHANGE** for **URL**: Added new trace query endpoint `/v1/traces/query`
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}/rules/{rule_id}  added optional metrics to the task response
# 07/21/2025
- **CHANGE** for **URL**: /api/v2/tasks  added is_agentic to the request, and response
- **CHANGE** for **URL**: /api/v2/tasks/search  added is_agentic as a search filter and part of the task response body
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}  added is_agentic to the response
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}/rules/{rule_id}  added is_agentic to the response

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
