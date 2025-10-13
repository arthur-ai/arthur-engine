The intention of this changelog is to document API changes as they happen to effectively communicate them to customers.

---

# 10/10/2025
- **CHANGE** for **URL**: /api/v2/datasets/search  endpoint added

# 10/09/2025
- **CHANGE** for **URL**: /api/v2/datasets  endpoint added
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}  endpoint added
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}  endpoint added
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}  endpoint added
- **CHANGE** for **URL**: /v1/span/{span_id}/metrics  added the optional property 'session_id' to the response with the '200' status
- **CHANGE** for **URL**: /v1/span/{span_id}/metrics  added the required property 'status_code' to the response with the '200' status
- **CHANGE** for **URL**: /v1/spans/query  added the optional property 'spans/items/session_id' to the response with the '200' status
- **CHANGE** for **URL**: /v1/spans/query  added the required property 'spans/items/status_code' to the response with the '200' status
- **CHANGE** for **URL**: /v1/traces/metrics/  added the optional property 'traces/items/root_spans/items/session_id' to the response with the '200' status
- **CHANGE** for **URL**: /v1/traces/metrics/  added the required property 'traces/items/root_spans/items/status_code' to the response with the '200' status
- **CHANGE** for **URL**: /v1/traces/query  added the optional property 'traces/items/root_spans/items/session_id' to the response with the '200' status
- **CHANGE** for **URL**: /v1/traces/query  added the required property 'traces/items/root_spans/items/status_code' to the response with the '200' status

# 10/07/2025
- **CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/delete_prompt/{prompt_name}  endpoint added
- **CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/get_all_prompts  endpoint added
- **CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/get_prompt/{prompt_name}  endpoint added
- **CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/run_prompt  endpoint added
- **CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/run_prompt/{prompt_name}  endpoint added
- **CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/save_prompt  endpoint added
- **CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/update_prompt  endpoint added

# 09/10/2025
- v1/traces/metrics and v1/traces/query added new optional request parameters: 'query_relevance_eq', 'query_relevance_gt', 'query_relevance_gte', 'query_relevance_lt', 'query_relevance_lte', 'response_relevance_eq', 'response_relevance_gt', 'response_relevance_gte', 'response_relevance_lt', 'response_relevance_lte', 'tool_name', 'tool_selection', 'tool_usage', 'trace_duration_eq', 'trace_duration_gt', 'trace_duration_gte', 'trace_duration_lt', 'trace_duration_lte', 'trace_ids', 'span_kind'

# 09/05/2025
- Added span_name to spans response

# 08/27/2025
- **CHANGE** for **URL**: /v1/spans/query  endpoint added

# 08/25/2025
- **BREAKING CHANGE** for **URL**: /api/chat/conversations  the 'page' response's property type/format changed from ''/'' to 'integer'/'' for status '200'
- **BREAKING CHANGE** for **URL**: /api/chat/conversations  the 'pages' response's property type/format changed from ''/'' to 'integer'/'' for status '200'
- **BREAKING CHANGE** for **URL**: /api/chat/conversations  the 'size' response's property type/format changed from ''/'' to 'integer'/'' for status '200'
- **BREAKING CHANGE** for **URL**: /api/chat/conversations  the 'total' response's property type/format changed from ''/'' to 'integer'/'' for status '200'
- **CHANGE** for **URL**: /api/chat/conversations  removed 'subschema #1, subschema #2' from the 'page' response property 'anyOf' list for the response status '200'
- **CHANGE** for **URL**: /api/chat/conversations  removed 'subschema #1, subschema #2' from the 'pages' response property 'anyOf' list for the response status '200'
- **CHANGE** for **URL**: /api/chat/conversations  removed 'subschema #1, subschema #2' from the 'size' response property 'anyOf' list for the response status '200'
- **CHANGE** for **URL**: /api/chat/conversations  removed 'subschema #1, subschema #2' from the 'total' response property 'anyOf' list for the response status '200'
- **CHANGE** for **URL**: /api/chat/conversations  the response property 'pages' became required for the status '200'
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
