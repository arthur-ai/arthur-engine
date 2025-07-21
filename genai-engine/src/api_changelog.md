The intention of this changelog is to document API changes as they happen to effectively communicate them to customers.

---

# 07/21/2025
- **CHANGE** for **URL**: /api/v2/tasks  added task_type to the request, and response
- **CHANGE** for **URL**: /api/v2/tasks/search  added task_type as a search filter and part of the task response body
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}  added task_type to the response
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}/rules/{rule_id}  added task_type to the response

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
