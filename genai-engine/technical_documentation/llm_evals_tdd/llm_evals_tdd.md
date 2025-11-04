# Prompts LLM Evals Lifecycle Technical Design Doc

## Backend

### DB
- Create an LLM Evals table that will hold all the eval prompts
- DB Schema:
    ```
    task_id: str
    name: str
    model_provider: str
    model_name: str
    instructions: str
    score_range: JSON (a min_score and max_score range defaults to boolean)
    config: JSON
    created_at: timestamp
    deleted_at: timestamp
    version: int
    ```
- enforce same unique constraint as agentic prompts for task_id, name and version, and also have a unique id exclusive to the table

### Class Schemas:
- ScoreRange
  ```python
  min_score: int
  max_score: int
  ```

- LLMEvalMetadata:
  ```python
  name: str
  versions: int
  created_at: datetime
  latest_version_created_at: datetime
  deleted_versions: List[int]
  ```

- LLMEvalMetadataListResponse
    ```python
    eval_metadata: List[LLMEvalMetadata]
    count: int
    ```

- LLMEvalsGetAllFilterRequest
    ```python
    eval_names: Optional[list[str]]
    model_provider: Optional[ModelProvider]
    model_name: Optional[str]
    created_after: Optional[datetime]
    created_before: Optional[datetime]
    ```

- LLMEvalsGetVersionsFilterRequest
    ```python
    model_provider: Optional[ModelProvider]
    model_name: Optional[str]
    created_after: Optional[datetime]
    created_before: Optional[datetime]
    exclude_deleted: Optional[bool]
    min_version: Optional[int]
    max_version: Optional[int]
    ```

- LLMEvalsVersionResponse
    ```python
    version: int
    created_at: datetime
    deleted_at: Optional[datetime]
    model_provider: ModelProvider
    model_name: str
    ```

- LLMEvalsVersionListResponse
    ```python
    versions: list[LLMEvalsVersionResponse]
    count: int
    ```

- LLMEvalResponseFormat
  ```python
  score_range: [ScoreRange | bool]
  reasoning: str
  ```

- LLMEvalRunRequest
  ```python
  variables: Optional[List[VariableTemplateValue]]
  ```

- LLMEval:
    ```python
    instructions: str
    model_name: str
    model_provider: ModelProvider
    version: int
    score_range: ScoreRange
    timeout: Optional[float]
    temperature: Optional[float]
    top_p: Optional[float]
    max_tokens: Optional[int]
    stop: Optional[str]
    presence_penalty: Optional[float]
    frequency_penalty: Optional[float]
    seed: Optional[int]
    logprobs: Optional[bool]
    top_logprobs: Optional[int]
    logit_bias: Optional[List[LogitBiasItem]]
    max_completion_tokens: Optional[int]
    reasoning_effort: Optional[ReasoningEffortEnum]
    thinking: Optional[AnthropicThinkingParam]
    created_at: Optional[datetime]
    deleted_at: Optional[datetime]
    ```

- CreateEvalRequest
    ```python
    instructions: str
    model_name: str
    model_provider: ModelProvider
    timeout: Optional[float]
    temperature: Optional[float]
    top_p: Optional[float]
    max_tokens: Optional[int]
    stop: Optional[str]
    presence_penalty: Optional[float]
    frequency_penalty: Optional[float]
    seed: Optional[int]
    logprobs: Optional[bool]
    top_logprobs: Optional[int]
    logit_bias: Optional[List[LogitBiasItem]]
    max_completion_tokens: Optional[int]
    reasoning_effort: Optional[ReasoningEffortEnum]
    thinking: Optional[AnthropicThinkingParam]
    ```

- LLMEvalRunResponse:
  ```python
  score: [int | bool]
  reason: str
  cost: float
  ```

### Repository
- LLM Evals Repository:
    - get_all_evals:
        - Inputs:
            - task_id: str
            - pagination_params: PaginationParameters
            - filter_request: LLMEvalsGetAllFilterRequest
        - Outputs: LLMEvalMetadataListResponse
    - get_eval_versions:
        - Inputs:
            - task_id: str
            - eval_id: str
            - pagination_params: PaginationParameters
            - filter_request: LLMEvalsGetVersionsFilterRequest
        - Outputs: LLMEvalsVersionListResponse
    - get_eval:
        - Inputs:
            - task_id: str
            - eval_id: str
            - version: str (latest, number or timestamp)
        - Outputs: LLMEval
    - save_eval:
        - Inputs:
            - task_id: str
            - eval_request: CreateEvalRequest (in diagram below)
        - Outputs: AgenticPrompt
    - soft_delete_eval_version:
        - Inputs:
            - task_id: str
            - eval_id: str
            - version: str  (latest, number or timestamp)
        - Outputs: None
    - delete_eval:
        - Inputs:
            - task_id: str
            - eval_id: str
        - Outputs: None

### LLM Evals Router

- POST: /tasks/{task_id}/llm_evals - Creates a new version of a prompt which has the following parameters:
    - Request:
      - CreateEvalRequest
        - required:
            - name
            - model_provider
            - model_name
            - instructions
            - score range
        - Optional:
            - The rest of the LLM config settings (e.g. temperature)
    - Response:
        - LLMEval
    - Functionality:
        - Uses the request parameters to create an LLMEval and save it to the llm_evals table
- GET: /tasks/{task_id}/llm_evals - Lists all llm evals
    - Request:
        - PaginationParameters
        - LLMEvalsGetAllFilterRequest
    - Response:
        - LLMEvalMetadataListResponse
- GET: /tasks/{task_id}/llm_evals/{evaluator_id}/versions - Lists all versions of a specific llm_eval
    - Request:
      - PaginationParameters
      - LLMEvalsGetVersionsFilterRequest
    - Response:
      - LLMEvalsVersionListResponse
- POST: /tasks/{task_id}/llm_evals/{eval_id}/versions/{version}
    - Request:
      - LLMEvalRunRequest
    - Response:
        - LLMEvalRunResponse
    - Functionality:
      - grabs an llm_eval from the db
      - converts it to an AgenticPrompt by setting the instructions to the system prompt and converting the LLMEvalResponseFormat to a properly formatted response_format in OpenAI formatting style
      - Converts the LLMEvalRunRequest to an AgenticPromptRunRequest with the same variables, strict=True, stream=False
      - run chat completion
- DELETE: /tasks/{task_id}/llm_evals/{eval_id}/versions/{version} - soft-delete a version of an llm eval
- DELETE: /tasks/{task_id}/llm_evals/{eval_id} - Delete all versions of an llm eval
- Future additions:
    - either a new endpoint or modify the existing completions endpoint with a dataset_id/or list of trace ids/etc to run completions in bulk without needing to make multiple requests

### Template llm evaluators

- Incorporate Ragas - Extract and send the formatted prompts for Martin to have on the frontend (< 1 day)
- Creating our own custom llm-as-a-judge evals (the list below is straight from langfuse but we can change it)
    - Conciseness
    - Context correctness
    - context relevance
    - hallucination
    - helpfulness
    - relevance
    - toxicity
    - In terms of timing for each of these I could see each being 1 day, a few days or potentially even longer. Not sure how much time we want to dedicate to each of these. But finding datasets to benchmark each of these evaluators and iterating to find the best llm-as-a-judge prompt can definitely take some time.


### Diagrams
![llm_eval_table](./img/llm_evals_table_schema.png)
![llm_eval_workflow.png](./img/llm_eval_workflow.png)
![save_eval](./img/save_llm_eval.png)
![run_eval](./img/run_llm_eval.png)
![get_eval](./img/get_llm_eval.png)
![get_eval_versions](./img/list_versions.png)
![get_all_evals](./img/get_all_llm_evals.png)
![delete_evals](./img/delete_evals.png)

### Examples

- POST: /tasks/{task_id}/llm_evals/{eval_name}
    - Input:
        ```json
        {
            "model_name": "gpt-4o",
            "model_provider": "openai",
            "instructions": "Given a ground truth and an answer statements, analyze each statement and classify them in one of the following categories: TP (true positive): statements that are present in answer that are also directly supported by the one or more statements in ground truth, FP (false positive): statements present in the answer but not directly supported by any statement in ground truth, FN (false negative): statements found in the ground truth but not present in answer. Each statement can only belong to one of the categories. Provide a reason for each classification. Examples: {{examples}}",
            "score_range": {
                "min_score": 0,
                "max_score": 1
            },
            "temperature": 0
        }
        ```
    - Response:
        ```json
        {
            "name": "{eval_name}",
            "model_name": "gpt-4o",
            "model_provider": "openai",
            "instructions": "Given a ground truth and an answer statements, analyze each statement and classify them in one of the following categories: TP (true positive): statements that are present in answer that are also directly supported by the one or more statements in ground truth, FP (false positive): statements present in the answer but not directly supported by any statement in ground truth, FN (false negative): statements found in the ground truth but not present in answer. Each statement can only belong to one of the categories. Provide a reason for each classification. Examples: {{examples}}",
            "score_range": {
                "min_score": 0,
                "max_score": 1
            },
            "temperature": 0,
            "version": 1,
            "created_at": "2025-10-31T09:23:45-05:00",
            "deleted_at": null
        }
        ```

- POST: /tasks/{task_id}/llm_evals/{eval_name}/versions/{version}/completions
  - Input: 
    ```json
    {
        "variables": [
            {"name": "ground_truth", "value": "The sky is blue"},
            {"name": "answer", "value": "The sky is green"}
        ]
    }
    ```
  - BE Conversion: 
    ```json
    {
        "variables": [
            {"name": "ground_truth", "value": "The sky is blue"},
            {"name": "answer", "value": "The sky is green"}
        ],
        "strict": true,
        "stream": false,
    }
    ```
  - Response: 
    ```json
    {
        "score": 1,
        "reasoning": "The answer statements mostly align with the ground truth, with only minor omissions that do not affect accuracy.",
        "cost": 0.00012,
    }
    ```    

- GET: /tasks/{task_id}/llm_evals/{eval_name}/versions/{version}
    ```json
    {
        "name": "{eval_name}",
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Given a ground truth and an answer statements, analyze each statement and classify them in one of the following categories: TP (true positive): statements that are present in answer that are also directly supported by the one or more statements in ground truth, FP (false positive): statements present in the answer but not directly supported by any statement in ground truth, FN (false negative): statements found in the ground truth but not present in answer. Each statement can only belong to one of the categories. Provide a reason for each classification. Examples: {{examples}}",
        "score_range": {
            "min_score": 0,
            "max_score": 1
        },
        "temperature": 0,
        "version": 1,
        "created_at": "2025-10-31T09:23:45-05:00"
    }
    ```    

- GET: /tasks/{task_id}/llm_evals/{eval_name}/versions
    ```json
    {
        "versions": [
            "version": 1,
            "created_at": "2025-10-20T09:23:45-05:00",
            "deleted_at": null,
            "model_provider": "openai",
            "model_name": "gpt-4o",
        ],
        "count": 1
    }
    ```   

- GET: /tasks/{task_id}/llm_evals
    ```json
    {
        "eval_metadata": [
            "name": "test_eval",
            "versions": 3,
            "created_at": "2025-10-31T09:23:45-05:00",
            "latest_version_created_at": "2025-10-31T09:23:45-05:00",
            "deleted_versions": [1, 2]
        ],
        "count": 1
    }
    ```   

- DELETE: /tasks/{task_id}/llm_evals/{eval_name}
    - 204 no content response, deletes all versions of an eval

- DELETE: /tasks/{task_id}/llm_evals/{eval_name}/versions/{version}
    - 204 no content response, soft-deletes a specific version of an eval


### Tasks
- Create llm_evals table (<1 day)
- Save an llm_eval (<1 day)
- Run a saved llm_eval (<1 day)
- Create get requests for llm_evals (~1 day)
- Create delete requests for llm_evals (<1 day)
- Extract Ragas prompts for FE (<1 day)
- Run llm evals over entire datasets/traces (future work, just noting it so we don't lose track)

## Frontend

- Create template prompts for pre-built metrics. These will be static strings we can load in as the eval prompt. For example,  answer correctness from ragas could look like:

```
-----------------------------------------------------
Instruction (System) Prompt:

Given a ground truth and an answer statements, analyze each statement and classify them in one of the following categories: TP (true positive): statements that are present in answer that are also directly supported by the one or more statements in ground truth, FP (false positive): statements present in the answer but not directly supported by any statement in ground truth, FN (false negative): statements found in the ground truth but not present in answer. Each statement can only belong to one of the categories. Provide a reason for each classification.

Examples: {{examples}}

ground truth: {{ground_truth}}
answer: {{answer}}

-----------------------------------------------------
```

- Tal - Extract and send prompts for Martin to use
- Martin - Implement the pre-built prompts on the frontend