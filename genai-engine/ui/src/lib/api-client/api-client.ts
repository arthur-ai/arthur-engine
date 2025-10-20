/* eslint-disable */
/* tslint:disable */
/*
 * ---------------------------------------------------------------
 * ## THIS FILE WAS GENERATED VIA SWAGGER-TYPESCRIPT-API        ##
 * ##                                                           ##
 * ## AUTHOR: acacode                                           ##
 * ## SOURCE: https://github.com/acacode/swagger-typescript-api ##
 * ---------------------------------------------------------------
 */

/** APIKeysRolesEnum */
export type APIKeysRolesEnum = "DEFAULT-RULE-ADMIN" | "TASK-ADMIN" | "VALIDATION-USER" | "ORG-AUDITOR" | "ORG-ADMIN";

/** AgenticPrompt */
export interface AgenticPrompt {
  /**
   * Frequency Penalty
   * Frequency penalty (-2.0 to 2.0). Positive values penalize tokens based on frequency
   */
  frequency_penalty?: number | null;
  /**
   * Logit Bias
   * Modify likelihood of specified tokens appearing in completion
   */
  logit_bias?: LogitBiasItem[] | null;
  /**
   * Logprobs
   * Whether to return log probabilities of output tokens
   */
  logprobs?: boolean | null;
  /**
   * Max Completion Tokens
   * Maximum number of completion tokens (alternative to max_tokens)
   */
  max_completion_tokens?: number | null;
  /**
   * Max Tokens
   * Maximum number of tokens to generate in the response
   */
  max_tokens?: number | null;
  /**
   * Messages
   * List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])
   */
  messages: AgenticPromptMessageOutput[];
  /**
   * Model Name
   * Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')
   */
  model_name: string;
  /** Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure') */
  model_provider: ProviderEnum;
  /**
   * Name
   * Name of the agentic prompt
   */
  name: string;
  /**
   * Presence Penalty
   * Presence penalty (-2.0 to 2.0). Positive values penalize new tokens based on their presence
   */
  presence_penalty?: number | null;
  /** Reasoning effort level for models that support it (e.g., OpenAI o1 series) */
  reasoning_effort?: ReasoningEffortEnum | null;
  /** Response format specification (e.g., {'type': 'json_object'} for JSON mode) */
  response_format?: LLMResponseFormatOutput | null;
  /**
   * Seed
   * Random seed for reproducible outputs
   */
  seed?: number | null;
  /**
   * Stop
   * Stop sequence(s) where the model should stop generating
   */
  stop?: string | null;
  /** Additional streaming configuration options */
  stream_options?: StreamOptions | null;
  /**
   * Temperature
   * Sampling temperature (0.0 to 2.0). Higher values make output more random
   */
  temperature?: number | null;
  /** Anthropic-specific thinking parameter for Claude models */
  thinking?: AnthropicThinkingParam | null;
  /**
   * Timeout
   * Request timeout in seconds
   */
  timeout?: number | null;
  /**
   * Tool Choice
   * Tool choice configuration ('auto', 'none', 'required', or a specific tool selection)
   */
  tool_choice?: ToolChoiceEnum | string | null;
  /**
   * Tools
   * Available tools/functions for the model to call, in OpenAI function calling format
   */
  tools?: LLMToolOutput[] | null;
  /**
   * Top Logprobs
   * Number of most likely tokens to return log probabilities for (1-20)
   */
  top_logprobs?: number | null;
  /**
   * Top P
   * Top-p sampling parameter (0.0 to 1.0). Alternative to temperature
   */
  top_p?: number | null;
}

/** AgenticPromptBaseConfig */
export interface AgenticPromptBaseConfig {
  /**
   * Frequency Penalty
   * Frequency penalty (-2.0 to 2.0). Positive values penalize tokens based on frequency
   */
  frequency_penalty?: number | null;
  /**
   * Logit Bias
   * Modify likelihood of specified tokens appearing in completion
   */
  logit_bias?: LogitBiasItem[] | null;
  /**
   * Logprobs
   * Whether to return log probabilities of output tokens
   */
  logprobs?: boolean | null;
  /**
   * Max Completion Tokens
   * Maximum number of completion tokens (alternative to max_tokens)
   */
  max_completion_tokens?: number | null;
  /**
   * Max Tokens
   * Maximum number of tokens to generate in the response
   */
  max_tokens?: number | null;
  /**
   * Messages
   * List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])
   */
  messages: AgenticPromptMessageInput[];
  /**
   * Model Name
   * Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')
   */
  model_name: string;
  /** Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure') */
  model_provider: ProviderEnum;
  /**
   * Presence Penalty
   * Presence penalty (-2.0 to 2.0). Positive values penalize new tokens based on their presence
   */
  presence_penalty?: number | null;
  /** Reasoning effort level for models that support it (e.g., OpenAI o1 series) */
  reasoning_effort?: ReasoningEffortEnum | null;
  /** Response format specification (e.g., {'type': 'json_object'} for JSON mode) */
  response_format?: LLMResponseFormatInput | null;
  /**
   * Seed
   * Random seed for reproducible outputs
   */
  seed?: number | null;
  /**
   * Stop
   * Stop sequence(s) where the model should stop generating
   */
  stop?: string | null;
  /** Additional streaming configuration options */
  stream_options?: StreamOptions | null;
  /**
   * Temperature
   * Sampling temperature (0.0 to 2.0). Higher values make output more random
   */
  temperature?: number | null;
  /** Anthropic-specific thinking parameter for Claude models */
  thinking?: AnthropicThinkingParam | null;
  /**
   * Timeout
   * Request timeout in seconds
   */
  timeout?: number | null;
  /**
   * Tool Choice
   * Tool choice configuration ('auto', 'none', 'required', or a specific tool selection)
   */
  tool_choice?: ToolChoiceEnum | string | null;
  /**
   * Tools
   * Available tools/functions for the model to call, in OpenAI function calling format
   */
  tools?: LLMToolInput[] | null;
  /**
   * Top Logprobs
   * Number of most likely tokens to return log probabilities for (1-20)
   */
  top_logprobs?: number | null;
  /**
   * Top P
   * Top-p sampling parameter (0.0 to 1.0). Alternative to temperature
   */
  top_p?: number | null;
}

/** AgenticPromptMessage */
export interface AgenticPromptMessageInput {
  /**
   * Content
   * Content of the message
   */
  content?: string | null;
  /** Role of the message */
  role: MessageRole;
  /**
   * Tool Call Id
   * ID of the tool call this message is responding to
   */
  tool_call_id?: string | null;
  /**
   * Tool Calls
   * Tool calls made by assistant
   */
  tool_calls?: ToolCallInput[] | null;
}

/** AgenticPromptMessage */
export interface AgenticPromptMessageOutput {
  /**
   * Content
   * Content of the message
   */
  content?: string | null;
  /** Role of the message */
  role: MessageRole;
  /**
   * Tool Call Id
   * ID of the tool call this message is responding to
   */
  tool_call_id?: string | null;
  /**
   * Tool Calls
   * Tool calls made by assistant
   */
  tool_calls?: ToolCallOutput[] | null;
}

/**
 * AgenticPromptRunConfig
 * Request schema for running an agentic prompt
 */
export interface AgenticPromptRunConfig {
  /**
   * Stream
   * Whether to stream the response
   * @default false
   */
  stream?: boolean | null;
  /**
   * Variables
   * List of VariableTemplateValue fields that specify the values to fill in for each template in the prompt
   * @default []
   */
  variables?: VariableTemplateValue[] | null;
}

/** AgenticPromptRunResponse */
export interface AgenticPromptRunResponse {
  /** Content */
  content?: string | null;
  /** Cost */
  cost: string;
  /** Tool Calls */
  tool_calls?: ChatCompletionMessageToolCall[] | null;
}

/**
 * AgenticPromptUnsavedRunConfig
 * Request schema for running an unsaved agentic prompt
 */
export interface AgenticPromptUnsavedRunConfig {
  /**
   * Frequency Penalty
   * Frequency penalty (-2.0 to 2.0). Positive values penalize tokens based on frequency
   */
  frequency_penalty?: number | null;
  /**
   * Logit Bias
   * Modify likelihood of specified tokens appearing in completion
   */
  logit_bias?: LogitBiasItem[] | null;
  /**
   * Logprobs
   * Whether to return log probabilities of output tokens
   */
  logprobs?: boolean | null;
  /**
   * Max Completion Tokens
   * Maximum number of completion tokens (alternative to max_tokens)
   */
  max_completion_tokens?: number | null;
  /**
   * Max Tokens
   * Maximum number of tokens to generate in the response
   */
  max_tokens?: number | null;
  /**
   * Messages
   * List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])
   */
  messages: AgenticPromptMessageInput[];
  /**
   * Model Name
   * Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')
   */
  model_name: string;
  /** Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure') */
  model_provider: ProviderEnum;
  /**
   * Presence Penalty
   * Presence penalty (-2.0 to 2.0). Positive values penalize new tokens based on their presence
   */
  presence_penalty?: number | null;
  /** Reasoning effort level for models that support it (e.g., OpenAI o1 series) */
  reasoning_effort?: ReasoningEffortEnum | null;
  /** Response format specification (e.g., {'type': 'json_object'} for JSON mode) */
  response_format?: LLMResponseFormatInput | null;
  /**
   * Run configuration for the unsaved prompt
   * @default {"variables":[],"stream":false}
   */
  run_config?: AgenticPromptRunConfig;
  /**
   * Seed
   * Random seed for reproducible outputs
   */
  seed?: number | null;
  /**
   * Stop
   * Stop sequence(s) where the model should stop generating
   */
  stop?: string | null;
  /** Additional streaming configuration options */
  stream_options?: StreamOptions | null;
  /**
   * Temperature
   * Sampling temperature (0.0 to 2.0). Higher values make output more random
   */
  temperature?: number | null;
  /** Anthropic-specific thinking parameter for Claude models */
  thinking?: AnthropicThinkingParam | null;
  /**
   * Timeout
   * Request timeout in seconds
   */
  timeout?: number | null;
  /**
   * Tool Choice
   * Tool choice configuration ('auto', 'none', 'required', or a specific tool selection)
   */
  tool_choice?: ToolChoiceEnum | string | null;
  /**
   * Tools
   * Available tools/functions for the model to call, in OpenAI function calling format
   */
  tools?: LLMToolInput[] | null;
  /**
   * Top Logprobs
   * Number of most likely tokens to return log probabilities for (1-20)
   */
  top_logprobs?: number | null;
  /**
   * Top P
   * Top-p sampling parameter (0.0 to 1.0). Alternative to temperature
   */
  top_p?: number | null;
}

/** AgenticPrompts */
export interface AgenticPrompts {
  /** Prompts */
  prompts: AgenticPrompt[];
}

/** AnthropicThinkingParam */
export interface AnthropicThinkingParam {
  /** Budget Tokens */
  budget_tokens?: number;
  /** Type */
  type?: "enabled";
}

/** ApiKeyResponse */
export interface ApiKeyResponse {
  /**
   * Created At
   * Creation time of the key
   * @format date-time
   */
  created_at: string;
  /**
   * Deactivated At
   * Deactivation time of the key
   */
  deactivated_at?: string | null;
  /**
   * Description
   * Description of the API key
   */
  description?: string | null;
  /**
   * Id
   * ID of the key
   */
  id: string;
  /**
   * Is Active
   * Status of the key.
   */
  is_active: boolean;
  /**
   * Key
   * The generated GenAI Engine API key. The key is displayed on key creation request only.
   */
  key?: string | null;
  /**
   * Message
   * Optional Message
   */
  message?: string | null;
  /**
   * Roles
   * Roles of the API key
   * @default []
   */
  roles?: string[];
}

export type ArchiveDefaultRuleApiV2DefaultRulesRuleIdDeleteData = any;

export type ArchiveDefaultRuleApiV2DefaultRulesRuleIdDeleteError = HTTPValidationError;

export type ArchiveTaskApiV2TasksTaskIdDeleteData = any;

export type ArchiveTaskApiV2TasksTaskIdDeleteError = HTTPValidationError;

export type ArchiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDeleteData = any;

export type ArchiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDeleteError = HTTPValidationError;

export type ArchiveTaskRuleApiV2TasksTaskIdRulesRuleIdDeleteData = any;

export type ArchiveTaskRuleApiV2TasksTaskIdRulesRuleIdDeleteError = HTTPValidationError;

/** AuthUserRole */
export interface AuthUserRole {
  /** Composite */
  composite: boolean;
  /** Description */
  description: string;
  /** Id */
  id?: string | null;
  /** Name */
  name: string;
}

/** BaseDetailsResponse */
export interface BaseDetailsResponse {
  /** Message */
  message?: string | null;
  /** Score */
  score?: boolean | null;
}

/** Body_upload_embeddings_file_api_chat_files_post */
export interface BodyUploadEmbeddingsFileApiChatFilesPost {
  /**
   * File
   * @format binary
   */
  file: File;
}

/** ChatCompletionMessageToolCall */
export type ChatCompletionMessageToolCall = Record<string, any>;

/** ChatDefaultTaskRequest */
export interface ChatDefaultTaskRequest {
  /** Task Id */
  task_id: string;
}

/** ChatDefaultTaskResponse */
export interface ChatDefaultTaskResponse {
  /** Task Id */
  task_id: string;
}

/** ChatDocumentContext */
export interface ChatDocumentContext {
  /** Context */
  context: string;
  /** Id */
  id: string;
  /** Seq Num */
  seq_num: number;
}

/** ChatRequest */
export interface ChatRequest {
  /**
   * Conversation Id
   * Conversation ID
   */
  conversation_id: string;
  /**
   * File Ids
   * list of file IDs to retrieve from during chat.
   */
  file_ids: string[];
  /**
   * User Prompt
   * Prompt user wants to send to chat.
   */
  user_prompt: string;
}

export type ChatRequestData = ChatResponse;

export type ChatRequestError = HTTPValidationError;

/** ChatResponse */
export interface ChatResponse {
  /**
   * Conversation Id
   * ID of the conversation session
   */
  conversation_id: string;
  /**
   * Inference Id
   * ID of the inference sent to the chat
   */
  inference_id: string;
  /**
   * Llm Response
   * response from the LLM for the original user prompt
   */
  llm_response: string;
  /**
   * Model Name
   * The model name and version used for this chat response (e.g., 'gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'gemini-pro').
   */
  model_name?: string | null;
  /**
   * Prompt Results
   * list of rule results for the user prompt
   */
  prompt_results: ExternalRuleResult[];
  /**
   * Response Results
   * list of rule results for the llm response
   */
  response_results: ExternalRuleResult[];
  /**
   * Retrieved Context
   * related sections of documents that were most relevant to the inference prompt. Formatted as a list of retrieved context chunks which include document name, seq num, and context.
   */
  retrieved_context: ChatDocumentContext[];
  /**
   * Timestamp
   * Time the inference was made in unix milliseconds
   */
  timestamp: number;
}

export type CheckUserPermissionUsersPermissionsCheckGetData = any;

export type CheckUserPermissionUsersPermissionsCheckGetError = HTTPValidationError;

export interface CheckUserPermissionUsersPermissionsCheckGetParams {
  /** Action to check permissions of. */
  action?: UserPermissionAction;
  /** Resource to check permissions of. */
  resource?: UserPermissionResource;
}

export type ComputeSessionMetricsApiV1SessionsSessionIdMetricsGetData = SessionTracesResponse;

export type ComputeSessionMetricsApiV1SessionsSessionIdMetricsGetError = HTTPValidationError;

export interface ComputeSessionMetricsApiV1SessionsSessionIdMetricsGetParams {
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /** Session Id */
  sessionId: string;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
}

export type ComputeSpanMetricsApiV1SpansSpanIdMetricsGetData = SpanWithMetricsResponse;

export type ComputeSpanMetricsApiV1SpansSpanIdMetricsGetError = HTTPValidationError;

export type ComputeSpanMetricsV1SpanSpanIdMetricsGetData = SpanWithMetricsResponse;

export type ComputeSpanMetricsV1SpanSpanIdMetricsGetError = HTTPValidationError;

export type ComputeTraceMetricsApiV1TracesTraceIdMetricsGetData = TraceResponse;

export type ComputeTraceMetricsApiV1TracesTraceIdMetricsGetError = HTTPValidationError;

/** ConversationBaseResponse */
export interface ConversationBaseResponse {
  /** Id */
  id: string;
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
}

export type CreateApiKeyAuthApiKeysPostData = ApiKeyResponse;

export type CreateApiKeyAuthApiKeysPostError = HTTPValidationError;

export type CreateDefaultRuleApiV2DefaultRulesPostData = RuleResponse;

export type CreateDefaultRuleApiV2DefaultRulesPostError = HTTPValidationError;

export type CreateTaskApiV2TasksPostData = TaskResponse;

export type CreateTaskApiV2TasksPostError = HTTPValidationError;

export type CreateTaskMetricApiV2TasksTaskIdMetricsPostData = any;

export type CreateTaskMetricApiV2TasksTaskIdMetricsPostError = HTTPValidationError;

export type CreateTaskRuleApiV2TasksTaskIdRulesPostData = RuleResponse;

export type CreateTaskRuleApiV2TasksTaskIdRulesPostError = HTTPValidationError;

/** CreateUserRequest */
export interface CreateUserRequest {
  /** Email */
  email: string;
  /** Firstname */
  firstName: string;
  /** Lastname */
  lastName: string;
  /** Password */
  password: string;
  /** Roles */
  roles: string[];
  /**
   * Temporary
   * @default true
   */
  temporary?: boolean;
}

export type CreateUserUsersPostData = any;

export type CreateUserUsersPostError = HTTPValidationError;

export type DeactivateApiKeyAuthApiKeysDeactivateApiKeyIdDeleteData = ApiKeyResponse;

export type DeactivateApiKeyAuthApiKeysDeactivateApiKeyIdDeleteError = HTTPValidationError;

export type DefaultValidatePromptApiV2ValidatePromptPostData = ValidationResult;

export type DefaultValidatePromptApiV2ValidatePromptPostError = HTTPValidationError;

export type DefaultValidateResponseApiV2ValidateResponseInferenceIdPostData = ValidationResult;

export type DefaultValidateResponseApiV2ValidateResponseInferenceIdPostError = HTTPValidationError;

export type DeleteAgenticPromptApiV1TaskIdAgenticPromptsPromptNameDeleteData = any;

export type DeleteAgenticPromptApiV1TaskIdAgenticPromptsPromptNameDeleteError = HTTPValidationError;

export type DeleteAgenticPromptVersionApiV1TaskIdAgenticPromptsPromptNameVersionsPromptVersionDeleteData = any;

export type DeleteAgenticPromptVersionApiV1TaskIdAgenticPromptsPromptNameVersionsPromptVersionDeleteError =
  HTTPValidationError;

export type DeleteFileApiChatFilesFileIdDeleteData = any;

export type DeleteFileApiChatFilesFileIdDeleteError = HTTPValidationError;

export type DeleteUserUsersUserIdDeleteData = any;

export type DeleteUserUsersUserIdDeleteError = HTTPValidationError;

/**
 * ExampleConfig
 * @example {"example":"John has O negative blood group","result":true}
 */
export interface ExampleConfig {
  /**
   * Example
   * Custom example for the sensitive data
   */
  example: string;
  /**
   * Result
   * Boolean value representing if the example passes or fails the the sensitive data rule
   */
  result: boolean;
}

/**
 * ExamplesConfig
 * @example {"examples":[{"example":"John has O negative blood group","result":true},{"example":"Most of the people have A positive blood group","result":false}],"hint":"specific individual's blood type"}
 */
export interface ExamplesConfig {
  /**
   * Examples
   * List of all the examples for Sensitive Data Rule
   */
  examples: ExampleConfig[];
  /**
   * Hint
   * Optional. Hint added to describe what Sensitive Data Rule should be checking for
   */
  hint?: string | null;
}

/** ExternalDocument */
export interface ExternalDocument {
  /** Id */
  id: string;
  /** Name */
  name: string;
  /** Owner Id */
  owner_id: string;
  /** Type */
  type: string;
}

/** ExternalInference */
export interface ExternalInference {
  /** Conversation Id */
  conversation_id?: string | null;
  /** Created At */
  created_at: number;
  /** Id */
  id: string;
  /** Inference Feedback */
  inference_feedback: InferenceFeedbackResponse[];
  inference_prompt: ExternalInferencePrompt;
  inference_response?: ExternalInferenceResponse | null;
  /**
   * Model Name
   * The model name and version used for this inference (e.g., 'gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'gemini-pro').
   */
  model_name?: string | null;
  result: RuleResultEnum;
  /** Task Id */
  task_id?: string | null;
  /** Task Name */
  task_name?: string | null;
  /** Updated At */
  updated_at: number;
  /** User Id */
  user_id?: string | null;
}

/** ExternalInferencePrompt */
export interface ExternalInferencePrompt {
  /** Created At */
  created_at: number;
  /** Id */
  id: string;
  /** Inference Id */
  inference_id: string;
  /** Message */
  message: string;
  /**
   * Model Name
   * The model name and version used for this prompt (e.g., 'gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'gemini-pro').
   */
  model_name?: string | null;
  /** Prompt Rule Results */
  prompt_rule_results: ExternalRuleResult[];
  result: RuleResultEnum;
  /** Tokens */
  tokens?: number | null;
  /** Updated At */
  updated_at: number;
}

/** ExternalInferenceResponse */
export interface ExternalInferenceResponse {
  /** Context */
  context?: string | null;
  /** Created At */
  created_at: number;
  /** Id */
  id: string;
  /** Inference Id */
  inference_id: string;
  /** Message */
  message: string;
  /**
   * Model Name
   * The model name and version used for this response (e.g., 'gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'gemini-pro').
   */
  model_name?: string | null;
  /** Response Rule Results */
  response_rule_results: ExternalRuleResult[];
  result: RuleResultEnum;
  /** Tokens */
  tokens?: number | null;
  /** Updated At */
  updated_at: number;
}

/**
 * ExternalRuleResult
 * @example {"id":"90f18c69-d793-4913-9bde-a0c7f3643de0","name":"PII Rule","result":"Pass"}
 */
export interface ExternalRuleResult {
  /**
   * Details
   * Details of the rule output
   */
  details?:
    | KeywordDetailsResponse
    | RegexDetailsResponse
    | HallucinationDetailsResponse
    | PIIDetailsResponse
    | ToxicityDetailsResponse
    | BaseDetailsResponse
    | null;
  /**
   * Id
   *  ID of the rule
   */
  id: string;
  /**
   * Latency Ms
   * Duration in millisesconds of rule execution
   */
  latency_ms: number;
  /**
   * Name
   * Name of the rule
   */
  name: string;
  /** Result if the rule */
  result: RuleResultEnum;
  /** Type of the rule */
  rule_type: RuleType;
  /** Scope of the rule. The rule can be set at default level or task level. */
  scope: RuleScope;
}

/** FeedbackRequest */
export interface FeedbackRequest {
  /** Reason */
  reason: string | null;
  /** Score */
  score: number;
  target: InferenceFeedbackTarget;
  /** User Id */
  user_id?: string | null;
}

/** FileUploadResult */
export interface FileUploadResult {
  /** Id */
  id: string;
  /** Name */
  name: string;
  /** Success */
  success: boolean;
  /** Type */
  type: string;
  /** Word Count */
  word_count: number;
}

export type GetAgenticPromptApiV1TaskIdAgenticPromptsPromptNameVersionsPromptVersionGetData = AgenticPrompt;

export type GetAgenticPromptApiV1TaskIdAgenticPromptsPromptNameVersionsPromptVersionGetError = HTTPValidationError;

/** Response Get All Active Api Keys Auth Api Keys  Get */
export type GetAllActiveApiKeysAuthApiKeysGetData = ApiKeyResponse[];

export type GetAllAgenticPromptVersionsApiV1TaskIdAgenticPromptsPromptNameVersionsGetData = AgenticPrompts;

export type GetAllAgenticPromptVersionsApiV1TaskIdAgenticPromptsPromptNameVersionsGetError = HTTPValidationError;

export type GetAllAgenticPromptsApiV1TaskIdAgenticPromptsGetData = AgenticPrompts;

export type GetAllAgenticPromptsApiV1TaskIdAgenticPromptsGetError = HTTPValidationError;

/** Response Get All Tasks Api V2 Tasks Get */
export type GetAllTasksApiV2TasksGetData = TaskResponse[];

export type GetApiKeyAuthApiKeysApiKeyIdGetData = ApiKeyResponse;

export type GetApiKeyAuthApiKeysApiKeyIdGetError = HTTPValidationError;

export type GetConversationsApiChatConversationsGetData = PageListConversationBaseResponse;

export type GetConversationsApiChatConversationsGetError = HTTPValidationError;

export interface GetConversationsApiChatConversationsGetParams {
  /**
   * Page
   * @min 1
   * @default 1
   */
  page?: number;
  /**
   * Size
   * @min 1
   * @max 100
   * @default 50
   */
  size?: number;
}

/** Response Get Default Rules Api V2 Default Rules Get */
export type GetDefaultRulesApiV2DefaultRulesGetData = RuleResponse[];

export type GetDefaultTaskApiChatDefaultTaskGetData = ChatDefaultTaskResponse;

/** Response Get Files Api Chat Files Get */
export type GetFilesApiChatFilesGetData = ExternalDocument[];

/** Response Get Inference Document Context Api Chat Context  Inference Id  Get */
export type GetInferenceDocumentContextApiChatContextInferenceIdGetData = ChatDocumentContext[];

export type GetInferenceDocumentContextApiChatContextInferenceIdGetError = HTTPValidationError;

export type GetSessionTracesApiV1SessionsSessionIdGetData = SessionTracesResponse;

export type GetSessionTracesApiV1SessionsSessionIdGetError = HTTPValidationError;

export interface GetSessionTracesApiV1SessionsSessionIdGetParams {
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /** Session Id */
  sessionId: string;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
}

export type GetSpanByIdApiV1SpansSpanIdGetData = SpanWithMetricsResponse;

export type GetSpanByIdApiV1SpansSpanIdGetError = HTTPValidationError;

export type GetTaskApiV2TasksTaskIdGetData = TaskResponse;

export type GetTaskApiV2TasksTaskIdGetError = HTTPValidationError;

/** Response Get Token Usage Api V2 Usage Tokens Get */
export type GetTokenUsageApiV2UsageTokensGetData = TokenUsageResponse[];

export type GetTokenUsageApiV2UsageTokensGetError = HTTPValidationError;

export interface GetTokenUsageApiV2UsageTokensGetParams {
  /**
   * End Time
   * Exclusive end date in ISO8601 string format. Defaults to the end of the current day if not provided.
   * @format date-time
   */
  end_time?: string;
  /**
   * Group By
   * Entities to group token counts on.
   * @default ["rule_type"]
   */
  group_by?: TokenUsageScope[];
  /**
   * Start Time
   * Inclusive start date in ISO8601 string format. Defaults to the beginning of the current day if not provided.
   * @format date-time
   */
  start_time?: string;
}

export type GetTraceByIdApiV1TracesTraceIdGetData = TraceResponse;

export type GetTraceByIdApiV1TracesTraceIdGetError = HTTPValidationError;

/**
 * HTTPError
 * @example {"detail":"HTTPException raised."}
 */
export interface HTTPError {
  /** Detail */
  detail: string;
}

/** HTTPValidationError */
export interface HTTPValidationError {
  /** Detail */
  detail?: ValidationError[];
}

/** HallucinationClaimResponse */
export interface HallucinationClaimResponse {
  /** Claim */
  claim: string;
  /**
   * Order Number
   * This field is a helper for ordering the claims
   * @default -1
   */
  order_number?: number | null;
  /** Reason */
  reason: string;
  /** Valid */
  valid: boolean;
}

/** HallucinationDetailsResponse */
export interface HallucinationDetailsResponse {
  /** Claims */
  claims: HallucinationClaimResponse[];
  /** Message */
  message?: string | null;
  /** Score */
  score?: boolean | null;
}

/** InferenceFeedbackResponse */
export interface InferenceFeedbackResponse {
  /**
   * Created At
   * @format date-time
   */
  created_at: string;
  /** Id */
  id: string;
  /** Inference Id */
  inference_id: string;
  /** Reason */
  reason?: string | null;
  /** Score */
  score: number;
  target: InferenceFeedbackTarget;
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
  /** User Id */
  user_id?: string | null;
}

/** InferenceFeedbackTarget */
export type InferenceFeedbackTarget = "context" | "response_results" | "prompt_results";

/** JsonPropertySchema */
export interface JsonPropertySchema {
  /**
   * Description
   * A description of the argument
   */
  description?: string | null;
  /**
   * Enum
   * An enum for the argument (e.g. ['celsius', 'fahrenheit'])
   */
  enum?: string[] | null;
  /**
   * Items
   * For array types, describes the items
   */
  items?: null;
  /**
   * Name
   * The name of the argument
   */
  name: string;
  /**
   * Type
   * The argument's type (e.g. string, boolean, etc.)
   * @default "string"
   */
  type?: string;
}

/** JsonSchema */
export interface JsonSchema {
  /**
   * Additional Properties
   * Whether the function definition should allow additional properties
   */
  additional_properties?: boolean | null;
  /**
   * Properties
   * The properties of the function
   */
  properties: JsonPropertySchema[];
  /**
   * Required
   * The required properties of the function
   */
  required?: string[];
  /**
   * Type
   * @default "object"
   */
  type?: string;
}

/** KeywordDetailsResponse */
export interface KeywordDetailsResponse {
  /**
   * Keyword Matches
   * Each keyword in this list corresponds to a keyword that was both configured in the rule that was run and found in the input text.
   * @default []
   */
  keyword_matches?: KeywordSpanResponse[];
  /** Message */
  message?: string | null;
  /** Score */
  score?: boolean | null;
}

/** KeywordSpanResponse */
export interface KeywordSpanResponse {
  /**
   * Keyword
   * The keyword from the rule that matched within the input string.
   */
  keyword: string;
}

/**
 * KeywordsConfig
 * @example {"keywords":["Blocked_Keyword_1","Blocked_Keyword_2"]}
 */
export interface KeywordsConfig {
  /**
   * Keywords
   * List of Keywords
   */
  keywords: string[];
}

/** LLMResponseFormatEnum */
export type LLMResponseFormatEnum = "text" | "json_object" | "json_schema";

/** LLMResponseFormat */
export interface LLMResponseFormatInput {
  /** JSON schema definition (required when type is 'json_schema') */
  response_schema?: LLMResponseSchemaInput | null;
  /** Response format type: 'text', 'json_object', or 'json_schema' */
  type: LLMResponseFormatEnum;
}

/** LLMResponseFormat */
export interface LLMResponseFormatOutput {
  /** JSON schema definition (required when type is 'json_schema') */
  response_schema?: LLMResponseSchemaOutput | null;
  /** Response format type: 'text', 'json_object', or 'json_schema' */
  type: LLMResponseFormatEnum;
}

/** LLMResponseSchema */
export interface LLMResponseSchemaInput {
  /**
   * Description
   * Description of the schema
   */
  description?: string | null;
  /** The JSON schema object */
  json_schema: JsonSchema;
  /**
   * Name
   * Name of the schema
   */
  name: string;
  /**
   * Strict
   * Whether to enforce strict schema adherence
   */
  strict?: boolean | null;
}

/** LLMResponseSchema */
export interface LLMResponseSchemaOutput {
  /**
   * Description
   * Description of the schema
   */
  description?: string | null;
  /** The JSON schema object */
  json_schema: JsonSchema;
  /**
   * Name
   * Name of the schema
   */
  name: string;
  /**
   * Strict
   * Whether to enforce strict schema adherence
   */
  strict?: boolean | null;
}

/** LLMTool */
export interface LLMToolInput {
  /**
   * Description
   * Description of what the tool does
   */
  description?: string | null;
  /** The function's parameter schema */
  function_definition?: JsonSchema | null;
  /**
   * Name
   * The name of the tool/function
   */
  name: string;
  /**
   * Strict
   * Whether the function definition should use OpenAI's strict mode
   */
  strict?: boolean | null;
}

/** LLMTool */
export interface LLMToolOutput {
  /**
   * Description
   * Description of what the tool does
   */
  description?: string | null;
  /** The function's parameter schema */
  function_definition?: JsonSchema | null;
  /**
   * Name
   * The name of the tool/function
   */
  name: string;
  /**
   * Strict
   * Whether the function definition should use OpenAI's strict mode
   */
  strict?: boolean | null;
}

export type ListSessionsMetadataApiV1SessionsGetData = SessionListResponse;

export type ListSessionsMetadataApiV1SessionsGetError = HTTPValidationError;

export interface ListSessionsMetadataApiV1SessionsGetParams {
  /**
   * End Time
   * Exclusive end date in ISO8601 string format. Use local time (not UTC).
   * @format date-time
   */
  end_time?: string;
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Start Time
   * Inclusive start date in ISO8601 string format. Use local time (not UTC).
   * @format date-time
   */
  start_time?: string;
  /**
   * Task Ids
   * Task IDs to filter on. At least one is required.
   * @minItems 1
   */
  task_ids: string[];
}

export type ListSpansMetadataApiV1SpansGetData = SpanListResponse;

export type ListSpansMetadataApiV1SpansGetError = HTTPValidationError;

export interface ListSpansMetadataApiV1SpansGetParams {
  /**
   * End Time
   * Exclusive end date in ISO8601 string format. Use local time (not UTC).
   * @format date-time
   */
  end_time?: string;
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Span Types
   * Span types to filter on. Optional.
   */
  span_types?: string[];
  /**
   * Start Time
   * Inclusive start date in ISO8601 string format. Use local time (not UTC).
   * @format date-time
   */
  start_time?: string;
  /**
   * Task Ids
   * Task IDs to filter on. At least one is required.
   * @minItems 1
   */
  task_ids: string[];
}

export type ListTracesMetadataApiV1TracesGetData = TraceListResponse;

export type ListTracesMetadataApiV1TracesGetError = HTTPValidationError;

export interface ListTracesMetadataApiV1TracesGetParams {
  /**
   * End Time
   * Exclusive end date in ISO8601 string format. Use local time (not UTC).
   * @format date-time
   */
  end_time?: string;
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /**
   * Query Relevance Eq
   * Equal to this value.
   * @min 0
   * @max 1
   */
  query_relevance_eq?: number;
  /**
   * Query Relevance Gt
   * Greater than this value.
   * @min 0
   * @max 1
   */
  query_relevance_gt?: number;
  /**
   * Query Relevance Gte
   * Greater than or equal to this value.
   * @min 0
   * @max 1
   */
  query_relevance_gte?: number;
  /**
   * Query Relevance Lt
   * Less than this value.
   * @min 0
   * @max 1
   */
  query_relevance_lt?: number;
  /**
   * Query Relevance Lte
   * Less than or equal to this value.
   * @min 0
   * @max 1
   */
  query_relevance_lte?: number;
  /**
   * Response Relevance Eq
   * Equal to this value.
   * @min 0
   * @max 1
   */
  response_relevance_eq?: number;
  /**
   * Response Relevance Gt
   * Greater than this value.
   * @min 0
   * @max 1
   */
  response_relevance_gt?: number;
  /**
   * Response Relevance Gte
   * Greater than or equal to this value.
   * @min 0
   * @max 1
   */
  response_relevance_gte?: number;
  /**
   * Response Relevance Lt
   * Less than this value.
   * @min 0
   * @max 1
   */
  response_relevance_lt?: number;
  /**
   * Response Relevance Lte
   * Less than or equal to this value.
   * @min 0
   * @max 1
   */
  response_relevance_lte?: number;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Span Types
   * Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
   */
  span_types?: string[];
  /**
   * Start Time
   * Inclusive start date in ISO8601 string format. Use local time (not UTC).
   * @format date-time
   */
  start_time?: string;
  /**
   * Task Ids
   * Task IDs to filter on. At least one is required.
   * @minItems 1
   */
  task_ids: string[];
  /**
   * Tool Name
   * Return only results with this tool name.
   */
  tool_name?: string;
  /** Tool selection evaluation result. */
  tool_selection?: ToolClassEnum;
  /** Tool usage evaluation result. */
  tool_usage?: ToolClassEnum;
  /**
   * Trace Duration Eq
   * Duration exactly equal to this value (seconds).
   * @min 0
   */
  trace_duration_eq?: number;
  /**
   * Trace Duration Gt
   * Duration greater than this value (seconds).
   * @min 0
   */
  trace_duration_gt?: number;
  /**
   * Trace Duration Gte
   * Duration greater than or equal to this value (seconds).
   * @min 0
   */
  trace_duration_gte?: number;
  /**
   * Trace Duration Lt
   * Duration less than this value (seconds).
   * @min 0
   */
  trace_duration_lt?: number;
  /**
   * Trace Duration Lte
   * Duration less than or equal to this value (seconds).
   * @min 0
   */
  trace_duration_lte?: number;
  /**
   * Trace Ids
   * Trace IDs to filter on. Optional.
   */
  trace_ids?: string[];
}

/** LogitBiasItem */
export interface LogitBiasItem {
  /**
   * Bias
   * Bias value between -100 and 100
   * @min -100
   * @max 100
   */
  bias: number;
  /**
   * Token Id
   * Token ID to bias
   */
  token_id: number;
}

/** MessageRole */
export type MessageRole = "system" | "user" | "assistant" | "tool";

/** MetricResponse */
export interface MetricResponse {
  /**
   * Config
   * JSON-serialized configuration for the Metric
   */
  config?: string | null;
  /**
   * Created At
   * Time the Metric was created in unix milliseconds
   * @format date-time
   */
  created_at: string;
  /**
   * Enabled
   * Whether the Metric is enabled
   */
  enabled?: boolean | null;
  /**
   * Id
   * ID of the Metric
   */
  id: string;
  /**
   * Metric Metadata
   * Metadata of the Metric
   */
  metric_metadata: string;
  /**
   * Name
   * Name of the Metric
   */
  name: string;
  /** Type of the Metric */
  type: MetricType;
  /**
   * Updated At
   * Time the Metric was updated in unix milliseconds
   * @format date-time
   */
  updated_at: string;
}

/** MetricResultResponse */
export interface MetricResultResponse {
  /**
   * Completion Tokens
   * Number of completion tokens used
   */
  completion_tokens: number;
  /**
   * Created At
   * Time the result was created
   * @format date-time
   */
  created_at: string;
  /**
   * Details
   * JSON-serialized metric details
   */
  details?: string | null;
  /**
   * Id
   * ID of the metric result
   */
  id: string;
  /**
   * Latency Ms
   * Latency in milliseconds
   */
  latency_ms: number;
  /**
   * Metric Id
   * ID of the metric that generated this result
   */
  metric_id: string;
  /** Type of the metric */
  metric_type: MetricType;
  /**
   * Prompt Tokens
   * Number of prompt tokens used
   */
  prompt_tokens: number;
  /**
   * Span Id
   * ID of the span this result belongs to
   */
  span_id: string;
  /**
   * Updated At
   * Time the result was last updated
   * @format date-time
   */
  updated_at: string;
}

/** MetricType */
export type MetricType = "QueryRelevance" | "ResponseRelevance" | "ToolSelection";

/**
 * NestedSpanWithMetricsResponse
 * Nested span response with children for building span trees
 */
export interface NestedSpanWithMetricsResponse {
  /**
   * Children
   * Child spans nested under this span
   * @default []
   */
  children?: NestedSpanWithMetricsResponse[];
  /** Context */
  context?: Record<string, any>[] | null;
  /**
   * Created At
   * @format date-time
   */
  created_at: string;
  /**
   * End Time
   * @format date-time
   */
  end_time: string;
  /** Id */
  id: string;
  /**
   * Metric Results
   * List of metric results for this span
   * @default []
   */
  metric_results?: MetricResultResponse[];
  /** Parent Span Id */
  parent_span_id?: string | null;
  /** Raw Data */
  raw_data: Record<string, any>;
  /** Response */
  response?: string | null;
  /** Session Id */
  session_id?: string | null;
  /** Span Id */
  span_id: string;
  /** Span Kind */
  span_kind?: string | null;
  /** Span Name */
  span_name?: string | null;
  /**
   * Start Time
   * @format date-time
   */
  start_time: string;
  /**
   * Status Code
   * Status code for the span (Unset, Error, Ok)
   */
  status_code: string;
  /** System Prompt */
  system_prompt?: string | null;
  /** Task Id */
  task_id?: string | null;
  /** Trace Id */
  trace_id: string;
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
  /** User Query */
  user_query?: string | null;
}

/** NewApiKeyRequest */
export interface NewApiKeyRequest {
  /**
   * Description
   * Description of the API key. Optional.
   */
  description?: string | null;
  /**
   * Roles
   * Role that will be assigned to API key. Allowed values: [<APIKeysRolesEnum.DEFAULT_RULE_ADMIN: 'DEFAULT-RULE-ADMIN'>, <APIKeysRolesEnum.TASK_ADMIN: 'TASK-ADMIN'>, <APIKeysRolesEnum.VALIDATION_USER: 'VALIDATION-USER'>, <APIKeysRolesEnum.ORG_AUDITOR: 'ORG-AUDITOR'>, <APIKeysRolesEnum.ORG_ADMIN: 'ORG-ADMIN'>]
   * @default ["VALIDATION-USER"]
   */
  roles?: APIKeysRolesEnum[] | null;
}

/** NewMetricRequest */
export interface NewMetricRequest {
  /** Configuration for the metric. Currently only applies to UserQueryRelevance and ResponseRelevance metric types. */
  config?: RelevanceMetricConfig | null;
  /**
   * Metric Metadata
   * Additional metadata for the metric
   */
  metric_metadata: string;
  /**
   * Name
   * Name of metric
   */
  name: string;
  /** Type of the metric. It can only be one of QueryRelevance, ResponseRelevance, ToolSelection */
  type: MetricType;
}

/** NewRuleRequest */
export interface NewRuleRequest {
  /**
   * Apply To Prompt
   * Boolean value to enable or disable the rule for llm prompt
   */
  apply_to_prompt: boolean;
  /**
   * Apply To Response
   * Boolean value to enable or disable the rule for llm response
   */
  apply_to_response: boolean;
  /**
   * Config
   * Config of the rule
   */
  config?: KeywordsConfig | RegexConfig | ExamplesConfig | ToxicityConfig | PIIConfig | null;
  /**
   * Name
   * Name of the rule
   */
  name: string;
  /**
   * Type
   * Type of the rule. It can only be one of KeywordRule, RegexRule, ModelSensitiveDataRule, ModelHallucinationRule, ModelHallucinationRuleV2, PromptInjectionRule, PIIDataRule
   */
  type: string;
}

/** NewTaskRequest */
export interface NewTaskRequest {
  /**
   * Is Agentic
   * Whether the task is agentic or not.
   * @default false
   */
  is_agentic?: boolean;
  /**
   * Name
   * Name of the task.
   * @minLength 1
   */
  name: string;
}

/**
 * PIIConfig
 * @example {"allow_list":["arthur.ai","Arthur"],"confidence_threshold":"0.5","disabled_pii_entities":["PERSON","URL"]}
 */
export interface PIIConfig {
  /**
   * Allow List
   * Optional. List of strings to pass PII validation.
   */
  allow_list?: string[] | null;
  /**
   * Confidence Threshold
   * Optional. Float (0, 1) indicating the level of tolerable PII to consider the rule passed or failed. Min: 0 (less confident) Max: 1 (very confident). Default: 0
   * @deprecated
   * @default 0
   */
  confidence_threshold?: number | null;
  /**
   * Disabled Pii Entities
   * Optional. List of PII entities to disable. Valid values are: CREDIT_CARD,CRYPTO,DATE_TIME,EMAIL_ADDRESS,IBAN_CODE,IP_ADDRESS,NRP,LOCATION,PERSON,PHONE_NUMBER,MEDICAL_LICENSE,URL,US_BANK_NUMBER,US_DRIVER_LICENSE,US_ITIN,US_PASSPORT,US_SSN
   */
  disabled_pii_entities?: string[] | null;
}

/** PIIDetailsResponse */
export interface PIIDetailsResponse {
  /** Message */
  message?: string | null;
  /** Pii Entities */
  pii_entities: PIIEntitySpanResponse[];
  /** Score */
  score?: boolean | null;
}

/** PIIEntitySpanResponse */
export interface PIIEntitySpanResponse {
  /**
   * Confidence
   * Float value representing the confidence score of a given PII identification.
   */
  confidence?: number | null;
  entity: PIIEntityTypes;
  /**
   * Span
   * The subtext within the input string that was identified as PII.
   */
  span: string;
}

/** PIIEntityTypes */
export type PIIEntityTypes =
  | "CREDIT_CARD"
  | "CRYPTO"
  | "DATE_TIME"
  | "EMAIL_ADDRESS"
  | "IBAN_CODE"
  | "IP_ADDRESS"
  | "NRP"
  | "LOCATION"
  | "PERSON"
  | "PHONE_NUMBER"
  | "MEDICAL_LICENSE"
  | "URL"
  | "US_BANK_NUMBER"
  | "US_DRIVER_LICENSE"
  | "US_ITIN"
  | "US_PASSPORT"
  | "US_SSN";

/** Page[List[ConversationBaseResponse]] */
export interface PageListConversationBaseResponse {
  /** Items */
  items: ConversationBaseResponse[][];
  /**
   * Page
   * @min 1
   */
  page: number;
  /**
   * Pages
   * @min 0
   */
  pages: number;
  /**
   * Size
   * @min 1
   */
  size: number;
  /**
   * Total
   * @min 0
   */
  total: number;
}

/** PaginationSortMethod */
export type PaginationSortMethod = "asc" | "desc";

/** PasswordResetRequest */
export interface PasswordResetRequest {
  /** Password */
  password: string;
}

export type PostChatFeedbackApiChatFeedbackInferenceIdPostData = any;

export type PostChatFeedbackApiChatFeedbackInferenceIdPostError = HTTPValidationError;

export type PostFeedbackApiV2FeedbackInferenceIdPostData = InferenceFeedbackResponse;

export type PostFeedbackApiV2FeedbackInferenceIdPostError = HTTPValidationError;

/** PromptValidationRequest */
export interface PromptValidationRequest {
  /**
   * Conversation Id
   * The unique conversation ID this prompt belongs to. All prompts and responses from this         conversation can later be reconstructed with this ID.
   */
  conversation_id?: string | null;
  /**
   * Model Name
   * The model name and version being used for this prompt (e.g., 'gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'gemini-pro').
   */
  model_name?: string | null;
  /**
   * Prompt
   * Prompt to be validated by GenAI Engine
   */
  prompt: string;
  /**
   * User Id
   * The user ID this prompt belongs to
   */
  user_id?: string | null;
}

/** ProviderEnum */
export type ProviderEnum =
  | "anthropic"
  | "openai"
  | "gemini"
  | "azure"
  | "deepseek"
  | "mistral"
  | "meta_llama"
  | "groq"
  | "bedrock"
  | "sagemaker"
  | "vertex_ai"
  | "huggingface"
  | "cloudflare"
  | "ai21"
  | "baseten"
  | "cohere"
  | "empower"
  | "featherless_ai"
  | "friendliai"
  | "galadriel"
  | "nebius"
  | "nlp_cloud"
  | "novita"
  | "openrouter"
  | "petals"
  | "replicate"
  | "together_ai"
  | "vllm"
  | "watsonx";

export type QueryFeedbackApiV2FeedbackQueryGetData = QueryFeedbackResponse;

export type QueryFeedbackApiV2FeedbackQueryGetError = HTTPValidationError;

export interface QueryFeedbackApiV2FeedbackQueryGetParams {
  /**
   * Conversation Id
   * Conversation ID to filter on
   */
  conversation_id?: string | string[] | null;
  /**
   * End Time
   * Exclusive end date in ISO8601 string format
   */
  end_time?: string | null;
  /**
   * Feedback Id
   * Feedback ID to filter on
   */
  feedback_id?: string | string[] | null;
  /**
   * Feedback User Id
   * User ID of the user giving feedback to filter on (query will perform fuzzy search)
   */
  feedback_user_id?: string | null;
  /**
   * Inference Id
   * Inference ID to filter on
   */
  inference_id?: string | string[] | null;
  /**
   * Inference User Id
   * User ID of the user who created the inferences to filter on (query will perform fuzzy search)
   */
  inference_user_id?: string | null;
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /**
   * Score
   * Score of the feedback. Must be an integer.
   */
  score?: number | number[] | null;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Start Time
   * Inclusive start date in ISO8601 string format
   */
  start_time?: string | null;
  /**
   * Target
   * Target of the feedback. Must be one of ['context', 'response_results', 'prompt_results']
   */
  target?: string | string[] | null;
  /**
   * Task Id
   * Task ID to filter on
   */
  task_id?: string | string[] | null;
}

/**
 * QueryFeedbackResponse
 * @example {"feedback":[{"created_at":"2024-06-06T06:37:46.123-04:00","id":"90f18c69-d793-4913-9bde-a0c7f3643de0","inference_id":"81437d71-9557-4611-981b-9283d1c98643","reason":"good reason","score":"0","target":"context","updated_at":"2024-06-06T06:37:46.123-04:00","user_id":"user_1"},{"created_at":"2023-05-05T05:26:35.987-04:00","id":"248381c2-543b-4de0-98cd-d7511fee6241","inference_id":"bcbc7ca0-4cfc-4f67-9cf8-26cb2291ba33","reason":"some reason","score":"1","target":"response_results","updated_at":"2023-05-05T05:26:35.987-04:00","user_id":"user_2"}],"page":1,"page_size":10,"total_count":2,"total_pages":1}
 */
export interface QueryFeedbackResponse {
  /**
   * Feedback
   * List of inferences matching the search filters. Length is less than or equal to page_size parameter
   */
  feedback: InferenceFeedbackResponse[];
  /**
   * Page
   * The current page number
   */
  page: number;
  /**
   * Page Size
   * The number of feedback items per page
   */
  page_size: number;
  /**
   * Total Count
   * The total number of feedback items matching the query parameters
   */
  total_count: number;
  /**
   * Total Pages
   * The total number of pages
   */
  total_pages: number;
}

export type QueryInferencesApiV2InferencesQueryGetData = QueryInferencesResponse;

export type QueryInferencesApiV2InferencesQueryGetError = HTTPValidationError;

export interface QueryInferencesApiV2InferencesQueryGetParams {
  /**
   * Conversation Id
   * Conversation ID to filter on.
   */
  conversation_id?: string;
  /**
   * End Time
   * Exclusive end date in ISO8601 string format.
   * @format date-time
   */
  end_time?: string;
  /**
   * Include Count
   * Whether to include the total count of matching inferences. Set to False to improve query performance for large datasets. Count will be returned as -1 if set to False.
   * @default true
   */
  include_count?: boolean;
  /**
   * Inference Id
   * Inference ID to filter on.
   */
  inference_id?: string;
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /**
   * Prompt Statuses
   * List of RuleResultEnum to query for at inference prompt stage level. Must be 'Pass' / 'Fail'. Defaults to both.
   * @default []
   */
  prompt_statuses?: RuleResultEnum[];
  /**
   * Response Statuses
   * List of RuleResultEnum to query for at inference response stage level. Must be 'Pass' / 'Fail'. Defaults to both. Inferences missing responses will not be affected by this filter.
   * @default []
   */
  response_statuses?: RuleResultEnum[];
  /**
   * Rule Statuses
   * List of RuleResultEnum to query for. Any inference with any rule status in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_types, will return inferences with rules in the intersection of rule_statuses and rule_types.
   * @default []
   */
  rule_statuses?: RuleResultEnum[];
  /**
   * Rule Types
   * List of RuleType to query for. Any inference that ran any rule in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_statuses, will return inferences with rules in the intersection of rule_types and rule_statuses.
   * @default []
   */
  rule_types?: RuleType[];
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Start Time
   * Inclusive start date in ISO8601 string format.
   * @format date-time
   */
  start_time?: string;
  /**
   * Task Ids
   * Task ID to filter on.
   * @default []
   */
  task_ids?: string[];
  /**
   * Task Name
   * Task name to filter on.
   */
  task_name?: string;
  /**
   * User Id
   * User ID to filter on.
   */
  user_id?: string;
}

/**
 * QueryInferencesResponse
 * @example {"count":1,"inferences":[{"conversation_id":"957df309-c907-4b77-abe5-15dd00c08112","created_at":1723204737120,"id":"957df309-c907-4b77-abe5-15dd00c081f7","inference_feedback":[{"created_at":"2024-08-09T12:08:34.847381","id":"0d602e5c-4ae6-4fc9-a610-68a1d8928ad7","inference_id":"957df309-c907-4b77-abe5-15dd00c081f7","reason":"Perfect answer.","score":100,"target":"context","updated_at":"2024-08-09T12:08:34.847386","user_id":"957df309-2137-4b77-abe5-15dd00c081f8"}],"inference_prompt":{"created_at":1723204737121,"id":"834f7ebd-cd6b-4691-9473-8bc350f8922c","inference_id":"957df309-c907-4b77-abe5-15dd00c081f7","message":"How many stars are in the solar system?","prompt_rule_results":[{"id":"bc599a56-2e31-4cb7-910d-9e5ed6455db2","latency_ms":73,"name":"My_PII_Rule","result":"Pass","rule_type":"PIIDataRule","scope":"default"}],"result":"Pass","tokens":100,"updated_at":1723204737121},"inference_response":{"context":"Solar system contains one star.","created_at":1723204786599,"id":"ec765a75-1479-4938-8e1c-6334b7deb8ce","inference_id":"957df309-c907-4b77-abe5-15dd00c081f7","message":"There is one star in solar system.","response_rule_results":[{"id":"a45267c5-96d9-4de2-a871-debf2c8fdb86","latency_ms":107,"name":"My_another_PII_Rule","result":"Pass","rule_type":"PIIDataRule","scope":"default"},{"details":{"claims":[{"claim":"There is one star in solar system.","order_number":0,"reason":"No hallucination detected!","valid":true}],"message":"All claims were supported by the context!","pii_entities":[],"pii_results":[],"score":true},"id":"92b7b46e-eaf2-4226-82d4-be12ceb3e4b7","latency_ms":700,"name":"My_Hallucination_Rule","result":"Pass","rule_type":"ModelHallucinationRuleV2","scope":"default"}],"result":"Pass","tokens":100,"updated_at":1723204786599},"result":"Pass","task_id":"957df309-c907-4b77-abe5-15dd00c081f8","task_name":"My task name","updated_at":1723204787050,"user_id":"957df309-2137-4b77-abe5-15dd00c081f8"}]}
 */
export interface QueryInferencesResponse {
  /**
   * Count
   * The total number of inferences matching the query parameters
   */
  count: number;
  /**
   * Inferences
   * List of inferences matching the search filters. Length is less than or equal to page_size parameter
   */
  inferences: ExternalInference[];
}

export type QuerySpansByTypeV1SpansQueryGetData = QuerySpansResponse;

export type QuerySpansByTypeV1SpansQueryGetError = HTTPValidationError;

export interface QuerySpansByTypeV1SpansQueryGetParams {
  /**
   * End Time
   * Exclusive end date in ISO8601 string format. Use local time (not UTC).
   * @format date-time
   */
  end_time?: string;
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Span Types
   * Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
   */
  span_types?: string[];
  /**
   * Start Time
   * Inclusive start date in ISO8601 string format. Use local time (not UTC).
   * @format date-time
   */
  start_time?: string;
  /**
   * Task Ids
   * Task IDs to filter on. At least one is required.
   * @minItems 1
   */
  task_ids: string[];
}

/** QuerySpansResponse */
export interface QuerySpansResponse {
  /**
   * Count
   * The total number of spans matching the query parameters
   */
  count: number;
  /**
   * Spans
   * List of spans with metrics matching the search filters
   */
  spans: SpanWithMetricsResponse[];
}

export type QuerySpansV1TracesQueryGetData = QueryTracesWithMetricsResponse;

export type QuerySpansV1TracesQueryGetError = HTTPValidationError;

export interface QuerySpansV1TracesQueryGetParams {
  /**
   * End Time
   * Exclusive end date in ISO8601 string format. Use local time (not UTC).
   * @format date-time
   */
  end_time?: string;
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /**
   * Query Relevance Eq
   * Equal to this value.
   * @min 0
   * @max 1
   */
  query_relevance_eq?: number;
  /**
   * Query Relevance Gt
   * Greater than this value.
   * @min 0
   * @max 1
   */
  query_relevance_gt?: number;
  /**
   * Query Relevance Gte
   * Greater than or equal to this value.
   * @min 0
   * @max 1
   */
  query_relevance_gte?: number;
  /**
   * Query Relevance Lt
   * Less than this value.
   * @min 0
   * @max 1
   */
  query_relevance_lt?: number;
  /**
   * Query Relevance Lte
   * Less than or equal to this value.
   * @min 0
   * @max 1
   */
  query_relevance_lte?: number;
  /**
   * Response Relevance Eq
   * Equal to this value.
   * @min 0
   * @max 1
   */
  response_relevance_eq?: number;
  /**
   * Response Relevance Gt
   * Greater than this value.
   * @min 0
   * @max 1
   */
  response_relevance_gt?: number;
  /**
   * Response Relevance Gte
   * Greater than or equal to this value.
   * @min 0
   * @max 1
   */
  response_relevance_gte?: number;
  /**
   * Response Relevance Lt
   * Less than this value.
   * @min 0
   * @max 1
   */
  response_relevance_lt?: number;
  /**
   * Response Relevance Lte
   * Less than or equal to this value.
   * @min 0
   * @max 1
   */
  response_relevance_lte?: number;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Span Types
   * Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
   */
  span_types?: string[];
  /**
   * Start Time
   * Inclusive start date in ISO8601 string format. Use local time (not UTC).
   * @format date-time
   */
  start_time?: string;
  /**
   * Task Ids
   * Task IDs to filter on. At least one is required.
   * @minItems 1
   */
  task_ids: string[];
  /**
   * Tool Name
   * Return only results with this tool name.
   */
  tool_name?: string;
  /** Tool selection evaluation result. */
  tool_selection?: ToolClassEnum;
  /** Tool usage evaluation result. */
  tool_usage?: ToolClassEnum;
  /**
   * Trace Duration Eq
   * Duration exactly equal to this value (seconds).
   * @min 0
   */
  trace_duration_eq?: number;
  /**
   * Trace Duration Gt
   * Duration greater than this value (seconds).
   * @min 0
   */
  trace_duration_gt?: number;
  /**
   * Trace Duration Gte
   * Duration greater than or equal to this value (seconds).
   * @min 0
   */
  trace_duration_gte?: number;
  /**
   * Trace Duration Lt
   * Duration less than this value (seconds).
   * @min 0
   */
  trace_duration_lt?: number;
  /**
   * Trace Duration Lte
   * Duration less than or equal to this value (seconds).
   * @min 0
   */
  trace_duration_lte?: number;
  /**
   * Trace Ids
   * Trace IDs to filter on. Optional.
   */
  trace_ids?: string[];
}

export type QuerySpansWithMetricsV1TracesMetricsGetData = QueryTracesWithMetricsResponse;

export type QuerySpansWithMetricsV1TracesMetricsGetError = HTTPValidationError;

export interface QuerySpansWithMetricsV1TracesMetricsGetParams {
  /**
   * End Time
   * Exclusive end date in ISO8601 string format. Use local time (not UTC).
   * @format date-time
   */
  end_time?: string;
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /**
   * Query Relevance Eq
   * Equal to this value.
   * @min 0
   * @max 1
   */
  query_relevance_eq?: number;
  /**
   * Query Relevance Gt
   * Greater than this value.
   * @min 0
   * @max 1
   */
  query_relevance_gt?: number;
  /**
   * Query Relevance Gte
   * Greater than or equal to this value.
   * @min 0
   * @max 1
   */
  query_relevance_gte?: number;
  /**
   * Query Relevance Lt
   * Less than this value.
   * @min 0
   * @max 1
   */
  query_relevance_lt?: number;
  /**
   * Query Relevance Lte
   * Less than or equal to this value.
   * @min 0
   * @max 1
   */
  query_relevance_lte?: number;
  /**
   * Response Relevance Eq
   * Equal to this value.
   * @min 0
   * @max 1
   */
  response_relevance_eq?: number;
  /**
   * Response Relevance Gt
   * Greater than this value.
   * @min 0
   * @max 1
   */
  response_relevance_gt?: number;
  /**
   * Response Relevance Gte
   * Greater than or equal to this value.
   * @min 0
   * @max 1
   */
  response_relevance_gte?: number;
  /**
   * Response Relevance Lt
   * Less than this value.
   * @min 0
   * @max 1
   */
  response_relevance_lt?: number;
  /**
   * Response Relevance Lte
   * Less than or equal to this value.
   * @min 0
   * @max 1
   */
  response_relevance_lte?: number;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Span Types
   * Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
   */
  span_types?: string[];
  /**
   * Start Time
   * Inclusive start date in ISO8601 string format. Use local time (not UTC).
   * @format date-time
   */
  start_time?: string;
  /**
   * Task Ids
   * Task IDs to filter on. At least one is required.
   * @minItems 1
   */
  task_ids: string[];
  /**
   * Tool Name
   * Return only results with this tool name.
   */
  tool_name?: string;
  /** Tool selection evaluation result. */
  tool_selection?: ToolClassEnum;
  /** Tool usage evaluation result. */
  tool_usage?: ToolClassEnum;
  /**
   * Trace Duration Eq
   * Duration exactly equal to this value (seconds).
   * @min 0
   */
  trace_duration_eq?: number;
  /**
   * Trace Duration Gt
   * Duration greater than this value (seconds).
   * @min 0
   */
  trace_duration_gt?: number;
  /**
   * Trace Duration Gte
   * Duration greater than or equal to this value (seconds).
   * @min 0
   */
  trace_duration_gte?: number;
  /**
   * Trace Duration Lt
   * Duration less than this value (seconds).
   * @min 0
   */
  trace_duration_lt?: number;
  /**
   * Trace Duration Lte
   * Duration less than or equal to this value (seconds).
   * @min 0
   */
  trace_duration_lte?: number;
  /**
   * Trace Ids
   * Trace IDs to filter on. Optional.
   */
  trace_ids?: string[];
}

/**
 * QueryTracesWithMetricsResponse
 * New response format that groups spans into traces with nested structure
 */
export interface QueryTracesWithMetricsResponse {
  /**
   * Count
   * The total number of spans matching the query parameters
   */
  count: number;
  /**
   * Traces
   * List of traces containing nested spans matching the search filters
   */
  traces: TraceResponse[];
}

/** ReasoningEffortEnum */
export type ReasoningEffortEnum = "none" | "minimal" | "low" | "medium" | "high" | "default";

export type ReceiveTracesApiV1TracesPostData = any;

export type ReceiveTracesApiV1TracesPostError = HTTPValidationError;

/**
 * Body
 * @format binary
 */
export type ReceiveTracesApiV1TracesPostPayload = File;

export type ReceiveTracesV1TracesPostData = any;

export type ReceiveTracesV1TracesPostError = HTTPValidationError;

/**
 * Body
 * @format binary
 */
export type ReceiveTracesV1TracesPostPayload = File;

export type RedirectToTasksApiV2TaskPostData = any;

/**
 * RegexConfig
 * @example {"regex_patterns":["\\d{3}-\\d{2}-\\d{4}","\\d{5}-\\d{6}-\\d{7}"]}
 */
export interface RegexConfig {
  /**
   * Regex Patterns
   * List of Regex patterns to be used for validation. Be sure to encode requests in JSON and account for escape characters.
   */
  regex_patterns: string[];
}

/** RegexDetailsResponse */
export interface RegexDetailsResponse {
  /** Message */
  message?: string | null;
  /**
   * Regex Matches
   * Each string in this list corresponds to a matching span from the input text that matches the configured regex rule.
   * @default []
   */
  regex_matches?: RegexSpanResponse[];
  /** Score */
  score?: boolean | null;
}

/** RegexSpanResponse */
export interface RegexSpanResponse {
  /**
   * Matching Text
   * The subtext within the input string that matched the regex rule.
   */
  matching_text: string;
  /**
   * Pattern
   * Pattern that yielded the match.
   */
  pattern?: string | null;
}

/**
 * RelevanceMetricConfig
 * Configuration for relevance metrics including QueryRelevance and ResponseRelevance
 */
export interface RelevanceMetricConfig {
  /**
   * Relevance Threshold
   * Threshold for determining relevance when not using LLM judge
   */
  relevance_threshold?: number | null;
  /**
   * Use Llm Judge
   * Whether to use LLM as a judge for relevance scoring
   * @default true
   */
  use_llm_judge?: boolean;
}

export type ResetUserPasswordUsersUserIdResetPasswordPostData = any;

export type ResetUserPasswordUsersUserIdResetPasswordPostError = HTTPValidationError;

/** ResponseValidationRequest */
export interface ResponseValidationRequest {
  /**
   * Context
   * Optional data provided as context for the validation.
   */
  context?: string | null;
  /**
   * Model Name
   * The model name and version being used for this response (e.g., 'gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'gemini-pro').
   */
  model_name?: string | null;
  /**
   * Response
   * LLM Response to be validated by GenAI Engine
   */
  response: string;
}

/** RuleResponse */
export interface RuleResponse {
  /**
   * Apply To Prompt
   * Rule applies to prompt
   */
  apply_to_prompt: boolean;
  /**
   * Apply To Response
   * Rule applies to response
   */
  apply_to_response: boolean;
  /**
   * Config
   * Config of the rule
   */
  config?: KeywordsConfig | RegexConfig | ExamplesConfig | ToxicityConfig | PIIConfig | null;
  /**
   * Created At
   * Time the rule was created in unix milliseconds
   */
  created_at: number;
  /**
   * Enabled
   * Rule is enabled for the task
   */
  enabled?: boolean | null;
  /**
   * Id
   * ID of the Rule
   */
  id: string;
  /**
   * Name
   * Name of the Rule
   */
  name: string;
  /** Scope of the rule. The rule can be set at default level or task level. */
  scope: RuleScope;
  /** Type of Rule */
  type: RuleType;
  /**
   * Updated At
   * Time the rule was updated in unix milliseconds
   */
  updated_at: number;
}

/** RuleResultEnum */
export type RuleResultEnum =
  | "Pass"
  | "Fail"
  | "Skipped"
  | "Unavailable"
  | "Partially Unavailable"
  | "Model Not Available";

/** RuleScope */
export type RuleScope = "default" | "task";

/** RuleType */
export type RuleType =
  | "KeywordRule"
  | "ModelHallucinationRuleV2"
  | "ModelSensitiveDataRule"
  | "PIIDataRule"
  | "PromptInjectionRule"
  | "RegexRule"
  | "ToxicityRule";

export type RunAgenticPromptApiV1CompletionsPostData = AgenticPromptRunResponse;

export type RunAgenticPromptApiV1CompletionsPostError = HTTPValidationError;

export type RunSavedAgenticPromptApiV1TaskTaskIdPromptPromptNameVersionsPromptVersionCompletionsPostData =
  AgenticPromptRunResponse;

export type RunSavedAgenticPromptApiV1TaskTaskIdPromptPromptNameVersionsPromptVersionCompletionsPostError =
  HTTPValidationError;

export type SaveAgenticPromptApiV1TaskIdAgenticPromptsPromptNamePutData = any;

export type SaveAgenticPromptApiV1TaskIdAgenticPromptsPromptNamePutError = HTTPValidationError;

export type SearchRulesApiV2RulesSearchPostData = SearchRulesResponse;

export type SearchRulesApiV2RulesSearchPostError = HTTPValidationError;

export interface SearchRulesApiV2RulesSearchPostParams {
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
}

/** SearchRulesRequest */
export interface SearchRulesRequest {
  /**
   * Prompt Enabled
   * Include or exclude prompt-enabled rules.
   */
  prompt_enabled?: boolean | null;
  /**
   * Response Enabled
   * Include or exclude response-enabled rules.
   */
  response_enabled?: boolean | null;
  /**
   * Rule Ids
   * List of rule IDs to search for.
   */
  rule_ids?: string[] | null;
  /**
   * Rule Scopes
   * List of rule scopes to search for.
   */
  rule_scopes?: RuleScope[] | null;
  /**
   * Rule Types
   * List of rule types to search for.
   */
  rule_types?: RuleType[] | null;
}

/** SearchRulesResponse */
export interface SearchRulesResponse {
  /**
   * Count
   * The total number of rules matching the parameters
   */
  count: number;
  /**
   * Rules
   * List of rules matching the search filters. Length is less than or equal to page_size parameter
   */
  rules: RuleResponse[];
}

export type SearchTasksApiV2TasksSearchPostData = SearchTasksResponse;

export type SearchTasksApiV2TasksSearchPostError = HTTPValidationError;

export interface SearchTasksApiV2TasksSearchPostParams {
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
}

/** SearchTasksRequest */
export interface SearchTasksRequest {
  /**
   * Is Agentic
   * Filter tasks by agentic status. If not provided, returns both agentic and non-agentic tasks.
   */
  is_agentic?: boolean | null;
  /**
   * Task Ids
   * List of tasks to query for.
   */
  task_ids?: string[] | null;
  /**
   * Task Name
   * Task name substring search string.
   */
  task_name?: string | null;
}

/** SearchTasksResponse */
export interface SearchTasksResponse {
  /**
   * Count
   * The total number of tasks matching the parameters
   */
  count: number;
  /**
   * Tasks
   * List of tasks matching the search filters. Length is less than or equal to page_size parameter
   */
  tasks: TaskResponse[];
}

/** Response Search Users Users Get */
export type SearchUsersUsersGetData = UserResponse[];

export type SearchUsersUsersGetError = HTTPValidationError;

export interface SearchUsersUsersGetParams {
  /**
   * Page
   * Page number
   * @default 0
   */
  page?: number;
  /**
   * Page Size
   * Page size. Default is 10. Must be greater than 0 and less than 5000.
   * @default 10
   */
  page_size?: number;
  /**
   * Search String
   * Substring to match on. Will search first name, last name, email.
   */
  search_string?: string | null;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
}

/**
 * SessionListResponse
 * Response for session list endpoint
 */
export interface SessionListResponse {
  /**
   * Count
   * Total number of sessions matching filters
   */
  count: number;
  /**
   * Sessions
   * List of session metadata
   */
  sessions: SessionMetadataResponse[];
}

/**
 * SessionMetadataResponse
 * Session summary metadata
 */
export interface SessionMetadataResponse {
  /**
   * Duration Ms
   * Total session duration in milliseconds
   */
  duration_ms: number;
  /**
   * Earliest Start Time
   * Start time of earliest trace
   * @format date-time
   */
  earliest_start_time: string;
  /**
   * Latest End Time
   * End time of latest trace
   * @format date-time
   */
  latest_end_time: string;
  /**
   * Session Id
   * Session identifier
   */
  session_id: string;
  /**
   * Span Count
   * Total number of spans in this session
   */
  span_count: number;
  /**
   * Task Id
   * Task ID this session belongs to
   */
  task_id: string;
  /**
   * Trace Count
   * Number of traces in this session
   */
  trace_count: number;
  /**
   * Trace Ids
   * List of trace IDs in this session
   */
  trace_ids: string[];
}

/**
 * SessionTracesResponse
 * Response for session traces endpoint
 */
export interface SessionTracesResponse {
  /**
   * Count
   * Number of traces in this session
   */
  count: number;
  /**
   * Session Id
   * Session identifier
   */
  session_id: string;
  /**
   * Traces
   * List of full trace trees
   */
  traces: TraceResponse[];
}

/**
 * SpanListResponse
 * Response for span list endpoint
 */
export interface SpanListResponse {
  /**
   * Count
   * Total number of spans matching filters
   */
  count: number;
  /**
   * Spans
   * List of span metadata
   */
  spans: SpanMetadataResponse[];
}

/**
 * SpanMetadataResponse
 * Lightweight span metadata for list operations
 */
export interface SpanMetadataResponse {
  /**
   * Created At
   * When the span was created
   * @format date-time
   */
  created_at: string;
  /**
   * Duration Ms
   * Span duration in milliseconds
   */
  duration_ms: number;
  /**
   * End Time
   * Span end time
   * @format date-time
   */
  end_time: string;
  /**
   * Id
   * Internal database ID
   */
  id: string;
  /**
   * Parent Span Id
   * Parent span ID
   */
  parent_span_id?: string | null;
  /**
   * Session Id
   * Session ID if available
   */
  session_id?: string | null;
  /**
   * Span Id
   * OpenTelemetry span ID
   */
  span_id: string;
  /**
   * Span Kind
   * Type of span (LLM, TOOL, etc.)
   */
  span_kind?: string | null;
  /**
   * Span Name
   * Human-readable span name
   */
  span_name?: string | null;
  /**
   * Start Time
   * Span start time
   * @format date-time
   */
  start_time: string;
  /**
   * Status Code
   * Status code (Unset, Error, Ok)
   */
  status_code: string;
  /**
   * Task Id
   * Task ID this span belongs to
   */
  task_id?: string | null;
  /**
   * Trace Id
   * ID of the parent trace
   */
  trace_id: string;
  /**
   * Updated At
   * When the span was updated
   * @format date-time
   */
  updated_at: string;
}

/** SpanWithMetricsResponse */
export interface SpanWithMetricsResponse {
  /** Context */
  context?: Record<string, any>[] | null;
  /**
   * Created At
   * @format date-time
   */
  created_at: string;
  /**
   * End Time
   * @format date-time
   */
  end_time: string;
  /** Id */
  id: string;
  /**
   * Metric Results
   * List of metric results for this span
   * @default []
   */
  metric_results?: MetricResultResponse[];
  /** Parent Span Id */
  parent_span_id?: string | null;
  /** Raw Data */
  raw_data: Record<string, any>;
  /** Response */
  response?: string | null;
  /** Session Id */
  session_id?: string | null;
  /** Span Id */
  span_id: string;
  /** Span Kind */
  span_kind?: string | null;
  /** Span Name */
  span_name?: string | null;
  /**
   * Start Time
   * @format date-time
   */
  start_time: string;
  /**
   * Status Code
   * Status code for the span (Unset, Error, Ok)
   */
  status_code: string;
  /** System Prompt */
  system_prompt?: string | null;
  /** Task Id */
  task_id?: string | null;
  /** Trace Id */
  trace_id: string;
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
  /** User Query */
  user_query?: string | null;
}

/** StreamOptions */
export interface StreamOptions {
  /**
   * Include Usage
   * Whether to include usage information in the stream
   */
  include_usage?: boolean | null;
}

/** TaskResponse */
export interface TaskResponse {
  /**
   * Created At
   * Time the task was created in unix milliseconds
   */
  created_at: number;
  /**
   * Id
   *  ID of the task
   */
  id: string;
  /**
   * Is Agentic
   * Whether the task is agentic or not
   */
  is_agentic?: boolean | null;
  /**
   * Metrics
   * List of all the metrics for the task.
   */
  metrics?: MetricResponse[] | null;
  /**
   * Name
   * Name of the task
   */
  name: string;
  /**
   * Rules
   * List of all the rules for the task.
   */
  rules: RuleResponse[];
  /**
   * Updated At
   * Time the task was created in unix milliseconds
   */
  updated_at: number;
}

/** TokenUsageCount */
export interface TokenUsageCount {
  /**
   * Completion
   * Number of Completion tokens incurred by Arthur rules. This field is deprecated and will be removed in the future. Use eval_completion instead.
   * @deprecated
   */
  completion: number;
  /**
   * Eval Completion
   * Number of Completion tokens incurred by Arthur rules.
   */
  eval_completion: number;
  /**
   * Eval Prompt
   * Number of Prompt tokens incurred by Arthur rules.
   */
  eval_prompt: number;
  /**
   * Inference
   * Number of inference tokens sent to Arthur.
   */
  inference: number;
  /**
   * Prompt
   * Number of Prompt tokens incurred by Arthur rules. This field is deprecated and will be removed in the future. Use eval_prompt instead.
   * @deprecated
   */
  prompt: number;
  /**
   * User Input
   * Number of user input tokens sent to Arthur. This field is deprecated and will be removed in the future. Use inference instead.
   * @deprecated
   */
  user_input: number;
}

/** TokenUsageResponse */
export interface TokenUsageResponse {
  count: TokenUsageCount;
  /** Rule Type */
  rule_type?: string | null;
  /** Task Id */
  task_id?: string | null;
}

/** TokenUsageScope */
export type TokenUsageScope = "rule_type" | "task";

/** ToolCallFunction */
export interface ToolCallFunction {
  /**
   * Arguments
   * JSON string of function arguments
   */
  arguments: string;
  /**
   * Name
   * Name of the function to call
   */
  name: string;
}

/** ToolCall */
export interface ToolCallInput {
  /** Function details */
  function: ToolCallFunction;
  /**
   * Id
   * Unique identifier for the tool call
   */
  id: string;
}

/** ToolCall */
export interface ToolCallOutput {
  /** Function details */
  function: ToolCallFunction;
  /**
   * Id
   * Unique identifier for the tool call
   */
  id: string;
  /** Type */
  readonly type: string;
}

/** ToolChoiceEnum */
export type ToolChoiceEnum = "auto" | "none" | "required";

/** ToolClassEnum */
export type ToolClassEnum = 0 | 1 | 2;

/**
 * ToxicityConfig
 * @example {"threshold":0.5}
 */
export interface ToxicityConfig {
  /**
   * Threshold
   * Optional. Float (0, 1) indicating the level of tolerable toxicity to consider the rule passed or failed. Min: 0 (no toxic language) Max: 1 (very toxic language). Default: 0.5
   * @default 0.5
   */
  threshold?: number;
}

/** ToxicityDetailsResponse */
export interface ToxicityDetailsResponse {
  /** Message */
  message?: string | null;
  /** Score */
  score?: boolean | null;
  /** Toxicity Score */
  toxicity_score?: number | null;
  toxicity_violation_type: ToxicityViolationType;
}

/** ToxicityViolationType */
export type ToxicityViolationType = "benign" | "harmful_request" | "toxic_content" | "profanity" | "unknown";

/**
 * TraceListResponse
 * Response for trace list endpoint
 */
export interface TraceListResponse {
  /**
   * Count
   * Total number of traces matching filters
   */
  count: number;
  /**
   * Traces
   * List of trace metadata
   */
  traces: TraceMetadataResponse[];
}

/**
 * TraceMetadataResponse
 * Lightweight trace metadata for list operations
 */
export interface TraceMetadataResponse {
  /**
   * Created At
   * When the trace was first created
   * @format date-time
   */
  created_at: string;
  /**
   * Duration Ms
   * Total trace duration in milliseconds
   */
  duration_ms: number;
  /**
   * End Time
   * End time of the latest span
   * @format date-time
   */
  end_time: string;
  /**
   * Session Id
   * Session ID if available
   */
  session_id?: string | null;
  /**
   * Span Count
   * Number of spans in this trace
   */
  span_count: number;
  /**
   * Start Time
   * Start time of the earliest span
   * @format date-time
   */
  start_time: string;
  /**
   * Task Id
   * Task ID this trace belongs to
   */
  task_id: string;
  /**
   * Trace Id
   * ID of the trace
   */
  trace_id: string;
  /**
   * Updated At
   * When the trace was last updated
   * @format date-time
   */
  updated_at: string;
}

/**
 * TraceResponse
 * Response model for a single trace containing nested spans
 */
export interface TraceResponse {
  /**
   * End Time
   * End time of the latest span in this trace
   * @format date-time
   */
  end_time: string;
  /**
   * Root Spans
   * Root spans (spans with no parent) in this trace, with children nested
   * @default []
   */
  root_spans?: NestedSpanWithMetricsResponse[];
  /**
   * Start Time
   * Start time of the earliest span in this trace
   * @format date-time
   */
  start_time: string;
  /**
   * Trace Id
   * ID of the trace
   */
  trace_id: string;
}

export type UpdateDefaultTaskApiChatDefaultTaskPutData = ChatDefaultTaskResponse;

export type UpdateDefaultTaskApiChatDefaultTaskPutError = HTTPValidationError;

/** UpdateMetricRequest */
export interface UpdateMetricRequest {
  /**
   * Enabled
   * Boolean value to enable or disable the metric.
   */
  enabled: boolean;
}

/** UpdateRuleRequest */
export interface UpdateRuleRequest {
  /**
   * Enabled
   * Boolean value to enable or disable the rule.
   */
  enabled: boolean;
}

export type UpdateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatchData = any;

export type UpdateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatchError = HTTPValidationError;

export type UpdateTaskRulesApiV2TasksTaskIdRulesRuleIdPatchData = TaskResponse;

export type UpdateTaskRulesApiV2TasksTaskIdRulesRuleIdPatchError = HTTPValidationError;

export type UploadEmbeddingsFileApiChatFilesPostData = FileUploadResult;

export type UploadEmbeddingsFileApiChatFilesPostError = HTTPValidationError;

export interface UploadEmbeddingsFileApiChatFilesPostParams {
  /**
   * Is Global
   * @default false
   */
  is_global?: boolean;
}

/** UserPermissionAction */
export type UserPermissionAction = "create" | "read";

/** UserPermissionResource */
export type UserPermissionResource = "prompts" | "responses" | "rules" | "tasks";

/** UserResponse */
export interface UserResponse {
  /** Email */
  email: string;
  /** First Name */
  first_name?: string | null;
  /** Id */
  id: string;
  /** Last Name */
  last_name?: string | null;
  /** Roles */
  roles: AuthUserRole[];
}

export type ValidatePromptEndpointApiV2TasksTaskIdValidatePromptPostData = ValidationResult;

export type ValidatePromptEndpointApiV2TasksTaskIdValidatePromptPostError = HTTPError | HTTPValidationError;

export type ValidateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPostData = ValidationResult;

export type ValidateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPostError =
  | HTTPError
  | HTTPValidationError;

/** ValidationError */
export interface ValidationError {
  /** Location */
  loc: (string | number)[];
  /** Message */
  msg: string;
  /** Error Type */
  type: string;
}

/**
 * ValidationResult
 * @example {"inference_id":"4dd1fae1-34b9-4aec-8abe-fe7bf12af31d","rule_results":[{"id":"90f18c69-d793-4913-9bde-a0c7f3643de0","name":"PII Check","result":"Pass"},{"id":"946c4a44-b367-4229-84d4-1a8e461cb132","name":"Sensitive Data Check","result":"Pass"}]}
 */
export interface ValidationResult {
  /**
   * Inference Id
   * ID of the inference
   */
  inference_id?: string | null;
  /**
   * Model Name
   * The model name and version used for this validation (e.g., 'gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', 'gemini-pro').
   */
  model_name?: string | null;
  /**
   * Rule Results
   * List of rule results
   */
  rule_results?: ExternalRuleResult[] | null;
  /**
   * User Id
   * The user ID this prompt belongs to
   */
  user_id?: string | null;
}

/** VariableTemplateValue */
export interface VariableTemplateValue {
  /**
   * Name
   * Name of the variable
   */
  name: string;
  /**
   * Value
   * Value of the variable
   */
  value: string;
}

import type { AxiosInstance, AxiosRequestConfig, AxiosResponse, HeadersDefaults, ResponseType } from "axios";
import axios from "axios";

export type QueryParamsType = Record<string | number, any>;

export interface FullRequestParams extends Omit<AxiosRequestConfig, "data" | "params" | "url" | "responseType"> {
  /** set parameter to `true` for call `securityWorker` for this request */
  secure?: boolean;
  /** request path */
  path: string;
  /** content type of request body */
  type?: ContentType;
  /** query params */
  query?: QueryParamsType;
  /** format of response (i.e. response.json() -> format: "json") */
  format?: ResponseType;
  /** request body */
  body?: unknown;
}

export type RequestParams = Omit<FullRequestParams, "body" | "method" | "query" | "path">;

export interface ApiConfig<SecurityDataType = unknown> extends Omit<AxiosRequestConfig, "data" | "cancelToken"> {
  securityWorker?: (
    securityData: SecurityDataType | null,
  ) => Promise<AxiosRequestConfig | void> | AxiosRequestConfig | void;
  secure?: boolean;
  format?: ResponseType;
}

export enum ContentType {
  Json = "application/json",
  FormData = "multipart/form-data",
  UrlEncoded = "application/x-www-form-urlencoded",
  Text = "text/plain",
}

export class HttpClient<SecurityDataType = unknown> {
  public instance: AxiosInstance;
  private securityData: SecurityDataType | null = null;
  private securityWorker?: ApiConfig<SecurityDataType>["securityWorker"];
  private secure?: boolean;
  private format?: ResponseType;

  constructor({ securityWorker, secure, format, ...axiosConfig }: ApiConfig<SecurityDataType> = {}) {
    this.instance = axios.create({ ...axiosConfig, baseURL: axiosConfig.baseURL || "" });
    this.secure = secure;
    this.format = format;
    this.securityWorker = securityWorker;
  }

  public setSecurityData = (data: SecurityDataType | null) => {
    this.securityData = data;
  };

  protected mergeRequestParams(params1: AxiosRequestConfig, params2?: AxiosRequestConfig): AxiosRequestConfig {
    const method = params1.method || (params2 && params2.method);

    return {
      ...this.instance.defaults,
      ...params1,
      ...(params2 || {}),
      headers: {
        ...((method && this.instance.defaults.headers[method.toLowerCase() as keyof HeadersDefaults]) || {}),
        ...(params1.headers || {}),
        ...((params2 && params2.headers) || {}),
      },
    };
  }

  protected stringifyFormItem(formItem: unknown) {
    if (typeof formItem === "object" && formItem !== null) {
      return JSON.stringify(formItem);
    } else {
      return `${formItem}`;
    }
  }

  protected createFormData(input: Record<string, unknown>): FormData {
    if (input instanceof FormData) {
      return input;
    }
    return Object.keys(input || {}).reduce((formData, key) => {
      const property = input[key];
      const propertyContent: any[] = property instanceof Array ? property : [property];

      for (const formItem of propertyContent) {
        const isFileType = formItem instanceof Blob || formItem instanceof File;
        formData.append(key, isFileType ? formItem : this.stringifyFormItem(formItem));
      }

      return formData;
    }, new FormData());
  }

  public request = async <T = any, _E = any>({
    secure,
    path,
    type,
    query,
    format,
    body,
    ...params
  }: FullRequestParams): Promise<AxiosResponse<T>> => {
    const secureParams =
      ((typeof secure === "boolean" ? secure : this.secure) &&
        this.securityWorker &&
        (await this.securityWorker(this.securityData))) ||
      {};
    const requestParams = this.mergeRequestParams(params, secureParams);
    const responseFormat = format || this.format || undefined;

    if (type === ContentType.FormData && body && body !== null && typeof body === "object") {
      body = this.createFormData(body as Record<string, unknown>);
    }

    if (type === ContentType.Text && body && body !== null && typeof body !== "string") {
      body = JSON.stringify(body);
    }

    return this.instance.request({
      ...requestParams,
      headers: {
        ...(requestParams.headers || {}),
        ...(type ? { "Content-Type": type } : {}),
      },
      params: query,
      responseType: responseFormat,
      data: body,
      url: path,
    });
  };
}

/**
 * @title Arthur GenAI Engine
 * @version 2.1.94
 */
export class Api<SecurityDataType extends unknown> extends HttpClient<SecurityDataType> {
  api = {
    /**
     * @description Archive existing default rule.
     *
     * @tags Rules
     * @name ArchiveDefaultRuleApiV2DefaultRulesRuleIdDelete
     * @summary Archive Default Rule
     * @request DELETE:/api/v2/default_rules/{rule_id}
     * @secure
     */
    archiveDefaultRuleApiV2DefaultRulesRuleIdDelete: (ruleId: string, params: RequestParams = {}) =>
      this.request<
        ArchiveDefaultRuleApiV2DefaultRulesRuleIdDeleteData,
        ArchiveDefaultRuleApiV2DefaultRulesRuleIdDeleteError
      >({
        path: `/api/v2/default_rules/${ruleId}`,
        method: "DELETE",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Archive task. Also archives all task-scoped rules. Associated default rules are unaffected.
     *
     * @tags Tasks
     * @name ArchiveTaskApiV2TasksTaskIdDelete
     * @summary Archive Task
     * @request DELETE:/api/v2/tasks/{task_id}
     * @secure
     */
    archiveTaskApiV2TasksTaskIdDelete: (taskId: string, params: RequestParams = {}) =>
      this.request<ArchiveTaskApiV2TasksTaskIdDeleteData, ArchiveTaskApiV2TasksTaskIdDeleteError>({
        path: `/api/v2/tasks/${taskId}`,
        method: "DELETE",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Archive a task metric.
     *
     * @tags Tasks
     * @name ArchiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDelete
     * @summary Archive Task Metric
     * @request DELETE:/api/v2/tasks/{task_id}/metrics/{metric_id}
     * @secure
     */
    archiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDelete: (
      taskId: string,
      metricId: string,
      params: RequestParams = {},
    ) =>
      this.request<
        ArchiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDeleteData,
        ArchiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDeleteError
      >({
        path: `/api/v2/tasks/${taskId}/metrics/${metricId}`,
        method: "DELETE",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Archive an existing rule for this task.
     *
     * @tags Tasks
     * @name ArchiveTaskRuleApiV2TasksTaskIdRulesRuleIdDelete
     * @summary Archive Task Rule
     * @request DELETE:/api/v2/tasks/{task_id}/rules/{rule_id}
     * @secure
     */
    archiveTaskRuleApiV2TasksTaskIdRulesRuleIdDelete: (taskId: string, ruleId: string, params: RequestParams = {}) =>
      this.request<
        ArchiveTaskRuleApiV2TasksTaskIdRulesRuleIdDeleteData,
        ArchiveTaskRuleApiV2TasksTaskIdRulesRuleIdDeleteError
      >({
        path: `/api/v2/tasks/${taskId}/rules/${ruleId}`,
        method: "DELETE",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Chat request for Arthur Chat
     *
     * @tags Chat
     * @name ChatRequest
     * @summary Chat
     * @request POST:/api/chat/
     */
    chatRequest: (data: ChatRequest, params: RequestParams = {}) =>
      this.request<ChatRequestData, ChatRequestError>({
        path: `/api/chat/`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Get all traces in a session and compute missing metrics. Returns list of full trace trees with computed metrics.
     *
     * @tags Sessions
     * @name ComputeSessionMetricsApiV1SessionsSessionIdMetricsGet
     * @summary Compute Missing Session Metrics
     * @request GET:/api/v1/sessions/{session_id}/metrics
     * @secure
     */
    computeSessionMetricsApiV1SessionsSessionIdMetricsGet: (
      { sessionId, ...query }: ComputeSessionMetricsApiV1SessionsSessionIdMetricsGetParams,
      params: RequestParams = {},
    ) =>
      this.request<
        ComputeSessionMetricsApiV1SessionsSessionIdMetricsGetData,
        ComputeSessionMetricsApiV1SessionsSessionIdMetricsGetError
      >({
        path: `/api/v1/sessions/${sessionId}/metrics`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Compute all missing metrics for a single span on-demand. Returns span with computed metrics.
     *
     * @tags Spans
     * @name ComputeSpanMetricsApiV1SpansSpanIdMetricsGet
     * @summary Compute Missing Span Metrics
     * @request GET:/api/v1/spans/{span_id}/metrics
     * @secure
     */
    computeSpanMetricsApiV1SpansSpanIdMetricsGet: (spanId: string, params: RequestParams = {}) =>
      this.request<ComputeSpanMetricsApiV1SpansSpanIdMetricsGetData, ComputeSpanMetricsApiV1SpansSpanIdMetricsGetError>(
        {
          path: `/api/v1/spans/${spanId}/metrics`,
          method: "GET",
          secure: true,
          format: "json",
          ...params,
        },
      ),

    /**
     * @description Compute all missing metrics for trace spans on-demand. Returns full trace tree with computed metrics.
     *
     * @tags Traces
     * @name ComputeTraceMetricsApiV1TracesTraceIdMetricsGet
     * @summary Compute Missing Trace Metrics
     * @request GET:/api/v1/traces/{trace_id}/metrics
     * @secure
     */
    computeTraceMetricsApiV1TracesTraceIdMetricsGet: (traceId: string, params: RequestParams = {}) =>
      this.request<
        ComputeTraceMetricsApiV1TracesTraceIdMetricsGetData,
        ComputeTraceMetricsApiV1TracesTraceIdMetricsGetError
      >({
        path: `/api/v1/traces/${traceId}/metrics`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Create a default rule. Default rules are applied universally across existing tasks, subsequently created new tasks, and any non-task related requests. Once a rule is created, it is immutable. Available rules are 'KeywordRule', 'ModelHallucinationRuleV2', 'ModelSensitiveDataRule', 'PIIDataRule', 'PromptInjectionRule', 'RegexRule', 'ToxicityRule'. Note: The rules are cached by the validation endpoints for 60 seconds.
     *
     * @tags Rules
     * @name CreateDefaultRuleApiV2DefaultRulesPost
     * @summary Create Default Rule
     * @request POST:/api/v2/default_rules
     * @secure
     */
    createDefaultRuleApiV2DefaultRulesPost: (data: NewRuleRequest, params: RequestParams = {}) =>
      this.request<CreateDefaultRuleApiV2DefaultRulesPostData, CreateDefaultRuleApiV2DefaultRulesPostError>({
        path: `/api/v2/default_rules`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Register a new task. When a new task is created, all existing default rules will be auto-applied for this new task. Optionally specify if the task is agentic.
     *
     * @tags Tasks
     * @name CreateTaskApiV2TasksPost
     * @summary Create Task
     * @request POST:/api/v2/tasks
     * @secure
     */
    createTaskApiV2TasksPost: (data: NewTaskRequest, params: RequestParams = {}) =>
      this.request<CreateTaskApiV2TasksPostData, CreateTaskApiV2TasksPostError>({
        path: `/api/v2/tasks`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Create metrics for a task. Only agentic tasks can have metrics.
     *
     * @tags Tasks
     * @name CreateTaskMetricApiV2TasksTaskIdMetricsPost
     * @summary Create Task Metric
     * @request POST:/api/v2/tasks/{task_id}/metrics
     * @secure
     */
    createTaskMetricApiV2TasksTaskIdMetricsPost: (taskId: string, data: NewMetricRequest, params: RequestParams = {}) =>
      this.request<CreateTaskMetricApiV2TasksTaskIdMetricsPostData, CreateTaskMetricApiV2TasksTaskIdMetricsPostError>({
        path: `/api/v2/tasks/${taskId}/metrics`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Create a rule to be applied only to this task. Available rule types are KeywordRule, ModelHallucinationRuleV2, ModelSensitiveDataRule, PIIDataRule, PromptInjectionRule, RegexRule, ToxicityRule.Note: The rules are cached by the validation endpoints for 60 seconds.
     *
     * @tags Tasks
     * @name CreateTaskRuleApiV2TasksTaskIdRulesPost
     * @summary Create Task Rule
     * @request POST:/api/v2/tasks/{task_id}/rules
     * @secure
     */
    createTaskRuleApiV2TasksTaskIdRulesPost: (taskId: string, data: NewRuleRequest, params: RequestParams = {}) =>
      this.request<CreateTaskRuleApiV2TasksTaskIdRulesPostData, CreateTaskRuleApiV2TasksTaskIdRulesPostError>({
        path: `/api/v2/tasks/${taskId}/rules`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description [Deprecated] Validate a non-task related prompt based on the configured default rules.
     *
     * @tags Default Validation
     * @name DefaultValidatePromptApiV2ValidatePromptPost
     * @summary Default Validate Prompt
     * @request POST:/api/v2/validate_prompt
     * @deprecated
     * @secure
     */
    defaultValidatePromptApiV2ValidatePromptPost: (data: PromptValidationRequest, params: RequestParams = {}) =>
      this.request<DefaultValidatePromptApiV2ValidatePromptPostData, DefaultValidatePromptApiV2ValidatePromptPostError>(
        {
          path: `/api/v2/validate_prompt`,
          method: "POST",
          body: data,
          secure: true,
          type: ContentType.Json,
          format: "json",
          ...params,
        },
      ),

    /**
     * @description [Deprecated] Validate a non-task related generated response based on the configured default rules. Inference ID corresponds to the previously validated associated prompt’s inference ID. Must provide context if a Hallucination Rule is an enabled default rule.
     *
     * @tags Default Validation
     * @name DefaultValidateResponseApiV2ValidateResponseInferenceIdPost
     * @summary Default Validate Response
     * @request POST:/api/v2/validate_response/{inference_id}
     * @deprecated
     * @secure
     */
    defaultValidateResponseApiV2ValidateResponseInferenceIdPost: (
      inferenceId: string,
      data: ResponseValidationRequest,
      params: RequestParams = {},
    ) =>
      this.request<
        DefaultValidateResponseApiV2ValidateResponseInferenceIdPostData,
        DefaultValidateResponseApiV2ValidateResponseInferenceIdPostError
      >({
        path: `/api/v2/validate_response/${inferenceId}`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Deletes an entire agentic prompt
     *
     * @tags AgenticPrompt
     * @name DeleteAgenticPromptApiV1TaskIdAgenticPromptsPromptNameDelete
     * @summary Delete an agentic prompt
     * @request DELETE:/api/v1/{task_id}/agentic_prompts/{prompt_name}
     * @secure
     */
    deleteAgenticPromptApiV1TaskIdAgenticPromptsPromptNameDelete: (
      promptName: string,
      taskId: string,
      params: RequestParams = {},
    ) =>
      this.request<
        DeleteAgenticPromptApiV1TaskIdAgenticPromptsPromptNameDeleteData,
        DeleteAgenticPromptApiV1TaskIdAgenticPromptsPromptNameDeleteError
      >({
        path: `/api/v1/${taskId}/agentic_prompts/${promptName}`,
        method: "DELETE",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Deletes a specific version of an agentic prompt
     *
     * @tags AgenticPrompt
     * @name DeleteAgenticPromptVersionApiV1TaskIdAgenticPromptsPromptNameVersionsPromptVersionDelete
     * @summary Delete an agentic prompt
     * @request DELETE:/api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}
     * @secure
     */
    deleteAgenticPromptVersionApiV1TaskIdAgenticPromptsPromptNameVersionsPromptVersionDelete: (
      promptName: string,
      promptVersion: string,
      taskId: string,
      params: RequestParams = {},
    ) =>
      this.request<
        DeleteAgenticPromptVersionApiV1TaskIdAgenticPromptsPromptNameVersionsPromptVersionDeleteData,
        DeleteAgenticPromptVersionApiV1TaskIdAgenticPromptsPromptNameVersionsPromptVersionDeleteError
      >({
        path: `/api/v1/${taskId}/agentic_prompts/${promptName}/versions/${promptVersion}`,
        method: "DELETE",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Remove a file by ID. This action cannot be undone.
     *
     * @tags Chat
     * @name DeleteFileApiChatFilesFileIdDelete
     * @summary Delete File
     * @request DELETE:/api/chat/files/{file_id}
     */
    deleteFileApiChatFilesFileIdDelete: (fileId: string, params: RequestParams = {}) =>
      this.request<DeleteFileApiChatFilesFileIdDeleteData, DeleteFileApiChatFilesFileIdDeleteError>({
        path: `/api/chat/files/${fileId}`,
        method: "DELETE",
        format: "json",
        ...params,
      }),

    /**
     * @description Get an agentic prompt by name and version
     *
     * @tags AgenticPrompt
     * @name GetAgenticPromptApiV1TaskIdAgenticPromptsPromptNameVersionsPromptVersionGet
     * @summary Get an agentic prompt
     * @request GET:/api/v1/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}
     * @secure
     */
    getAgenticPromptApiV1TaskIdAgenticPromptsPromptNameVersionsPromptVersionGet: (
      promptName: string,
      promptVersion: string,
      taskId: string,
      params: RequestParams = {},
    ) =>
      this.request<
        GetAgenticPromptApiV1TaskIdAgenticPromptsPromptNameVersionsPromptVersionGetData,
        GetAgenticPromptApiV1TaskIdAgenticPromptsPromptNameVersionsPromptVersionGetError
      >({
        path: `/api/v1/${taskId}/agentic_prompts/${promptName}/versions/${promptVersion}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get all agentic prompts for a given task
     *
     * @tags AgenticPrompt
     * @name GetAllAgenticPromptsApiV1TaskIdAgenticPromptsGet
     * @summary Get all agentic prompts
     * @request GET:/api/v1/{task_id}/agentic_prompts
     * @secure
     */
    getAllAgenticPromptsApiV1TaskIdAgenticPromptsGet: (taskId: string, params: RequestParams = {}) =>
      this.request<
        GetAllAgenticPromptsApiV1TaskIdAgenticPromptsGetData,
        GetAllAgenticPromptsApiV1TaskIdAgenticPromptsGetError
      >({
        path: `/api/v1/${taskId}/agentic_prompts`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description List all versions of an agentic prompt
     *
     * @tags AgenticPrompt
     * @name GetAllAgenticPromptVersionsApiV1TaskIdAgenticPromptsPromptNameVersionsGet
     * @summary List all versions of an agentic prompt
     * @request GET:/api/v1/{task_id}/agentic_prompts/{prompt_name}/versions
     * @secure
     */
    getAllAgenticPromptVersionsApiV1TaskIdAgenticPromptsPromptNameVersionsGet: (
      promptName: string,
      taskId: string,
      params: RequestParams = {},
    ) =>
      this.request<
        GetAllAgenticPromptVersionsApiV1TaskIdAgenticPromptsPromptNameVersionsGetData,
        GetAllAgenticPromptVersionsApiV1TaskIdAgenticPromptsPromptNameVersionsGetError
      >({
        path: `/api/v1/${taskId}/agentic_prompts/${promptName}/versions`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description [Deprecated] Use /tasks/search endpoint. This endpoint will be removed in a future release.
     *
     * @tags Tasks
     * @name GetAllTasksApiV2TasksGet
     * @summary Get All Tasks
     * @request GET:/api/v2/tasks
     * @deprecated
     * @secure
     */
    getAllTasksApiV2TasksGet: (params: RequestParams = {}) =>
      this.request<GetAllTasksApiV2TasksGetData, any>({
        path: `/api/v2/tasks`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get list of conversation IDs.
     *
     * @tags Chat
     * @name GetConversationsApiChatConversationsGet
     * @summary Get Conversations
     * @request GET:/api/chat/conversations
     */
    getConversationsApiChatConversationsGet: (
      query: GetConversationsApiChatConversationsGetParams,
      params: RequestParams = {},
    ) =>
      this.request<GetConversationsApiChatConversationsGetData, GetConversationsApiChatConversationsGetError>({
        path: `/api/chat/conversations`,
        method: "GET",
        query: query,
        format: "json",
        ...params,
      }),

    /**
     * @description Get default rules.
     *
     * @tags Rules
     * @name GetDefaultRulesApiV2DefaultRulesGet
     * @summary Get Default Rules
     * @request GET:/api/v2/default_rules
     * @secure
     */
    getDefaultRulesApiV2DefaultRulesGet: (params: RequestParams = {}) =>
      this.request<GetDefaultRulesApiV2DefaultRulesGetData, any>({
        path: `/api/v2/default_rules`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get the default task for Arthur Chat.
     *
     * @tags Chat
     * @name GetDefaultTaskApiChatDefaultTaskGet
     * @summary Get Default Task
     * @request GET:/api/chat/default_task
     */
    getDefaultTaskApiChatDefaultTaskGet: (params: RequestParams = {}) =>
      this.request<GetDefaultTaskApiChatDefaultTaskGetData, any>({
        path: `/api/chat/default_task`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description List uploaded files. Only files that are global or owned by the caller are returned.
     *
     * @tags Chat
     * @name GetFilesApiChatFilesGet
     * @summary Get Files
     * @request GET:/api/chat/files
     */
    getFilesApiChatFilesGet: (params: RequestParams = {}) =>
      this.request<GetFilesApiChatFilesGetData, any>({
        path: `/api/chat/files`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Get document context used for a past inference ID.
     *
     * @tags Chat
     * @name GetInferenceDocumentContextApiChatContextInferenceIdGet
     * @summary Get Inference Document Context
     * @request GET:/api/chat/context/{inference_id}
     */
    getInferenceDocumentContextApiChatContextInferenceIdGet: (inferenceId: string, params: RequestParams = {}) =>
      this.request<
        GetInferenceDocumentContextApiChatContextInferenceIdGetData,
        GetInferenceDocumentContextApiChatContextInferenceIdGetError
      >({
        path: `/api/chat/context/${inferenceId}`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Get all traces in a session. Returns list of full trace trees with existing metrics (no computation).
     *
     * @tags Sessions
     * @name GetSessionTracesApiV1SessionsSessionIdGet
     * @summary Get Session Traces
     * @request GET:/api/v1/sessions/{session_id}
     * @secure
     */
    getSessionTracesApiV1SessionsSessionIdGet: (
      { sessionId, ...query }: GetSessionTracesApiV1SessionsSessionIdGetParams,
      params: RequestParams = {},
    ) =>
      this.request<GetSessionTracesApiV1SessionsSessionIdGetData, GetSessionTracesApiV1SessionsSessionIdGetError>({
        path: `/api/v1/sessions/${sessionId}`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get single span with existing metrics (no computation). Returns full span object with any existing metrics.
     *
     * @tags Spans
     * @name GetSpanByIdApiV1SpansSpanIdGet
     * @summary Get Single Span
     * @request GET:/api/v1/spans/{span_id}
     * @secure
     */
    getSpanByIdApiV1SpansSpanIdGet: (spanId: string, params: RequestParams = {}) =>
      this.request<GetSpanByIdApiV1SpansSpanIdGetData, GetSpanByIdApiV1SpansSpanIdGetError>({
        path: `/api/v1/spans/${spanId}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get tasks.
     *
     * @tags Tasks
     * @name GetTaskApiV2TasksTaskIdGet
     * @summary Get Task
     * @request GET:/api/v2/tasks/{task_id}
     * @secure
     */
    getTaskApiV2TasksTaskIdGet: (taskId: string, params: RequestParams = {}) =>
      this.request<GetTaskApiV2TasksTaskIdGetData, GetTaskApiV2TasksTaskIdGetError>({
        path: `/api/v2/tasks/${taskId}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get token usage.
     *
     * @tags Usage
     * @name GetTokenUsageApiV2UsageTokensGet
     * @summary Get Token Usage
     * @request GET:/api/v2/usage/tokens
     * @secure
     */
    getTokenUsageApiV2UsageTokensGet: (query: GetTokenUsageApiV2UsageTokensGetParams, params: RequestParams = {}) =>
      this.request<GetTokenUsageApiV2UsageTokensGetData, GetTokenUsageApiV2UsageTokensGetError>({
        path: `/api/v2/usage/tokens`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get complete trace tree with existing metrics (no computation). Returns full trace structure with spans.
     *
     * @tags Traces
     * @name GetTraceByIdApiV1TracesTraceIdGet
     * @summary Get Single Trace
     * @request GET:/api/v1/traces/{trace_id}
     * @secure
     */
    getTraceByIdApiV1TracesTraceIdGet: (traceId: string, params: RequestParams = {}) =>
      this.request<GetTraceByIdApiV1TracesTraceIdGetData, GetTraceByIdApiV1TracesTraceIdGetError>({
        path: `/api/v1/traces/${traceId}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get session metadata with pagination and filtering. Returns aggregated session information.
     *
     * @tags Sessions
     * @name ListSessionsMetadataApiV1SessionsGet
     * @summary List Session Metadata
     * @request GET:/api/v1/sessions
     * @secure
     */
    listSessionsMetadataApiV1SessionsGet: (
      query: ListSessionsMetadataApiV1SessionsGetParams,
      params: RequestParams = {},
    ) =>
      this.request<ListSessionsMetadataApiV1SessionsGetData, ListSessionsMetadataApiV1SessionsGetError>({
        path: `/api/v1/sessions`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get lightweight span metadata for browsing/filtering operations. Returns metadata only without raw data or metrics for fast performance.
     *
     * @tags Spans
     * @name ListSpansMetadataApiV1SpansGet
     * @summary List Span Metadata
     * @request GET:/api/v1/spans
     * @secure
     */
    listSpansMetadataApiV1SpansGet: (query: ListSpansMetadataApiV1SpansGetParams, params: RequestParams = {}) =>
      this.request<ListSpansMetadataApiV1SpansGetData, ListSpansMetadataApiV1SpansGetError>({
        path: `/api/v1/spans`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get lightweight trace metadata for browsing/filtering operations. Returns metadata only without spans or metrics for fast performance.
     *
     * @tags Traces
     * @name ListTracesMetadataApiV1TracesGet
     * @summary List Trace Metadata
     * @request GET:/api/v1/traces
     * @secure
     */
    listTracesMetadataApiV1TracesGet: (query: ListTracesMetadataApiV1TracesGetParams, params: RequestParams = {}) =>
      this.request<ListTracesMetadataApiV1TracesGetData, ListTracesMetadataApiV1TracesGetError>({
        path: `/api/v1/traces`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Post feedback for Arthur Chat.
     *
     * @tags Chat, Chat
     * @name PostChatFeedbackApiChatFeedbackInferenceIdPost
     * @summary Post Chat Feedback
     * @request POST:/api/chat/feedback/{inference_id}
     */
    postChatFeedbackApiChatFeedbackInferenceIdPost: (
      inferenceId: string,
      data: FeedbackRequest,
      params: RequestParams = {},
    ) =>
      this.request<
        PostChatFeedbackApiChatFeedbackInferenceIdPostData,
        PostChatFeedbackApiChatFeedbackInferenceIdPostError
      >({
        path: `/api/chat/feedback/${inferenceId}`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Post feedback for LLM Application.
     *
     * @tags Feedback
     * @name PostFeedbackApiV2FeedbackInferenceIdPost
     * @summary Post Feedback
     * @request POST:/api/v2/feedback/{inference_id}
     * @secure
     */
    postFeedbackApiV2FeedbackInferenceIdPost: (
      inferenceId: string,
      data: FeedbackRequest,
      params: RequestParams = {},
    ) =>
      this.request<PostFeedbackApiV2FeedbackInferenceIdPostData, PostFeedbackApiV2FeedbackInferenceIdPostError>({
        path: `/api/v2/feedback/${inferenceId}`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Paginated feedback querying. See parameters for available filters. Includes feedback from archived tasks and rules.
     *
     * @tags Feedback
     * @name QueryFeedbackApiV2FeedbackQueryGet
     * @summary Query Feedback
     * @request GET:/api/v2/feedback/query
     * @secure
     */
    queryFeedbackApiV2FeedbackQueryGet: (query: QueryFeedbackApiV2FeedbackQueryGetParams, params: RequestParams = {}) =>
      this.request<QueryFeedbackApiV2FeedbackQueryGetData, QueryFeedbackApiV2FeedbackQueryGetError>({
        path: `/api/v2/feedback/query`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Paginated inference querying. See parameters for available filters. Includes inferences from archived tasks and rules.
     *
     * @tags Inferences
     * @name QueryInferencesApiV2InferencesQueryGet
     * @summary Query Inferences
     * @request GET:/api/v2/inferences/query
     * @secure
     */
    queryInferencesApiV2InferencesQueryGet: (
      query: QueryInferencesApiV2InferencesQueryGetParams,
      params: RequestParams = {},
    ) =>
      this.request<QueryInferencesApiV2InferencesQueryGetData, QueryInferencesApiV2InferencesQueryGetError>({
        path: `/api/v2/inferences/query`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Receiver for OpenInference trace standard.
     *
     * @tags Traces
     * @name ReceiveTracesApiV1TracesPost
     * @summary Receive Traces
     * @request POST:/api/v1/traces
     * @secure
     */
    receiveTracesApiV1TracesPost: (data: ReceiveTracesApiV1TracesPostPayload, params: RequestParams = {}) =>
      this.request<ReceiveTracesApiV1TracesPostData, ReceiveTracesApiV1TracesPostError>({
        path: `/api/v1/traces`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Redirect to /tasks endpoint.
     *
     * @tags Tasks
     * @name RedirectToTasksApiV2TaskPost
     * @summary Redirect To Tasks
     * @request POST:/api/v2/task
     */
    redirectToTasksApiV2TaskPost: (params: RequestParams = {}) =>
      this.request<RedirectToTasksApiV2TaskPostData, any>({
        path: `/api/v2/task`,
        method: "POST",
        format: "json",
        ...params,
      }),

    /**
     * @description Run an agentic prompt
     *
     * @tags AgenticPrompt
     * @name RunAgenticPromptApiV1CompletionsPost
     * @summary Run an agentic prompt
     * @request POST:/api/v1/completions
     * @secure
     */
    runAgenticPromptApiV1CompletionsPost: (data: AgenticPromptUnsavedRunConfig, params: RequestParams = {}) =>
      this.request<RunAgenticPromptApiV1CompletionsPostData, RunAgenticPromptApiV1CompletionsPostError>({
        path: `/api/v1/completions`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Run a specific version of an existing agentic prompt
     *
     * @tags AgenticPrompt
     * @name RunSavedAgenticPromptApiV1TaskTaskIdPromptPromptNameVersionsPromptVersionCompletionsPost
     * @summary Run a specific version of an agentic prompt
     * @request POST:/api/v1/task/{task_id}/prompt/{prompt_name}/versions/{prompt_version}/completions
     * @secure
     */
    runSavedAgenticPromptApiV1TaskTaskIdPromptPromptNameVersionsPromptVersionCompletionsPost: (
      promptName: string,
      promptVersion: string,
      taskId: string,
      data: AgenticPromptRunConfig,
      params: RequestParams = {},
    ) =>
      this.request<
        RunSavedAgenticPromptApiV1TaskTaskIdPromptPromptNameVersionsPromptVersionCompletionsPostData,
        RunSavedAgenticPromptApiV1TaskTaskIdPromptPromptNameVersionsPromptVersionCompletionsPostError
      >({
        path: `/api/v1/task/${taskId}/prompt/${promptName}/versions/${promptVersion}/completions`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Save an agentic prompt to the database
     *
     * @tags AgenticPrompt
     * @name SaveAgenticPromptApiV1TaskIdAgenticPromptsPromptNamePut
     * @summary Save an agentic prompt
     * @request PUT:/api/v1/{task_id}/agentic_prompts/{prompt_name}
     * @secure
     */
    saveAgenticPromptApiV1TaskIdAgenticPromptsPromptNamePut: (
      promptName: string,
      taskId: string,
      data: AgenticPromptBaseConfig,
      params: RequestParams = {},
    ) =>
      this.request<
        SaveAgenticPromptApiV1TaskIdAgenticPromptsPromptNamePutData,
        SaveAgenticPromptApiV1TaskIdAgenticPromptsPromptNamePutError
      >({
        path: `/api/v1/${taskId}/agentic_prompts/${promptName}`,
        method: "PUT",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Search default and/or task rules.
     *
     * @tags Rules
     * @name SearchRulesApiV2RulesSearchPost
     * @summary Search Rules
     * @request POST:/api/v2/rules/search
     * @secure
     */
    searchRulesApiV2RulesSearchPost: (
      query: SearchRulesApiV2RulesSearchPostParams,
      data: SearchRulesRequest,
      params: RequestParams = {},
    ) =>
      this.request<SearchRulesApiV2RulesSearchPostData, SearchRulesApiV2RulesSearchPostError>({
        path: `/api/v2/rules/search`,
        method: "POST",
        query: query,
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Search tasks. Can filter by task IDs, task name substring, and agentic status.
     *
     * @tags Tasks
     * @name SearchTasksApiV2TasksSearchPost
     * @summary Search Tasks
     * @request POST:/api/v2/tasks/search
     * @secure
     */
    searchTasksApiV2TasksSearchPost: (
      query: SearchTasksApiV2TasksSearchPostParams,
      data: SearchTasksRequest,
      params: RequestParams = {},
    ) =>
      this.request<SearchTasksApiV2TasksSearchPostData, SearchTasksApiV2TasksSearchPostError>({
        path: `/api/v2/tasks/search`,
        method: "POST",
        query: query,
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Update the default task for Arthur Chat.
     *
     * @tags Chat
     * @name UpdateDefaultTaskApiChatDefaultTaskPut
     * @summary Update Default Task
     * @request PUT:/api/chat/default_task
     */
    updateDefaultTaskApiChatDefaultTaskPut: (data: ChatDefaultTaskRequest, params: RequestParams = {}) =>
      this.request<UpdateDefaultTaskApiChatDefaultTaskPutData, UpdateDefaultTaskApiChatDefaultTaskPutError>({
        path: `/api/chat/default_task`,
        method: "PUT",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Update a task metric.
     *
     * @tags Tasks
     * @name UpdateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatch
     * @summary Update Task Metric
     * @request PATCH:/api/v2/tasks/{task_id}/metrics/{metric_id}
     * @secure
     */
    updateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatch: (
      taskId: string,
      metricId: string,
      data: UpdateMetricRequest,
      params: RequestParams = {},
    ) =>
      this.request<
        UpdateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatchData,
        UpdateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatchError
      >({
        path: `/api/v2/tasks/${taskId}/metrics/${metricId}`,
        method: "PATCH",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Enable or disable an existing rule for this task including the default rules.
     *
     * @tags Tasks
     * @name UpdateTaskRulesApiV2TasksTaskIdRulesRuleIdPatch
     * @summary Update Task Rules
     * @request PATCH:/api/v2/tasks/{task_id}/rules/{rule_id}
     * @secure
     */
    updateTaskRulesApiV2TasksTaskIdRulesRuleIdPatch: (
      taskId: string,
      ruleId: string,
      data: UpdateRuleRequest,
      params: RequestParams = {},
    ) =>
      this.request<
        UpdateTaskRulesApiV2TasksTaskIdRulesRuleIdPatchData,
        UpdateTaskRulesApiV2TasksTaskIdRulesRuleIdPatchError
      >({
        path: `/api/v2/tasks/${taskId}/rules/${ruleId}`,
        method: "PATCH",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Upload files via form-data. Only PDF, CSV, TXT types accepted.
     *
     * @tags Chat
     * @name UploadEmbeddingsFileApiChatFilesPost
     * @summary Upload Embeddings File
     * @request POST:/api/chat/files
     */
    uploadEmbeddingsFileApiChatFilesPost: (
      query: UploadEmbeddingsFileApiChatFilesPostParams,
      data: BodyUploadEmbeddingsFileApiChatFilesPost,
      params: RequestParams = {},
    ) =>
      this.request<UploadEmbeddingsFileApiChatFilesPostData, UploadEmbeddingsFileApiChatFilesPostError>({
        path: `/api/chat/files`,
        method: "POST",
        query: query,
        body: data,
        type: ContentType.FormData,
        format: "json",
        ...params,
      }),

    /**
     * @description Validate a prompt based on the configured rules for this task. Note: Rules related to specific tasks are cached for 60 seconds.
     *
     * @tags Task Based Validation
     * @name ValidatePromptEndpointApiV2TasksTaskIdValidatePromptPost
     * @summary Validate Prompt Endpoint
     * @request POST:/api/v2/tasks/{task_id}/validate_prompt
     * @secure
     */
    validatePromptEndpointApiV2TasksTaskIdValidatePromptPost: (
      taskId: string,
      data: PromptValidationRequest,
      params: RequestParams = {},
    ) =>
      this.request<
        ValidatePromptEndpointApiV2TasksTaskIdValidatePromptPostData,
        ValidatePromptEndpointApiV2TasksTaskIdValidatePromptPostError
      >({
        path: `/api/v2/tasks/${taskId}/validate_prompt`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Validate a response based on the configured rules for this task. Inference ID corresponds to the previously validated associated prompt’s inference id. Must provide context if a Hallucination Rule is an enabled task rule. Note: Rules related to specific tasks are cached for 60 seconds.
     *
     * @tags Task Based Validation
     * @name ValidateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPost
     * @summary Validate Response Endpoint
     * @request POST:/api/v2/tasks/{task_id}/validate_response/{inference_id}
     * @secure
     */
    validateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPost: (
      inferenceId: string,
      taskId: string,
      data: ResponseValidationRequest,
      params: RequestParams = {},
    ) =>
      this.request<
        ValidateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPostData,
        ValidateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPostError
      >({
        path: `/api/v2/tasks/${taskId}/validate_response/${inferenceId}`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),
  };
  auth = {
    /**
     * @description Generates a new API key. Up to 1000 active keys can exist at the same time by default. Contact your system administrator if you need more. Allowed roles are: DEFAULT-RULE-ADMIN, TASK-ADMIN, VALIDATION-USER, ORG-AUDITOR, ORG-ADMIN.
     *
     * @tags API Keys
     * @name CreateApiKeyAuthApiKeysPost
     * @summary Create Api Key
     * @request POST:/auth/api_keys/
     * @secure
     */
    createApiKeyAuthApiKeysPost: (data: NewApiKeyRequest, params: RequestParams = {}) =>
      this.request<CreateApiKeyAuthApiKeysPostData, CreateApiKeyAuthApiKeysPostError>({
        path: `/auth/api_keys/`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags API Keys
     * @name DeactivateApiKeyAuthApiKeysDeactivateApiKeyIdDelete
     * @summary Deactivate Api Key
     * @request DELETE:/auth/api_keys/deactivate/{api_key_id}
     * @secure
     */
    deactivateApiKeyAuthApiKeysDeactivateApiKeyIdDelete: (apiKeyId: string, params: RequestParams = {}) =>
      this.request<
        DeactivateApiKeyAuthApiKeysDeactivateApiKeyIdDeleteData,
        DeactivateApiKeyAuthApiKeysDeactivateApiKeyIdDeleteError
      >({
        path: `/auth/api_keys/deactivate/${apiKeyId}`,
        method: "DELETE",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags API Keys
     * @name GetAllActiveApiKeysAuthApiKeysGet
     * @summary Get All Active Api Keys
     * @request GET:/auth/api_keys/
     * @secure
     */
    getAllActiveApiKeysAuthApiKeysGet: (params: RequestParams = {}) =>
      this.request<GetAllActiveApiKeysAuthApiKeysGetData, any>({
        path: `/auth/api_keys/`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @tags API Keys
     * @name GetApiKeyAuthApiKeysApiKeyIdGet
     * @summary Get Api Key
     * @request GET:/auth/api_keys/{api_key_id}
     * @secure
     */
    getApiKeyAuthApiKeysApiKeyIdGet: (apiKeyId: string, params: RequestParams = {}) =>
      this.request<GetApiKeyAuthApiKeysApiKeyIdGetData, GetApiKeyAuthApiKeysApiKeyIdGetError>({
        path: `/auth/api_keys/${apiKeyId}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),
  };
  v1 = {
    /**
     * @description Compute metrics for a single span. Validates that the span is an LLM span.
     *
     * @tags Spans
     * @name ComputeSpanMetricsV1SpanSpanIdMetricsGet
     * @summary Compute Metrics for Span
     * @request GET:/v1/span/{span_id}/metrics
     * @deprecated
     * @secure
     */
    computeSpanMetricsV1SpanSpanIdMetricsGet: (spanId: string, params: RequestParams = {}) =>
      this.request<ComputeSpanMetricsV1SpanSpanIdMetricsGetData, ComputeSpanMetricsV1SpanSpanIdMetricsGetError>({
        path: `/v1/span/${spanId}/metrics`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Query spans filtered by span type. Task IDs are required. Returns spans with any existing metrics but does not compute new ones.
     *
     * @tags Spans
     * @name QuerySpansByTypeV1SpansQueryGet
     * @summary Query Spans By Type
     * @request GET:/v1/spans/query
     * @deprecated
     * @secure
     */
    querySpansByTypeV1SpansQueryGet: (query: QuerySpansByTypeV1SpansQueryGetParams, params: RequestParams = {}) =>
      this.request<QuerySpansByTypeV1SpansQueryGetData, QuerySpansByTypeV1SpansQueryGetError>({
        path: `/v1/spans/query`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Query traces with comprehensive filtering. Returns traces containing spans that match the filters, not just the spans themselves.
     *
     * @tags Spans
     * @name QuerySpansV1TracesQueryGet
     * @summary Query Traces
     * @request GET:/v1/traces/query
     * @deprecated
     * @secure
     */
    querySpansV1TracesQueryGet: (query: QuerySpansV1TracesQueryGetParams, params: RequestParams = {}) =>
      this.request<QuerySpansV1TracesQueryGetData, QuerySpansV1TracesQueryGetError>({
        path: `/v1/traces/query`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Query traces with comprehensive filtering and compute metrics. Returns traces containing spans that match the filters with computed metrics.
     *
     * @tags Spans
     * @name QuerySpansWithMetricsV1TracesMetricsGet
     * @summary Compute Missing Metrics and Query Traces
     * @request GET:/v1/traces/metrics/
     * @deprecated
     * @secure
     */
    querySpansWithMetricsV1TracesMetricsGet: (
      query: QuerySpansWithMetricsV1TracesMetricsGetParams,
      params: RequestParams = {},
    ) =>
      this.request<QuerySpansWithMetricsV1TracesMetricsGetData, QuerySpansWithMetricsV1TracesMetricsGetError>({
        path: `/v1/traces/metrics/`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Receiver for OpenInference trace standard.
     *
     * @tags Traces
     * @name ReceiveTracesV1TracesPost
     * @summary Receive Traces
     * @request POST:/v1/traces
     * @deprecated
     * @secure
     */
    receiveTracesV1TracesPost: (data: ReceiveTracesV1TracesPostPayload, params: RequestParams = {}) =>
      this.request<ReceiveTracesV1TracesPostData, ReceiveTracesV1TracesPostError>({
        path: `/v1/traces`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),
  };
  users = {
    /**
     * @description Checks if the current user has the requested permission. Returns 200 status code for authorized or 403 if not.
     *
     * @tags User Management
     * @name CheckUserPermissionUsersPermissionsCheckGet
     * @summary Check User Permission
     * @request GET:/users/permissions/check
     * @secure
     */
    checkUserPermissionUsersPermissionsCheckGet: (
      query: CheckUserPermissionUsersPermissionsCheckGetParams,
      params: RequestParams = {},
    ) =>
      this.request<CheckUserPermissionUsersPermissionsCheckGetData, CheckUserPermissionUsersPermissionsCheckGetError>({
        path: `/users/permissions/check`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Creates a new user with specific roles. The available roles are TASK-ADMIN and CHAT-USER. The 'temporary' field is for indicating if the user password needs to be reset at the first login.
     *
     * @tags User Management
     * @name CreateUserUsersPost
     * @summary Create User
     * @request POST:/users
     * @secure
     */
    createUserUsersPost: (data: CreateUserRequest, params: RequestParams = {}) =>
      this.request<CreateUserUsersPostData, CreateUserUsersPostError>({
        path: `/users`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Delete a user.
     *
     * @tags User Management
     * @name DeleteUserUsersUserIdDelete
     * @summary Delete User
     * @request DELETE:/users/{user_id}
     * @secure
     */
    deleteUserUsersUserIdDelete: (userId: string, params: RequestParams = {}) =>
      this.request<DeleteUserUsersUserIdDeleteData, DeleteUserUsersUserIdDeleteError>({
        path: `/users/${userId}`,
        method: "DELETE",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Reset password for user.
     *
     * @tags User Management
     * @name ResetUserPasswordUsersUserIdResetPasswordPost
     * @summary Reset User Password
     * @request POST:/users/{user_id}/reset_password
     */
    resetUserPasswordUsersUserIdResetPasswordPost: (
      userId: string,
      data: PasswordResetRequest,
      params: RequestParams = {},
    ) =>
      this.request<
        ResetUserPasswordUsersUserIdResetPasswordPostData,
        ResetUserPasswordUsersUserIdResetPasswordPostError
      >({
        path: `/users/${userId}/reset_password`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Fetch users.
     *
     * @tags User Management
     * @name SearchUsersUsersGet
     * @summary Search Users
     * @request GET:/users
     * @secure
     */
    searchUsersUsersGet: (query: SearchUsersUsersGetParams, params: RequestParams = {}) =>
      this.request<SearchUsersUsersGetData, SearchUsersUsersGetError>({
        path: `/users`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),
  };
}
