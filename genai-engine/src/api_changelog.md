The intention of this changelog is to document API changes as they happen to effectively communicate them to customers.

---

# 11/03/2025
- **CHANGE** for **URL**: /api/v1/rag_provider_settings/{setting_configuration_id}  endpoint added
- **CHANGE** for **URL**: /api/v1/rag_provider_settings/{setting_configuration_id}  endpoint added
- **CHANGE** for **URL**: /api/v1/rag_providers/{provider_id}/hybrid_search  added the new optional request property 'settings/search_kind'
- **CHANGE** for **URL**: /api/v1/rag_providers/{provider_id}/keyword_search  added the new optional request property 'settings/search_kind'
- **CHANGE** for **URL**: /api/v1/rag_providers/{provider_id}/similarity_text_search  added the new optional request property 'settings/search_kind'
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/rag_provider_settings  endpoint added

# 10/31/2025
- **CHANGE** for **URL**: /api/v1/rag_providers/{provider_id}/hybrid_search  endpoint added

# 10/31/2025
- **CHANGE** for **URL**: /api/v2/inferences/query  removed the optional property 'inferences/items/inference_prompt/model_name' from the response with the '200' status
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}/validate_prompt  removed the request property 'model_name'
- **CHANGE** for **URL**: /api/v2/validate_prompt  removed the request property 'model_name'
- **CHANGE** for Component/Schema:  removed the schema 'RagVectorKeywordSearchSettingRequest'

# 10/30/2025
- **CHANGE** for Component/Schema:  removed the schema 'RagProviderSimilarityTextSearchResponse'
- **CHANGE** for Component/Schema:  removed the schema 'WeaviateSimilaritySearchMetadata'
- **CHANGE** for Component/Schema:  removed the schema 'WeaviateSimilaritySearchTextResult'
- **CHANGE** for Component/Schema:  removed the schema 'WeaviateSimilarityTextSearchResponse'
- **CHANGE** for **URL**: /api/v1/rag_providers/{provider_id}/keyword_search  endpoint added
- **CHANGE** for **URL**: /api/v1/rag_providers/{provider_id}/similarity_text_search  added '#/components/schemas/WeaviateQueryResultMetadata' to the 'response/objects/items/metadata' response property 'anyOf' list for the response status '200'
- **CHANGE** for **URL**: /api/v1/rag_providers/{provider_id}/similarity_text_search  removed '#/components/schemas/WeaviateSimilaritySearchMetadata' from the 'response/objects/items/metadata' response property 'anyOf' list for the response status '200'
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/prompts/{prompt_name}  added the new 'developer' enum value to the 'messages/items/role' response property for the response status '200'
- **CHANGE** in API GET /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}
- **CHANGE** for **URL**: /api/v1/rag_providers/{provider_id}/collections  endpoint added


# 10/30/2025
- **CHANGE** for **URL**: /api/v1/rag_providers/{provider_id}/similarity_text_search  endpoint added
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/rag_providers/test_connection  endpoint added

# 10/30/2025
- **CHANGE** for **URL**: /api/v1/rag_providers/{provider_id}  endpoint added
- **CHANGE** for **URL**: /api/v1/rag_providers/{provider_id}  endpoint added
- **CHANGE** for **URL**: /api/v1/rag_providers/{provider_id}  endpoint added
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/rag_providers  endpoint added
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/rag_providers  endpoint added

# 10/28/2025
- **CHANGE** for **URL**: /api/v2/inferences/query  added the optional property 'inferences/items/inference_prompt/model_name' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/tasks/{task_id}/validate_prompt  added the new optional request property 'model_name'
- **CHANGE** for **URL**: /api/v2/validate_prompt  added the new optional request property 'model_name'

# 10/23/2025
- **CHANGE** for **URL**: /api/v1/completions  added the new optional request property 'completion_request/strict'
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/completions  added the new optional request property 'strict'

# 10/22/2025
- **BREAKING CHANGE** for **URL**: /api/v1/task/{task_id}/prompt/{prompt_name}/versions/{prompt_version}/completions  api path removed without deprecation
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  api path removed without deprecation
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  api path removed without deprecation
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  api path removed without deprecation
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  api path removed without deprecation
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  api path removed without deprecation
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  api path removed without deprecation
- **CHANGE** for **URL**: /api/v1/completions  api tag 'Prompts' added
- **CHANGE** for **URL**: /api/v1/completions  api tag 'AgenticPrompt' removed
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/prompts  endpoint added
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/prompts/{prompt_name}  endpoint added
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/prompts/{prompt_name}  endpoint added
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions  endpoint added
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}  endpoint added
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}  endpoint added
- **CHANGE** for **URL**: /api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/completions  endpoint added

# 10/22/2025
- **CHANGE** for **URL**: /api/v1/traces  added the new optional 'query' request parameter 'user_ids'
- **CHANGE** for **URL**: /api/v1/traces  added the optional property 'traces/items/user_id' to the response with the '200' status
- **CHANGE** for **URL**: /api/v1/traces/sessions  added the new optional 'query' request parameter 'user_ids'
- **CHANGE** for **URL**: /api/v1/traces/sessions  added the optional property 'sessions/items/user_id' to the response with the '200' status
- **CHANGE** for **URL**: /api/v1/traces/spans  added the optional property 'spans/items/user_id' to the response with the '200' status
- **CHANGE** for **URL**: /api/v1/traces/sessions  endpoint added
- **CHANGE** for **URL**: /api/v1/traces/sessions/{session_id}  endpoint added
- **CHANGE** for **URL**: /api/v1/traces/sessions/{session_id}/metrics  endpoint added
- **CHANGE** for **URL**: /api/v1/traces/spans  endpoint added
- **CHANGE** for **URL**: /api/v1/traces/spans/{span_id}  endpoint added
- **CHANGE** for **URL**: /api/v1/traces/spans/{span_id}/metrics  endpoint added
- **CHANGE** for **URL**: /api/v1/traces/users  endpoint added
- **CHANGE** for **URL**: /api/v1/traces/users/{user_id}  endpoint added

# 10/21/2025
- **CHANGE** for **URL**: /api/v1/model_providers/{provider}/available_models  endpoint added

# 10/20/2025
- **CHANGE** for **URL**: /api/v1/users  endpoint added
- **CHANGE** for **URL**: /api/v1/users/{user_id}/sessions  endpoint added
- **CHANGE** for **URL**: /api/v1/users/{user_id}/traces  endpoint added

# 10/21/2025
- **CHANGE** for **URL**: /api/v1/model_providers/{provider}/available_models  endpoint added

# 10/20/2025
- **CHANGE** for **URL**: /api/v2/datasets  added the optional property 'latest_version_number' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/datasets/search  added the optional property 'datasets/items/latest_version_number' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}  added the optional property 'latest_version_number' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}  added the optional property 'latest_version_number' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}/versions  added the required property 'rows/items/created_at' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}/versions/{version_number}  added the required property 'rows/items/created_at' to the response with the '200' status

# 10/20/2025
- **BREAKING CHANGE** for **URL**: /api/v1/model_providers/{provider}  the 'api_key' request property type/format changed from 'string'/'' to 'string'/'password'
- **CHANGE** for **URL**: /api/v1/model_providers/{provider}  the request required property 'api_key' became write-only

# 10/20/2025
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'azure' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'bedrock' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'sagemaker' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'vertex_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'azure' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'bedrock' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'sagemaker' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'vertex_ai' of the request property 'model_provider'
- **CHANGE** for **URL**: /api/v1/model_providers  endpoint added
- **CHANGE** for **URL**: /api/v1/model_providers/{provider}  endpoint added
- **CHANGE** for **URL**: /api/v1/model_providers/{provider}  endpoint added
- **CHANGE** for **URL**: /api/v1/secrets/rotation  endpoint added
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'azure' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'bedrock' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'sagemaker' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'vertex_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'azure' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'bedrock' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'sagemaker' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'vertex_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'azure' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'bedrock' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'sagemaker' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'vertex_ai' enum value from the 'model_provider' response property for the response status '200'

# 10/20/2025
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'azure' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'bedrock' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'sagemaker' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'vertex_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'azure' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'bedrock' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'sagemaker' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'vertex_ai' of the request property 'model_provider'
- **CHANGE** for **URL**: /api/v1/model_providers  endpoint added
- **CHANGE** for **URL**: /api/v1/model_providers/{provider}  endpoint added
- **CHANGE** for **URL**: /api/v1/model_providers/{provider}  endpoint added
- **CHANGE** for **URL**: /api/v1/secrets/rotation  endpoint added
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'azure' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'bedrock' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'sagemaker' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'vertex_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'azure' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'bedrock' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'sagemaker' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'vertex_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'azure' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'bedrock' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'sagemaker' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'vertex_ai' enum value from the 'model_provider' response property for the response status '200'

# 10/20/2025
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  added the optional property 'prompts/items/created_at' to the response with the '200' status
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  added the optional property 'prompts/items/created_at' to the response with the '200' status
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  added the optional property 'created_at' to the response with the '200' status

# 10/17/2025
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'ai21' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'baseten' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'cloudflare' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'cohere' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'deepseek' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'empower' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'featherless_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'friendliai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'galadriel' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'groq' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'huggingface' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'meta_llama' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'mistral' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'nebius' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'nlp_cloud' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'novita' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'openrouter' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'petals' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'replicate' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'together_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'vllm' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'watsonx' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'ai21' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'baseten' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'cloudflare' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'cohere' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'deepseek' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'empower' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'featherless_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'friendliai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'galadriel' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'groq' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'huggingface' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'meta_llama' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'mistral' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'nebius' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'nlp_cloud' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'novita' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'openrouter' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'petals' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'replicate' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'together_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'vllm' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'watsonx' of the request property 'model_provider'
- **CHANGE** for Component/Schema:  removed the schema 'ProviderEnum'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'ai21' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'baseten' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'cloudflare' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'cohere' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'deepseek' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'empower' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'featherless_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'friendliai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'galadriel' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'groq' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'huggingface' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'meta_llama' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'mistral' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'nebius' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'nlp_cloud' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'novita' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'openrouter' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'petals' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'replicate' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'together_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'vllm' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'watsonx' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'ai21' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'baseten' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'cloudflare' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'cohere' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'deepseek' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'empower' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'featherless_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'friendliai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'galadriel' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'groq' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'huggingface' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'meta_llama' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'mistral' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'nebius' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'nlp_cloud' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'novita' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'openrouter' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'petals' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'replicate' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'together_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'vllm' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'watsonx' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'ai21' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'baseten' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'cloudflare' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'cohere' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'deepseek' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'empower' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'featherless_ai' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'friendliai' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'galadriel' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'groq' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'huggingface' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'meta_llama' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'mistral' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'nebius' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'nlp_cloud' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'novita' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'openrouter' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'petals' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'replicate' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'together_ai' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'vllm' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'watsonx' enum value from the 'model_provider' response property for the response status '200'

# 10/17/2025
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'ai21' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'baseten' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'cloudflare' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'cohere' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'deepseek' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'empower' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'featherless_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'friendliai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'galadriel' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'groq' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'huggingface' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'meta_llama' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'mistral' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'nebius' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'nlp_cloud' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'novita' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'openrouter' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'petals' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'replicate' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'together_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'vllm' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'watsonx' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'ai21' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'baseten' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'cloudflare' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'cohere' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'deepseek' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'empower' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'featherless_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'friendliai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'galadriel' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'groq' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'huggingface' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'meta_llama' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'mistral' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'nebius' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'nlp_cloud' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'novita' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'openrouter' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'petals' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'replicate' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'together_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'vllm' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'watsonx' of the request property 'model_provider'
- **CHANGE** for Component/Schema:  removed the schema 'ProviderEnum'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'ai21' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'baseten' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'cloudflare' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'cohere' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'deepseek' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'empower' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'featherless_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'friendliai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'galadriel' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'groq' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'huggingface' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'meta_llama' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'mistral' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'nebius' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'nlp_cloud' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'novita' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'openrouter' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'petals' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'replicate' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'together_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'vllm' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'watsonx' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'ai21' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'baseten' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'cloudflare' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'cohere' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'deepseek' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'empower' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'featherless_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'friendliai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'galadriel' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'groq' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'huggingface' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'meta_llama' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'mistral' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'nebius' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'nlp_cloud' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'novita' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'openrouter' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'petals' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'replicate' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'together_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'vllm' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'watsonx' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'ai21' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'baseten' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'cloudflare' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'cohere' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'deepseek' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'empower' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'featherless_ai' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'friendliai' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'galadriel' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'groq' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'huggingface' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'meta_llama' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'mistral' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'nebius' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'nlp_cloud' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'novita' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'openrouter' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'petals' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'replicate' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'together_ai' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'vllm' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'watsonx' enum value from the 'model_provider' response property for the response status '200'

# 10/17/2025
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'ai21' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'baseten' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'cloudflare' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'cohere' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'deepseek' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'empower' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'featherless_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'friendliai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'galadriel' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'groq' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'huggingface' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'meta_llama' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'mistral' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'nebius' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'nlp_cloud' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'novita' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'openrouter' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'petals' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'replicate' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'together_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'vllm' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/completions  removed the enum value 'watsonx' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'ai21' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'baseten' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'cloudflare' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'cohere' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'deepseek' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'empower' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'featherless_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'friendliai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'galadriel' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'groq' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'huggingface' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'meta_llama' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'mistral' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'nebius' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'nlp_cloud' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'novita' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'openrouter' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'petals' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'replicate' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'together_ai' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'vllm' of the request property 'model_provider'
- **BREAKING CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  removed the enum value 'watsonx' of the request property 'model_provider'
- **CHANGE** for Component/Schema:  removed the schema 'ProviderEnum'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'ai21' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'baseten' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'cloudflare' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'cohere' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'deepseek' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'empower' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'featherless_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'friendliai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'galadriel' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'groq' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'huggingface' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'meta_llama' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'mistral' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'nebius' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'nlp_cloud' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'novita' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'openrouter' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'petals' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'replicate' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'together_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'vllm' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  removed the 'watsonx' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'ai21' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'baseten' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'cloudflare' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'cohere' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'deepseek' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'empower' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'featherless_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'friendliai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'galadriel' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'groq' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'huggingface' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'meta_llama' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'mistral' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'nebius' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'nlp_cloud' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'novita' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'openrouter' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'petals' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'replicate' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'together_ai' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'vllm' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  removed the 'watsonx' enum value from the 'prompts/items/model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'ai21' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'baseten' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'cloudflare' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'cohere' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'deepseek' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'empower' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'featherless_ai' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'friendliai' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'galadriel' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'groq' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'huggingface' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'meta_llama' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'mistral' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'nebius' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'nlp_cloud' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'novita' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'openrouter' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'petals' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'replicate' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'together_ai' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'vllm' enum value from the 'model_provider' response property for the response status '200'
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  removed the 'watsonx' enum value from the 'model_provider' response property for the response status '200'

# 10/17/2025
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}/versions  added the required property 'versions/items/column_names' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}/versions  added the required property 'column_names' to the response with the '200' status
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}/versions/{version_number}  added the required property 'column_names' to the response with the '200' status

# 10/16/2025
- **CHANGE** for **URL**: /api/v2/datasets  endpoint added
- **CHANGE** for **URL**: /api/v2/datasets/search  endpoint added
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}  endpoint added
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}  endpoint added
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}  endpoint added
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}/versions  endpoint added
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}/versions  endpoint added
- **CHANGE** for **URL**: /api/v2/datasets/{dataset_id}/versions/{version_number}  endpoint added


# 10/14/2025
- **CHANGE** for **URL**: /api/v1/completions  endpoint added
- **CHANGE** for **URL**: /api/v1/task/{task_id}/prompt/{prompt_name}/versions/{prompt_version}/completions  endpoint added
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts  endpoint added
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  endpoint added
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}  endpoint added
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions  endpoint added
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  endpoint added
- **CHANGE** for **URL**: /api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}  endpoint added

# 10/10/2025
- **CHANGE** for **URL**: /v1/span/{span_id}/metrics  added the optional property 'session_id' to the response with the '200' status
- **CHANGE** for **URL**: /v1/span/{span_id}/metrics  added the required property 'status_code' to the response with the '200' status
- **CHANGE** for **URL**: /v1/spans/query  added the optional property 'spans/items/session_id' to the response with the '200' status
- **CHANGE** for **URL**: /v1/spans/query  added the required property 'spans/items/status_code' to the response with the '200' status
- **CHANGE** for **URL**: /v1/traces/metrics/  added the optional property 'traces/items/root_spans/items/session_id' to the response with the '200' status
- **CHANGE** for **URL**: /v1/traces/metrics/  added the required property 'traces/items/root_spans/items/status_code' to the response with the '200' status
- **CHANGE** for **URL**: /v1/traces/query  added the optional property 'traces/items/root_spans/items/session_id' to the response with the '200' status
- **CHANGE** for **URL**: /v1/traces/query  added the required property 'traces/items/root_spans/items/status_code' to the response with the '200' status

# 10/09/2025
- **BREAKING CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/delete_prompt/{prompt_name}  api path removed without deprecation
- **BREAKING CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/get_all_prompts  api path removed without deprecation
- **BREAKING CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/get_prompt/{prompt_name}  api path removed without deprecation
- **BREAKING CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/run_prompt  api path removed without deprecation
- **BREAKING CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/run_prompt/{prompt_name}  api path removed without deprecation
- **BREAKING CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/save_prompt  api path removed without deprecation
- **BREAKING CHANGE** for **URL**: /v1/{task_id}/agentic_prompt/update_prompt  api path removed without deprecation

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
