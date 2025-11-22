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

export type AddTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPutData = AgenticPrompt;

export type AddTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPutError = HTTPValidationError;

export type AddTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPutData = LLMEval;

export type AddTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPutError = HTTPValidationError;

/** AgenticAnnotation */
export interface AgenticAnnotation {
  /**
   * Annotation Description
   * Description of the annotation
   */
  annotation_description?: string | null;
  /**
   * Annotation Score
   * Binary score for whether a traces has been liked or disliked (0 = disliked, 1 = liked)
   * @min 0
   * @max 1
   */
  annotation_score: number;
  /**
   * Created At
   * When the annotation was created
   * @format date-time
   */
  created_at?: string;
  /**
   * Id
   * Unique identifier for the annotation
   * @format uuid
   */
  id: string;
  /**
   * Trace Id
   * Trace ID this annotation belongs to
   */
  trace_id: string;
  /**
   * Updated At
   * When the annotation was last updated
   * @format date-time
   */
  updated_at?: string;
}

/** AgenticAnnotationRequest */
export interface AgenticAnnotationRequest {
  /**
   * Annotation Description
   * Description of the annotation
   */
  annotation_description?: string | null;
  /**
   * Annotation Score
   * Binary score for whether a traces has been liked or disliked (0 = disliked, 1 = liked)
   * @min 0
   * @max 1
   */
  annotation_score: number;
}

/** AgenticAnnotationResponse */
export interface AgenticAnnotationResponse {
  /**
   * Annotation Description
   * Description of the annotation.
   */
  annotation_description?: string | null;
  /**
   * Annotation Score
   * Binary score for whether a traces has been liked or disliked (0 = disliked, 1 = liked).
   */
  annotation_score?: number | null;
}

/** AgenticPrompt */
export interface AgenticPrompt {
  /** LLM configurations for this prompt (e.g. temperature, max_tokens, etc.) */
  config?: LLMConfigSettings | null;
  /**
   * Created At
   * Timestamp when the prompt was created.
   * @format date-time
   */
  created_at: string;
  /**
   * Deleted At
   * Time that this prompt was deleted
   */
  deleted_at?: string | null;
  /**
   * Messages
   * List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])
   */
  messages: OpenAIMessageOutput[];
  /**
   * Model Name
   * Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')
   */
  model_name: string;
  /** Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure') */
  model_provider: ModelProvider;
  /**
   * Name
   * Name of the agentic prompt
   */
  name: string;
  /**
   * Tags
   * List of tags for this agentic prompt version
   */
  tags?: string[];
  /**
   * Tools
   * Available tools/functions for the model to call, in OpenAI function calling format
   */
  tools?: LLMToolOutput[] | null;
  /**
   * Variables
   * List of variable names for the agentic prompt
   */
  variables?: string[];
  /**
   * Version
   * Version of the agentic prompt
   * @default 1
   */
  version?: number;
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

/** AgenticPromptVersionListResponse */
export interface AgenticPromptVersionListResponse {
  /**
   * Count
   * Total number of prompts matching filters
   */
  count: number;
  /**
   * Versions
   * List of prompt version metadata
   */
  versions: AgenticPromptVersionResponse[];
}

/** AgenticPromptVersionResponse */
export interface AgenticPromptVersionResponse {
  /**
   * Created At
   * Timestamp when the llm eval version was created
   * @format date-time
   */
  created_at: string;
  /**
   * Deleted At
   * Timestamp when the llm eval version was deleted (None if not deleted)
   */
  deleted_at: string | null;
  /**
   * Model Name
   * Model name chosen for this version of the llm eval
   */
  model_name: string;
  /** Model provider chosen for this version of the llm eval */
  model_provider: ModelProvider;
  /**
   * Num Messages
   * Number of messages in the prompt
   */
  num_messages: number;
  /**
   * Num Tools
   * Number of tools in the prompt
   */
  num_tools: number;
  /**
   * Tags
   * List of tags for the llm asset
   */
  tags?: string[];
  /**
   * Version
   * Version number of the llm eval
   */
  version: number;
}

export type AnnotateTraceApiV1TracesTraceIdAnnotationsPostData = AgenticAnnotation;

export type AnnotateTraceApiV1TracesTraceIdAnnotationsPostError = HTTPValidationError;

/** AnthropicThinkingParam */
export interface AnthropicThinkingParam {
  /** Budget Tokens */
  budget_tokens?: number;
  /** Type */
  type?: "enabled";
}

/** ApiKeyRagAuthenticationConfigRequest */
export interface ApiKeyRagAuthenticationConfigRequest {
  /**
   * Api Key
   * API key to use for authentication.
   * @format password
   */
  api_key: string;
  /**
   * Authentication Method
   * @default "api_key"
   */
  authentication_method?: "api_key";
  /**
   * Host Url
   * URL of host instance to authenticate with.
   * @format uri
   * @minLength 1
   */
  host_url: string;
  /** Name of RAG provider to authenticate with. */
  rag_provider: RagAPIKeyAuthenticationProviderEnum;
}

/** ApiKeyRagAuthenticationConfigResponse */
export interface ApiKeyRagAuthenticationConfigResponse {
  /**
   * Authentication Method
   * @default "api_key"
   */
  authentication_method?: "api_key";
  /**
   * Host Url
   * URL of host instance to authenticate with.
   * @format uri
   * @minLength 1
   */
  host_url: string;
  /** Name of RAG provider to authenticate with. */
  rag_provider: RagAPIKeyAuthenticationProviderEnum;
}

/** ApiKeyRagAuthenticationConfigUpdateRequest */
export interface ApiKeyRagAuthenticationConfigUpdateRequest {
  /**
   * Api Key
   * API key to use for authentication.
   */
  api_key?: string | null;
  /**
   * Authentication Method
   * @default "api_key"
   */
  authentication_method?: "api_key";
  /**
   * Host Url
   * URL of host instance to authenticate with.
   */
  host_url?: string | null;
  /** Name of RAG provider to authenticate with. */
  rag_provider?: RagAPIKeyAuthenticationProviderEnum | null;
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

/** BaseCompletionRequest */
export interface BaseCompletionRequest {
  /**
   * Variables
   * List of VariableTemplateValue fields that specify the values to fill in for each template in the prompt
   * @default []
   */
  variables?: VariableTemplateValue[] | null;
}

/** BaseDetailsResponse */
export interface BaseDetailsResponse {
  /** Message */
  message?: string | null;
  /** Score */
  score?: boolean | null;
}

/** Body_add_tag_to_agentic_prompt_version_api_v1_tasks__task_id__prompts__prompt_name__versions__prompt_version__tags_put */
export interface BodyAddTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPut {
  /**
   * Tag
   * Tag to add to this prompt version
   */
  tag: string;
}

/** Body_add_tag_to_llm_eval_version_api_v1_tasks__task_id__llm_evals__eval_name__versions__eval_version__tags_put */
export interface BodyAddTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPut {
  /**
   * Tag
   * Tag to add to this llm eval version
   */
  tag: string;
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

/**
 * CompletionRequest
 * Request schema for running an unsaved agentic prompt
 */
export interface CompletionRequest {
  /** Run configuration for the unsaved prompt */
  completion_request?: PromptCompletionRequest;
  /** LLM configurations for this prompt (e.g. temperature, max_tokens, etc.) */
  config?: LLMPromptRequestConfigSettings | null;
  /**
   * Messages
   * List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])
   */
  messages: OpenAIMessageInput[];
  /**
   * Model Name
   * Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')
   */
  model_name: string;
  /** Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure') */
  model_provider: ModelProvider;
  /**
   * Tools
   * Available tools/functions for the model to call, in OpenAI function calling format
   */
  tools?: LLMToolInput[] | null;
}

export type ComputeSessionMetricsApiV1TracesSessionsSessionIdMetricsGetData = SessionTracesResponse;

export type ComputeSessionMetricsApiV1TracesSessionsSessionIdMetricsGetError = HTTPValidationError;

export interface ComputeSessionMetricsApiV1TracesSessionsSessionIdMetricsGetParams {
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

export type ComputeSpanMetricsApiV1TracesSpansSpanIdMetricsGetData = SpanWithMetricsResponse;

export type ComputeSpanMetricsApiV1TracesSpansSpanIdMetricsGetError = HTTPValidationError;

export type ComputeSpanMetricsV1SpanSpanIdMetricsGetData = SpanWithMetricsResponse;

export type ComputeSpanMetricsV1SpanSpanIdMetricsGetError = HTTPValidationError;

export type ComputeTraceMetricsApiV1TracesTraceIdMetricsGetData = TraceResponse;

export type ComputeTraceMetricsApiV1TracesTraceIdMetricsGetError = HTTPValidationError;

/** ConnectionCheckOutcome */
export type ConnectionCheckOutcome = "passed" | "failed";

/** ConnectionCheckResult */
export interface ConnectionCheckResult {
  /** Result of the connection check. */
  connection_check_outcome: ConnectionCheckOutcome;
  /**
   * Failure Reason
   * Explainer of the connection check failure result.
   */
  failure_reason?: string | null;
}

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

/** CreateAgenticPromptRequest */
export interface CreateAgenticPromptRequest {
  /** LLM configurations for this prompt (e.g. temperature, max_tokens, etc.) */
  config?: LLMPromptRequestConfigSettings | null;
  /**
   * Messages
   * List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])
   */
  messages: OpenAIMessageInput[];
  /**
   * Model Name
   * Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')
   */
  model_name: string;
  /** Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure') */
  model_provider: ModelProvider;
  /**
   * Tools
   * Available tools/functions for the model to call, in OpenAI function calling format
   */
  tools?: LLMToolInput[] | null;
}

export type CreateApiKeyAuthApiKeysPostData = ApiKeyResponse;

export type CreateApiKeyAuthApiKeysPostError = HTTPValidationError;

export type CreateDatasetApiV2DatasetsPostData = DatasetResponse;

export type CreateDatasetApiV2DatasetsPostError = HTTPValidationError;

export type CreateDatasetVersionApiV2DatasetsDatasetIdVersionsPostData = DatasetVersionResponse;

export type CreateDatasetVersionApiV2DatasetsDatasetIdVersionsPostError = HTTPValidationError;

export type CreateDefaultRuleApiV2DefaultRulesPostData = RuleResponse;

export type CreateDefaultRuleApiV2DefaultRulesPostError = HTTPValidationError;

/** CreateEvalRequest */
export interface CreateEvalRequest {
  /** LLM configurations for this eval (e.g. temperature, max_tokens, etc.) */
  config?: LLMRequestConfigSettings | null;
  /**
   * Instructions
   * Instructions for the llm eval
   */
  instructions: string;
  /**
   * Model Name
   * Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')
   */
  model_name: string;
  /** Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure') */
  model_provider: ModelProvider;
}

export type CreateNotebookApiV1TasksTaskIdNotebooksPostData = NotebookDetail;

export type CreateNotebookApiV1TasksTaskIdNotebooksPostError = HTTPValidationError;

/**
 * CreateNotebookRequest
 * Request to create a new notebook
 */
export interface CreateNotebookRequest {
  /**
   * Description
   * Description
   */
  description?: string | null;
  /**
   * Name
   * Name of the notebook
   */
  name: string;
  /** Initial state */
  state?: NotebookStateInput | null;
}

export type CreatePromptExperimentApiV1TasksTaskIdPromptExperimentsPostData = PromptExperimentSummary;

export type CreatePromptExperimentApiV1TasksTaskIdPromptExperimentsPostError = HTTPValidationError;

/**
 * CreatePromptExperimentRequest
 * Request to create a new prompt experiment
 */
export interface CreatePromptExperimentRequest {
  /** Reference to the dataset to use */
  dataset_ref: DatasetRef;
  /**
   * Dataset Row Filter
   * Optional list of column name and value filters. Only rows matching ALL specified column name-value pairs (AND condition) will be included in the experiment. If not specified, all rows from the dataset will be used.
   */
  dataset_row_filter?: NewDatasetVersionRowColumnItemRequest[] | null;
  /**
   * Description
   * Description of the experiment
   */
  description?: string | null;
  /**
   * Eval List
   * List of evaluations to run
   */
  eval_list: EvalRefInput[];
  /**
   * Name
   * Name for the experiment
   */
  name: string;
  /**
   * Prompt Configs
   * List of prompt configurations (saved or unsaved)
   */
  prompt_configs: (
    | ({
        type: "saved";
      } & SavedPromptConfig)
    | ({
        type: "unsaved";
      } & UnsavedPromptConfig)
  )[];
  /**
   * Prompt Variable Mapping
   * Shared variable mapping for all prompts
   */
  prompt_variable_mapping: PromptVariableMappingInput[];
}

export type CreateRagProviderApiV1TasksTaskIdRagProvidersPostData = RagProviderConfigurationResponse;

export type CreateRagProviderApiV1TasksTaskIdRagProvidersPostError = HTTPValidationError;

export type CreateRagSearchSettingsData = RagSearchSettingConfigurationResponse;

export type CreateRagSearchSettingsError = HTTPValidationError;

export type CreateRagSearchSettingsVersionData = RagSearchSettingConfigurationVersionResponse;

export type CreateRagSearchSettingsVersionError = HTTPValidationError;

export type CreateTaskApiV2TasksPostData = TaskResponse;

export type CreateTaskApiV2TasksPostError = HTTPValidationError;

export type CreateTaskMetricApiV2TasksTaskIdMetricsPostData = MetricResponse;

export type CreateTaskMetricApiV2TasksTaskIdMetricsPostError = HTTPValidationError;

export type CreateTaskRuleApiV2TasksTaskIdRulesPostData = RuleResponse;

export type CreateTaskRuleApiV2TasksTaskIdRulesPostError = HTTPValidationError;

export type CreateTransformApiV2DatasetsDatasetIdTransformsPostData = DatasetTransformResponse;

export type CreateTransformApiV2DatasetsDatasetIdTransformsPostError = HTTPValidationError;

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

/**
 * DatasetColumnSource
 * Reference to a dataset column
 */
export interface DatasetColumnSource {
  /**
   * Name
   * Name of the dataset column
   */
  name: string;
}

/**
 * DatasetColumnVariableSource
 * Variable source from a dataset column
 */
export interface DatasetColumnVariableSource {
  /** Dataset column source */
  dataset_column: DatasetColumnSource;
  /**
   * Type
   * Type of source: 'dataset_column'
   */
  type: "dataset_column";
}

/**
 * DatasetRef
 * Reference to a dataset and version
 */
export interface DatasetRef {
  /**
   * Id
   * Dataset ID
   * @format uuid
   */
  id: string;
  /**
   * Version
   * Dataset version number
   */
  version: number;
}

/** DatasetResponse */
export interface DatasetResponse {
  /**
   * Created At
   * Timestamp representing the time of dataset creation in unix milliseconds.
   */
  created_at: number;
  /**
   * Description
   * Description of the dataset.
   */
  description?: string | null;
  /**
   * Id
   * ID of the dataset.
   * @format uuid
   */
  id: string;
  /**
   * Latest Version Number
   * Version number representing the latest version of the dataset. If unset, no versions exist for the dataset yet.
   */
  latest_version_number?: number | null;
  /**
   * Metadata
   * Any metadata to include that describes additional information about the dataset.
   */
  metadata?: Record<string, any> | null;
  /**
   * Name
   * Name of the dataset.
   */
  name: string;
  /**
   * Updated At
   * Timestamp representing the time of the last dataset update in unix milliseconds.
   */
  updated_at: number;
}

/** DatasetTransformResponse */
export interface DatasetTransformResponse {
  /**
   * Created At
   * Timestamp representing the time of transform creation in unix milliseconds.
   */
  created_at: number;
  /**
   * Dataset Id
   * ID of the parent dataset.
   * @format uuid
   */
  dataset_id: string;
  /**
   * Definition
   * Transform definition in JSON format specifying extraction rules.
   */
  definition: Record<string, any>;
  /**
   * Description
   * Description of the transform.
   */
  description?: string | null;
  /**
   * Id
   * ID of the transform.
   * @format uuid
   */
  id: string;
  /**
   * Name
   * Name of the transform.
   */
  name: string;
  /**
   * Updated At
   * Timestamp representing the time of the last transform update in unix milliseconds.
   */
  updated_at: number;
}

/** DatasetTransformUpdateRequest */
export interface DatasetTransformUpdateRequest {
  /**
   * Definition
   * Transform definition in JSON format specifying extraction rules.
   */
  definition?: Record<string, any> | null;
  /**
   * Description
   * Description of the transform.
   */
  description?: string | null;
  /**
   * Name
   * Name of the transform.
   */
  name?: string | null;
}

/** DatasetUpdateRequest */
export interface DatasetUpdateRequest {
  /**
   * Description
   * Description of the dataset.
   */
  description?: string | null;
  /**
   * Metadata
   * Any metadata to include that describes additional information about the dataset.
   */
  metadata?: Record<string, any> | null;
  /**
   * Name
   * Name of the dataset.
   */
  name: string | null;
}

/** DatasetVersionMetadataResponse */
export interface DatasetVersionMetadataResponse {
  /**
   * Column Names
   * Names of all columns in the dataset version.
   */
  column_names: string[];
  /**
   * Created At
   * Timestamp representing the time of dataset version creation in unix milliseconds.
   */
  created_at: number;
  /**
   * Dataset Id
   * ID of the dataset.
   * @format uuid
   */
  dataset_id: string;
  /**
   * Version Number
   * Version number of the dataset version.
   */
  version_number: number;
}

/** DatasetVersionResponse */
export interface DatasetVersionResponse {
  /**
   * Column Names
   * Names of all columns in the dataset version.
   */
  column_names: string[];
  /**
   * Created At
   * Timestamp representing the time of dataset version creation in unix milliseconds.
   */
  created_at: number;
  /**
   * Dataset Id
   * ID of the dataset.
   * @format uuid
   */
  dataset_id: string;
  /**
   * Page
   * The current page number for the included rows.
   */
  page: number;
  /**
   * Page Size
   * The number of rows per page.
   */
  page_size: number;
  /**
   * Rows
   * list of rows in the dataset version.
   */
  rows: DatasetVersionRowResponse[];
  /**
   * Total Count
   * The total number of rows in the dataset version.
   */
  total_count: number;
  /**
   * Total Pages
   * The total number of pages.
   */
  total_pages: number;
  /**
   * Version Number
   * Version number of the dataset version.
   */
  version_number: number;
}

/** DatasetVersionRowColumnItemResponse */
export interface DatasetVersionRowColumnItemResponse {
  /**
   * Column Name
   * Name of the column.
   */
  column_name: string;
  /**
   * Column Value
   * Value of the column.
   */
  column_value: string;
}

/** DatasetVersionRowResponse */
export interface DatasetVersionRowResponse {
  /**
   * Created At
   * Timestamp representing the time of dataset row creation in unix milliseconds. May differ within a version if a row already existed in a past version of the dataset.
   */
  created_at: number;
  /**
   * Data
   * List of column names and values in the row.
   */
  data: DatasetVersionRowColumnItemResponse[];
  /**
   * Id
   * ID of the version field.
   * @format uuid
   */
  id: string;
}

export type DeactivateApiKeyAuthApiKeysDeactivateApiKeyIdDeleteData = ApiKeyResponse;

export type DeactivateApiKeyAuthApiKeysDeactivateApiKeyIdDeleteError = HTTPValidationError;

export type DefaultValidatePromptApiV2ValidatePromptPostData = ValidationResult;

export type DefaultValidatePromptApiV2ValidatePromptPostError = HTTPValidationError;

export type DefaultValidateResponseApiV2ValidateResponseInferenceIdPostData = ValidationResult;

export type DefaultValidateResponseApiV2ValidateResponseInferenceIdPostError = HTTPValidationError;

export type DeleteAgenticPromptApiV1TasksTaskIdPromptsPromptNameDeleteData = any;

export type DeleteAgenticPromptApiV1TasksTaskIdPromptsPromptNameDeleteError = HTTPValidationError;

export type DeleteAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionDeleteData = any;

export type DeleteAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionDeleteError = HTTPValidationError;

export type DeleteAnnotationFromTraceApiV1TracesTraceIdAnnotationsDeleteData = any;

export type DeleteAnnotationFromTraceApiV1TracesTraceIdAnnotationsDeleteError = HTTPValidationError;

export type DeleteDatasetApiV2DatasetsDatasetIdDeleteData = any;

export type DeleteDatasetApiV2DatasetsDatasetIdDeleteError = HTTPValidationError;

export type DeleteFileApiChatFilesFileIdDeleteData = any;

export type DeleteFileApiChatFilesFileIdDeleteError = HTTPValidationError;

export type DeleteLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameDeleteData = any;

export type DeleteLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameDeleteError = HTTPValidationError;

export type DeleteModelProviderApiV1ModelProvidersProviderDeleteData = any;

export type DeleteModelProviderApiV1ModelProvidersProviderDeleteError = HTTPValidationError;

export type DeleteNotebookApiV1NotebooksNotebookIdDeleteData = any;

export type DeleteNotebookApiV1NotebooksNotebookIdDeleteError = HTTPValidationError;

export type DeletePromptExperimentApiV1PromptExperimentsExperimentIdDeleteData = any;

export type DeletePromptExperimentApiV1PromptExperimentsExperimentIdDeleteError = HTTPValidationError;

export type DeleteRagProviderApiV1RagProvidersProviderIdDeleteData = any;

export type DeleteRagProviderApiV1RagProvidersProviderIdDeleteError = HTTPValidationError;

export type DeleteRagSearchSettingData = any;

export type DeleteRagSearchSettingError = HTTPValidationError;

export type DeleteRagSearchSettingVersionData = any;

export type DeleteRagSearchSettingVersionError = HTTPValidationError;

export type DeleteTagFromAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsTagDeleteData = any;

export type DeleteTagFromAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsTagDeleteError = HTTPValidationError;

export type DeleteTagFromLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsTagDeleteData = any;

export type DeleteTagFromLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsTagDeleteError = HTTPValidationError;

export type DeleteTransformApiV2DatasetsDatasetIdTransformsTransformIdDeleteData = any;

export type DeleteTransformApiV2DatasetsDatasetIdTransformsTransformIdDeleteError = HTTPValidationError;

export type DeleteUserUsersUserIdDeleteData = any;

export type DeleteUserUsersUserIdDeleteError = HTTPValidationError;

/**
 * EvalExecution
 * Details of an eval execution
 */
export interface EvalExecution {
  /**
   * Eval Input Variables
   * Input variables used for the eval
   */
  eval_input_variables: InputVariable[];
  /**
   * Eval Name
   * Name of the evaluation
   */
  eval_name: string;
  /** Results from the eval (None if not yet executed) */
  eval_results?: EvalExecutionResult | null;
  /**
   * Eval Version
   * Version of the evaluation
   */
  eval_version: string;
}

/**
 * EvalExecutionResult
 * Results from an eval execution
 */
export interface EvalExecutionResult {
  /**
   * Cost
   * Cost of the evaluation
   */
  cost: string;
  /**
   * Explanation
   * Explanation of the score
   */
  explanation: string;
  /**
   * Score
   * Score from the evaluation
   */
  score: number;
}

/**
 * EvalRef
 * Reference to an evaluation configuration
 */
export interface EvalRefInput {
  /**
   * Name
   * Name of the evaluation
   */
  name: string;
  /**
   * Variable Mapping
   * Mapping of eval variables to data sources
   */
  variable_mapping: EvalVariableMappingInput[];
  /**
   * Version
   * Version of the evaluation
   */
  version: number;
}

/**
 * EvalRef
 * Reference to an evaluation configuration
 */
export interface EvalRefOutput {
  /**
   * Name
   * Name of the evaluation
   */
  name: string;
  /**
   * Variable Mapping
   * Mapping of eval variables to data sources
   */
  variable_mapping: EvalVariableMappingOutput[];
  /**
   * Version
   * Version of the evaluation
   */
  version: number;
}

/**
 * EvalResultSummary
 * Results for a single eval
 */
export interface EvalResultSummary {
  /**
   * Eval Name
   * Name of the evaluation
   */
  eval_name: string;
  /**
   * Eval Version
   * Version of the evaluation
   */
  eval_version: string;
  /**
   * Pass Count
   * Number of test cases that passed
   */
  pass_count: number;
  /**
   * Total Count
   * Total number of test cases evaluated
   */
  total_count: number;
}

/**
 * EvalVariableMapping
 * Mapping of an eval variable to its source (dataset column or experiment output)
 */
export interface EvalVariableMappingInput {
  /**
   * Source
   * Source of the variable value
   */
  source:
    | ({
        type: "dataset_column";
      } & DatasetColumnVariableSource)
    | ({
        type: "experiment_output";
      } & ExperimentOutputVariableSource);
  /**
   * Variable Name
   * Name of the eval variable
   */
  variable_name: string;
}

/**
 * EvalVariableMapping
 * Mapping of an eval variable to its source (dataset column or experiment output)
 */
export interface EvalVariableMappingOutput {
  /**
   * Source
   * Source of the variable value
   */
  source:
    | ({
        type: "dataset_column";
      } & DatasetColumnVariableSource)
    | ({
        type: "experiment_output";
      } & ExperimentOutputVariableSource);
  /**
   * Variable Name
   * Name of the eval variable
   */
  variable_name: string;
}

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

export type ExecuteHybridSearchApiV1RagProvidersProviderIdHybridSearchPostData = RagProviderQueryResponse;

export type ExecuteHybridSearchApiV1RagProvidersProviderIdHybridSearchPostError = HTTPValidationError;

export type ExecuteKeywordSearchApiV1RagProvidersProviderIdKeywordSearchPostData = RagProviderQueryResponse;

export type ExecuteKeywordSearchApiV1RagProvidersProviderIdKeywordSearchPostError = HTTPValidationError;

export type ExecuteSimilarityTextSearchApiV1RagProvidersProviderIdSimilarityTextSearchPostData = RagProviderQueryResponse;

export type ExecuteSimilarityTextSearchApiV1RagProvidersProviderIdSimilarityTextSearchPostError = HTTPValidationError;

export type ExecuteTransformEndpointApiV2DatasetsDatasetIdTransformsTransformIdExtractionsPostData = ExecuteTransformResponse;

export type ExecuteTransformEndpointApiV2DatasetsDatasetIdTransformsTransformIdExtractionsPostError = HTTPValidationError;

/** ExecuteTransformRequest */
export interface ExecuteTransformRequest {
  /**
   * Trace Id
   * ID of the trace to execute the transform against.
   */
  trace_id: string;
}

/** ExecuteTransformResponse */
export interface ExecuteTransformResponse {
  /**
   * Rows Extracted
   * List of rows extracted from the trace, ready to be added to a dataset version via the create dataset version API.
   */
  rows_extracted: NewDatasetVersionRowRequest[];
}

/**
 * ExperimentOutputSource
 * Reference to experiment output
 */
export interface ExperimentOutputSource {
  /**
   * Json Path
   * Optional JSON path to extract from experiment output
   */
  json_path?: string | null;
}

/**
 * ExperimentOutputVariableSource
 * Variable source from experiment output
 */
export interface ExperimentOutputVariableSource {
  /** Experiment output source */
  experiment_output: ExperimentOutputSource;
  /**
   * Type
   * Type of source: 'experiment_output'
   */
  type: "experiment_output";
}

/**
 * ExperimentStatus
 * Status of a prompt experiment
 */
export type ExperimentStatus = "queued" | "running" | "failed" | "completed";

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

export type GetAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGetData = AgenticPrompt;

export type GetAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGetError = HTTPValidationError;

export type GetAgenticPromptByTagApiV1TasksTaskIdPromptsPromptNameVersionsTagsTagGetData = AgenticPrompt;

export type GetAgenticPromptByTagApiV1TasksTaskIdPromptsPromptNameVersionsTagsTagGetError = HTTPValidationError;

/** Response Get All Active Api Keys Auth Api Keys  Get */
export type GetAllActiveApiKeysAuthApiKeysGetData = ApiKeyResponse[];

export type GetAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGetData = AgenticPromptVersionListResponse;

export type GetAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGetError = HTTPValidationError;

export interface GetAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGetParams {
  /**
   * Created After
   * Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).
   */
  created_after?: string | null;
  /**
   * Created Before
   * Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).
   */
  created_before?: string | null;
  /**
   * Exclude Deleted
   * Whether to exclude deleted prompt versions from the results. Default is False.
   * @default false
   */
  exclude_deleted?: boolean;
  /**
   * Max Version
   * Maximum version number to filter on (inclusive).
   */
  max_version?: number | null;
  /**
   * Min Version
   * Minimum version number to filter on (inclusive).
   */
  min_version?: number | null;
  /**
   * Model Name
   * Filter by model name (e.g., 'gpt-4', 'claude-3-5-sonnet').
   */
  model_name?: string | null;
  /**
   * Model Provider
   * Filter by model provider (e.g., 'openai', 'anthropic', 'azure').
   */
  model_provider?: string | null;
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
   * Prompt Name
   * The name of the prompt to retrieve.
   */
  promptName: string;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Task Id
   * @format uuid
   */
  taskId: string;
}

export type GetAllAgenticPromptsApiV1TasksTaskIdPromptsGetData = LLMGetAllMetadataListResponse;

export type GetAllAgenticPromptsApiV1TasksTaskIdPromptsGetError = HTTPValidationError;

export interface GetAllAgenticPromptsApiV1TasksTaskIdPromptsGetParams {
  /**
   * Created After
   * Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).
   */
  created_after?: string | null;
  /**
   * Created Before
   * Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).
   */
  created_before?: string | null;
  /**
   * Llm Asset Names
   * LLM asset names to filter on using partial matching. If provided, llm assets matching any of these name patterns will be returned
   */
  llm_asset_names?: string[] | null;
  /**
   * Model Name
   * Filter by model name (e.g., 'gpt-4', 'claude-3-5-sonnet').
   */
  model_name?: string | null;
  /**
   * Model Provider
   * Filter by model provider (e.g., 'openai', 'anthropic', 'azure').
   */
  model_provider?: string | null;
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
   * Task Id
   * @format uuid
   */
  taskId: string;
}

export type GetAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGetData = LLMEvalsVersionListResponse;

export type GetAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGetError = HTTPValidationError;

export interface GetAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGetParams {
  /**
   * Created After
   * Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).
   */
  created_after?: string | null;
  /**
   * Created Before
   * Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).
   */
  created_before?: string | null;
  /**
   * LLM Eval Name
   * The name of the llm eval to retrieve.
   */
  evalName: string;
  /**
   * Exclude Deleted
   * Whether to exclude deleted prompt versions from the results. Default is False.
   * @default false
   */
  exclude_deleted?: boolean;
  /**
   * Max Version
   * Maximum version number to filter on (inclusive).
   */
  max_version?: number | null;
  /**
   * Min Version
   * Minimum version number to filter on (inclusive).
   */
  min_version?: number | null;
  /**
   * Model Name
   * Filter by model name (e.g., 'gpt-4', 'claude-3-5-sonnet').
   */
  model_name?: string | null;
  /**
   * Model Provider
   * Filter by model provider (e.g., 'openai', 'anthropic', 'azure').
   */
  model_provider?: string | null;
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
   * Task Id
   * @format uuid
   */
  taskId: string;
}

export type GetAllLlmEvalsApiV1TasksTaskIdLlmEvalsGetData = LLMGetAllMetadataListResponse;

export type GetAllLlmEvalsApiV1TasksTaskIdLlmEvalsGetError = HTTPValidationError;

export interface GetAllLlmEvalsApiV1TasksTaskIdLlmEvalsGetParams {
  /**
   * Created After
   * Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).
   */
  created_after?: string | null;
  /**
   * Created Before
   * Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).
   */
  created_before?: string | null;
  /**
   * Llm Asset Names
   * LLM asset names to filter on using partial matching. If provided, llm assets matching any of these name patterns will be returned
   */
  llm_asset_names?: string[] | null;
  /**
   * Model Name
   * Filter by model name (e.g., 'gpt-4', 'claude-3-5-sonnet').
   */
  model_name?: string | null;
  /**
   * Model Provider
   * Filter by model provider (e.g., 'openai', 'anthropic', 'azure').
   */
  model_provider?: string | null;
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
   * Task Id
   * @format uuid
   */
  taskId: string;
}

/** Response Get All Tasks Api V2 Tasks Get */
export type GetAllTasksApiV2TasksGetData = TaskResponse[];

export type GetApiKeyAuthApiKeysApiKeyIdGetData = ApiKeyResponse;

export type GetApiKeyAuthApiKeysApiKeyIdGetError = HTTPValidationError;

export type GetConversationsApiChatConversationsGetData = PageConversationBaseResponse;

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

export type GetDatasetApiV2DatasetsDatasetIdGetData = DatasetResponse;

export type GetDatasetApiV2DatasetsDatasetIdGetError = HTTPValidationError;

export type GetDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGetData = DatasetVersionResponse;

export type GetDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGetError = HTTPValidationError;

export interface GetDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGetParams {
  /**
   * Dataset Id
   * ID of the dataset to fetch the version for.
   * @format uuid
   */
  datasetId: string;
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
   * Version Number
   * Version number to fetch.
   */
  versionNumber: number;
}

export type GetDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGetData = DatasetVersionRowResponse;

export type GetDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGetError = HTTPValidationError;

export type GetDatasetVersionsApiV2DatasetsDatasetIdVersionsGetData = ListDatasetVersionsResponse;

export type GetDatasetVersionsApiV2DatasetsDatasetIdVersionsGetError = HTTPValidationError;

export interface GetDatasetVersionsApiV2DatasetsDatasetIdVersionsGetParams {
  /**
   * Dataset Id
   * ID of the dataset to fetch versions for.
   * @format uuid
   */
  datasetId: string;
  /**
   * Latest Version Only
   * Whether to only include the latest version for the dataset in the response. Defaults to False.
   * @default false
   */
  latest_version_only?: boolean;
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

export type GetDatasetsApiV2DatasetsSearchGetData = SearchDatasetsResponse;

export type GetDatasetsApiV2DatasetsSearchGetError = HTTPValidationError;

export interface GetDatasetsApiV2DatasetsSearchGetParams {
  /**
   * Dataset Ids
   * List of dataset ids to query for.
   */
  dataset_ids?: string[] | null;
  /**
   * Dataset Name
   * Dataset name substring to search for.
   */
  dataset_name?: string | null;
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

/** Response Get Default Rules Api V2 Default Rules Get */
export type GetDefaultRulesApiV2DefaultRulesGetData = RuleResponse[];

export type GetDefaultTaskApiChatDefaultTaskGetData = ChatDefaultTaskResponse;

export type GetExperimentTestCasesApiV1PromptExperimentsExperimentIdTestCasesGetData = TestCaseListResponse;

export type GetExperimentTestCasesApiV1PromptExperimentsExperimentIdTestCasesGetError = HTTPValidationError;

export interface GetExperimentTestCasesApiV1PromptExperimentsExperimentIdTestCasesGetParams {
  /**
   * Experiment ID
   * The ID of the experiment
   */
  experimentId: string;
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

/** Response Get Files Api Chat Files Get */
export type GetFilesApiChatFilesGetData = ExternalDocument[];

/** Response Get Inference Document Context Api Chat Context  Inference Id  Get */
export type GetInferenceDocumentContextApiChatContextInferenceIdGetData = ChatDocumentContext[];

export type GetInferenceDocumentContextApiChatContextInferenceIdGetError = HTTPValidationError;

export type GetLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGetData = LLMEval;

export type GetLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGetError = HTTPValidationError;

export type GetLlmEvalByTagApiV1TasksTaskIdLlmEvalsEvalNameVersionsTagsTagGetData = LLMEval;

export type GetLlmEvalByTagApiV1TasksTaskIdLlmEvalsEvalNameVersionsTagsTagGetError = HTTPValidationError;

export type GetModelProvidersApiV1ModelProvidersGetData = ModelProviderList;

export type GetModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGetData = ModelProviderModelList;

export type GetModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGetError = HTTPValidationError;

export type GetNotebookApiV1NotebooksNotebookIdGetData = NotebookDetail;

export type GetNotebookApiV1NotebooksNotebookIdGetError = HTTPValidationError;

export type GetNotebookHistoryApiV1NotebooksNotebookIdHistoryGetData = PromptExperimentListResponse;

export type GetNotebookHistoryApiV1NotebooksNotebookIdHistoryGetError = HTTPValidationError;

export interface GetNotebookHistoryApiV1NotebooksNotebookIdHistoryGetParams {
  /**
   * Notebook Id
   * Notebook ID
   */
  notebookId: string;
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

export type GetNotebookStateApiV1NotebooksNotebookIdStateGetData = NotebookStateOutput;

export type GetNotebookStateApiV1NotebooksNotebookIdStateGetError = HTTPValidationError;

export type GetPromptExperimentApiV1PromptExperimentsExperimentIdGetData = PromptExperimentDetail;

export type GetPromptExperimentApiV1PromptExperimentsExperimentIdGetError = HTTPValidationError;

export type GetPromptVersionResultsApiV1PromptExperimentsExperimentIdPromptsPromptKeyResultsGetData = PromptVersionResultListResponse;

export type GetPromptVersionResultsApiV1PromptExperimentsExperimentIdPromptsPromptKeyResultsGetError = HTTPValidationError;

export interface GetPromptVersionResultsApiV1PromptExperimentsExperimentIdPromptsPromptKeyResultsGetParams {
  /**
   * Experiment ID
   * The ID of the experiment
   */
  experimentId: string;
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
   * Prompt Key
   * The prompt key (format: 'saved:name:version' or 'unsaved:auto_name'). URL-encode colons as %3A
   */
  promptKey: string;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
}

export type GetRagProviderApiV1RagProvidersProviderIdGetData = RagProviderConfigurationResponse;

export type GetRagProviderApiV1RagProvidersProviderIdGetError = HTTPValidationError;

export type GetRagProvidersApiV1TasksTaskIdRagProvidersGetData = SearchRagProviderConfigurationsResponse;

export type GetRagProvidersApiV1TasksTaskIdRagProvidersGetError = HTTPValidationError;

export interface GetRagProvidersApiV1TasksTaskIdRagProvidersGetParams {
  /**
   * Authentication Method
   * RAG Provider authentication method to filter by.
   */
  authentication_method?: RagProviderAuthenticationMethodEnum | null;
  /**
   * Config Name
   * RAG Provider configuration name substring to search for.
   */
  config_name?: string | null;
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
   * Rag Provider Name
   * RAG provider name to filter by.
   */
  rag_provider_name?: RagAPIKeyAuthenticationProviderEnum | null;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Task Id
   * ID of the task to fetch the provider connections for.
   * @format uuid
   */
  taskId: string;
}

export type GetRagSearchSettingConfigurationVersionsApiV1RagSearchSettingsSettingConfigurationIdVersionsGetData =
  ListRagSearchSettingConfigurationVersionsResponse;

export type GetRagSearchSettingConfigurationVersionsApiV1RagSearchSettingsSettingConfigurationIdVersionsGetError = HTTPValidationError;

export interface GetRagSearchSettingConfigurationVersionsApiV1RagSearchSettingsSettingConfigurationIdVersionsGetParams {
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
   * Setting Configuration Id
   * ID of the RAG search setting configuration to get versions for.
   * @format uuid
   */
  settingConfigurationId: string;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Tags
   * List of tags to filter for versions tagged with any matching tag.
   */
  tags?: string[] | null;
  /**
   * Version Numbers
   * List of version numbers to filter for.
   */
  version_numbers?: number[] | null;
}

export type GetRagSearchSettingData = RagSearchSettingConfigurationResponse;

export type GetRagSearchSettingError = HTTPValidationError;

export type GetRagSearchSettingVersionByTagData = RagSearchSettingConfigurationVersionResponse;

export type GetRagSearchSettingVersionByTagError = HTTPValidationError;

export type GetRagSearchSettingVersionData = RagSearchSettingConfigurationVersionResponse;

export type GetRagSearchSettingVersionError = HTTPValidationError;

export type GetSessionTracesApiV1TracesSessionsSessionIdGetData = SessionTracesResponse;

export type GetSessionTracesApiV1TracesSessionsSessionIdGetError = HTTPValidationError;

export interface GetSessionTracesApiV1TracesSessionsSessionIdGetParams {
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

export type GetSpanByIdApiV1TracesSpansSpanIdGetData = SpanWithMetricsResponse;

export type GetSpanByIdApiV1TracesSpansSpanIdGetError = HTTPValidationError;

export type GetTaskApiV2TasksTaskIdGetData = TaskResponse;

export type GetTaskApiV2TasksTaskIdGetError = HTTPValidationError;

export type GetTaskRagSearchSettingsApiV1TasksTaskIdRagSearchSettingsGetData = ListRagSearchSettingConfigurationsResponse;

export type GetTaskRagSearchSettingsApiV1TasksTaskIdRagSearchSettingsGetError = HTTPValidationError;

export interface GetTaskRagSearchSettingsApiV1TasksTaskIdRagSearchSettingsGetParams {
  /**
   * Config Name
   * Rag search setting configuration name substring to search for.
   */
  config_name?: string | null;
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
   * Rag Provider Ids
   * List of rag provider configuration IDs to filter for.
   */
  rag_provider_ids?: string[] | null;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Task Id
   * ID of the task to fetch the provider connections for.
   * @format uuid
   */
  taskId: string;
}

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

export type GetTransformApiV2DatasetsDatasetIdTransformsTransformIdGetData = DatasetTransformResponse;

export type GetTransformApiV2DatasetsDatasetIdTransformsTransformIdGetError = HTTPValidationError;

export type GetUnsavedPromptVariablesListApiV1PromptVariablesPostData = UnsavedPromptVariablesListResponse;

export type GetUnsavedPromptVariablesListApiV1PromptVariablesPostError = HTTPValidationError;

export type GetUserDetailsApiV1TracesUsersUserIdGetData = TraceUserMetadataResponse;

export type GetUserDetailsApiV1TracesUsersUserIdGetError = HTTPValidationError;

export interface GetUserDetailsApiV1TracesUsersUserIdGetParams {
  /**
   * Task Ids
   * Task IDs to filter on. At least one is required.
   * @minItems 1
   */
  task_ids: string[];
  /** User Id */
  userId: string;
}

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

/**
 * HybridFusion
 * Define how the query's hybrid fusion operation should be performed.
 */
export type HybridFusion = "FUSION_TYPE_RANKED" | "FUSION_TYPE_RELATIVE_SCORE";

/** ImageURL */
export interface ImageURL {
  /**
   * Url
   * URL of the image
   */
  url: string;
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

/** InputAudio */
export interface InputAudio {
  /**
   * Data
   * Base64 encoded audio data
   */
  data: string;
  /**
   * Format
   * audio format (e.g. 'mp3', 'wav', 'flac', etc.)
   */
  format: string;
}

/**
 * InputVariable
 * Input variable for a test case
 */
export interface InputVariable {
  /**
   * Value
   * Value of the variable
   */
  value: string;
  /**
   * Variable Name
   * Name of the variable
   */
  variable_name: string;
}

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
   * Type
   * The argument's type (e.g. string, boolean, etc.)
   * @default "string"
   */
  type?: string;
}

/** JsonSchema */
export interface JsonSchema {
  /**
   * Additionalproperties
   * Whether the function definition should allow additional properties
   */
  additionalProperties?: boolean | null;
  /**
   * Properties
   * The name of the property and the property schema (e.g. {'topic': {'type': 'string', 'description': 'the topic to generate a joke for'})
   */
  properties: Record<string, JsonPropertySchema>;
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

/** LLMBaseConfigSettings */
export interface LLMBaseConfigSettings {
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
   * Presence Penalty
   * Presence penalty (-2.0 to 2.0). Positive values penalize new tokens based on their presence
   */
  presence_penalty?: number | null;
  /** Reasoning effort level for models that support it (e.g., OpenAI o1 series) */
  reasoning_effort?: ReasoningEffortEnum | null;
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

/** LLMConfigSettings */
export interface LLMConfigSettings {
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
   * Presence Penalty
   * Presence penalty (-2.0 to 2.0). Positive values penalize new tokens based on their presence
   */
  presence_penalty?: number | null;
  /** Reasoning effort level for models that support it (e.g., OpenAI o1 series) */
  reasoning_effort?: ReasoningEffortEnum | null;
  /**
   * Response Format
   * Either a structured json_schema or a Pydantic model to enforce structured outputs.
   */
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
  tool_choice?: ToolChoiceEnum | ToolChoice | null;
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

/** LLMEval */
export interface LLMEval {
  /** LLM configurations for this eval (e.g. temperature, max_tokens, etc.) */
  config?: LLMBaseConfigSettings | null;
  /**
   * Created At
   * Timestamp when the llm eval was created.
   * @format date-time
   */
  created_at: string;
  /**
   * Deleted At
   * Time that this llm eval was deleted
   */
  deleted_at?: string | null;
  /**
   * Instructions
   * Instructions for the llm eval
   */
  instructions: string;
  /**
   * Model Name
   * Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')
   */
  model_name: string;
  /** Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure') */
  model_provider: ModelProvider;
  /**
   * Name
   * Name of the llm eval
   */
  name: string;
  /**
   * Tags
   * List of tags for this llm eval version
   */
  tags?: string[];
  /**
   * Variables
   * List of variable names for the llm eval
   */
  variables?: string[];
  /**
   * Version
   * Version of the llm eval
   * @default 1
   */
  version?: number;
}

/** LLMEvalRunResponse */
export interface LLMEvalRunResponse {
  /**
   * Cost
   * Cost of this llm completion
   */
  cost: string;
  /**
   * Reason
   * Explanation for how the llm arrived at this answer.
   */
  reason: string;
  /**
   * Score
   * Score for this llm eval
   */
  score: number;
}

/** LLMEvalsVersionListResponse */
export interface LLMEvalsVersionListResponse {
  /**
   * Count
   * Total number of llm evals matching filters
   */
  count: number;
  /**
   * Versions
   * List of llm eval version metadata
   */
  versions: LLMVersionResponse[];
}

/** LLMGetAllMetadataListResponse */
export interface LLMGetAllMetadataListResponse {
  /**
   * Count
   * Total number of llm assets matching filters
   */
  count: number;
  /**
   * Llm Metadata
   * List of llm asset metadata
   */
  llm_metadata: LLMGetAllMetadataResponse[];
}

/** LLMGetAllMetadataResponse */
export interface LLMGetAllMetadataResponse {
  /**
   * Created At
   * Timestamp when the llm asset was created
   * @format date-time
   */
  created_at: string;
  /**
   * Deleted Versions
   * List of deleted versions of the llm asset
   */
  deleted_versions: number[];
  /**
   * Latest Version Created At
   * Timestamp when the last version of the llm asset was created
   * @format date-time
   */
  latest_version_created_at: string;
  /**
   * Name
   * Name of the llm asset
   */
  name: string;
  /**
   * Tags
   * List of tags for the llm asset
   */
  tags?: string[];
  /**
   * Versions
   * Number of versions of the llm asset
   */
  versions: number;
}

/** LLMPromptRequestConfigSettings */
export interface LLMPromptRequestConfigSettings {
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
  tool_choice?: ToolChoiceEnum | ToolChoice | null;
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

/** LLMRequestConfigSettings */
export interface LLMRequestConfigSettings {
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
   * Presence Penalty
   * Presence penalty (-2.0 to 2.0). Positive values penalize new tokens based on their presence
   */
  presence_penalty?: number | null;
  /** Reasoning effort level for models that support it (e.g., OpenAI o1 series) */
  reasoning_effort?: ReasoningEffortEnum | null;
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

/** LLMResponseFormatEnum */
export type LLMResponseFormatEnum = "text" | "json_object" | "json_schema";

/** LLMResponseFormat */
export interface LLMResponseFormatInput {
  /** JSON schema definition (required when type is 'json_schema') */
  json_schema?: LLMResponseSchemaInput | null;
  /**
   * Response format type: 'text', 'json_object', or 'json_schema'
   * @example "json_schema"
   */
  type: LLMResponseFormatEnum;
}

/** LLMResponseFormat */
export interface LLMResponseFormatOutput {
  /** JSON schema definition (required when type is 'json_schema') */
  json_schema?: LLMResponseSchemaOutput | null;
  /**
   * Response format type: 'text', 'json_object', or 'json_schema'
   * @example "json_schema"
   */
  type: LLMResponseFormatEnum;
}

/** LLMResponseSchema */
export interface LLMResponseSchemaInput {
  /**
   * Description
   * Description of the schema
   */
  description?: string | null;
  /**
   * Name
   * Name of the schema
   */
  name: string;
  /** The JSON schema object */
  schema: JsonSchema;
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
  /**
   * Name
   * Name of the schema
   */
  name: string;
  /** The JSON schema object */
  schema: JsonSchema;
  /**
   * Strict
   * Whether to enforce strict schema adherence
   */
  strict?: boolean | null;
}

/** LLMTool */
export interface LLMToolInput {
  /** The function definition */
  function: ToolFunctionInput;
  /**
   * Strict
   * Whether the function definition should use OpenAI's strict mode
   */
  strict?: boolean | null;
  /**
   * Type
   * The type of tool. Should always be 'function'
   * @default "function"
   */
  type?: string;
}

/** LLMTool */
export interface LLMToolOutput {
  /** The function definition */
  function: ToolFunctionOutput;
  /**
   * Strict
   * Whether the function definition should use OpenAI's strict mode
   */
  strict?: boolean | null;
  /**
   * Type
   * The type of tool. Should always be 'function'
   * @default "function"
   */
  type?: string;
}

/** LLMVersionResponse */
export interface LLMVersionResponse {
  /**
   * Created At
   * Timestamp when the llm eval version was created
   * @format date-time
   */
  created_at: string;
  /**
   * Deleted At
   * Timestamp when the llm eval version was deleted (None if not deleted)
   */
  deleted_at: string | null;
  /**
   * Model Name
   * Model name chosen for this version of the llm eval
   */
  model_name: string;
  /** Model provider chosen for this version of the llm eval */
  model_provider: ModelProvider;
  /**
   * Tags
   * List of tags for the llm asset
   */
  tags?: string[];
  /**
   * Version
   * Version number of the llm eval
   */
  version: number;
}

/** ListDatasetTransformsResponse */
export interface ListDatasetTransformsResponse {
  /**
   * Transforms
   * List of transforms for the dataset.
   */
  transforms: DatasetTransformResponse[];
}

/** ListDatasetVersionsResponse */
export interface ListDatasetVersionsResponse {
  /**
   * Page
   * The current page number for the included rows.
   */
  page: number;
  /**
   * Page Size
   * The number of rows per page.
   */
  page_size: number;
  /**
   * Total Count
   * The total number of rows in the dataset version.
   */
  total_count: number;
  /**
   * Total Pages
   * The total number of pages.
   */
  total_pages: number;
  /**
   * Versions
   * List of existing versions for the dataset.
   */
  versions: DatasetVersionMetadataResponse[];
}

export type ListNotebooksApiV1TasksTaskIdNotebooksGetData = NotebookListResponse;

export type ListNotebooksApiV1TasksTaskIdNotebooksGetError = HTTPValidationError;

export interface ListNotebooksApiV1TasksTaskIdNotebooksGetParams {
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
   * Task Id
   * @format uuid
   */
  taskId: string;
}

export type ListPromptExperimentsApiV1TasksTaskIdPromptExperimentsGetData = PromptExperimentListResponse;

export type ListPromptExperimentsApiV1TasksTaskIdPromptExperimentsGetError = HTTPValidationError;

export interface ListPromptExperimentsApiV1TasksTaskIdPromptExperimentsGetParams {
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
   * Search
   * Search text to filter experiments by name, description, prompt name, or dataset name
   */
  search?: string | null;
  /**
   * Sort the results (asc/desc)
   * @default "desc"
   */
  sort?: PaginationSortMethod;
  /**
   * Task Id
   * @format uuid
   */
  taskId: string;
}

export type ListRagProviderCollectionsApiV1RagProvidersProviderIdCollectionsGetData = SearchRagProviderCollectionsResponse;

export type ListRagProviderCollectionsApiV1RagProvidersProviderIdCollectionsGetError = HTTPValidationError;

/** ListRagSearchSettingConfigurationVersionsResponse */
export interface ListRagSearchSettingConfigurationVersionsResponse {
  /**
   * Count
   * The total number of RAG search setting configuration versions matching the parameters.
   */
  count: number;
  /**
   * Rag Provider Setting Configurations
   * List of RAG search setting configuration versions matching the search filters. Length is less than or equal to page_size parameter
   */
  rag_provider_setting_configurations: RagSearchSettingConfigurationVersionResponse[];
}

/** ListRagSearchSettingConfigurationsResponse */
export interface ListRagSearchSettingConfigurationsResponse {
  /**
   * Count
   * The total number of RAG search setting configurations matching the parameters.
   */
  count: number;
  /**
   * Rag Provider Setting Configurations
   * List of RAG search setting configurations matching the search filters. Length is less than or equal to page_size parameter
   */
  rag_provider_setting_configurations: RagSearchSettingConfigurationResponse[];
}

export type ListSessionsMetadataApiV1TracesSessionsGetData = SessionListResponse;

export type ListSessionsMetadataApiV1TracesSessionsGetError = HTTPValidationError;

export interface ListSessionsMetadataApiV1TracesSessionsGetParams {
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
  /**
   * User Ids
   * User IDs to filter on. Optional.
   */
  user_ids?: string[];
}

export type ListSpansMetadataApiV1TracesSpansGetData = SpanListResponse;

export type ListSpansMetadataApiV1TracesSpansGetError = HTTPValidationError;

export interface ListSpansMetadataApiV1TracesSpansGetParams {
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
  /**
   * User Ids
   * User IDs to filter on. Optional.
   */
  user_ids?: string[];
}

export type ListTransformsApiV2DatasetsDatasetIdTransformsGetData = ListDatasetTransformsResponse;

export type ListTransformsApiV2DatasetsDatasetIdTransformsGetError = HTTPValidationError;

export type ListUsersMetadataApiV1TracesUsersGetData = TraceUserListResponse;

export type ListUsersMetadataApiV1TracesUsersGetError = HTTPValidationError;

export interface ListUsersMetadataApiV1TracesUsersGetParams {
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
export type MessageRole = "developer" | "system" | "user" | "assistant" | "tool";

/**
 * MetadataQuery
 * Define which metadata should be returned in the query's results.
 */
export interface MetadataQuery {
  /**
   * Certainty
   * @default false
   */
  certainty?: boolean;
  /**
   * Creation Time
   * @default false
   */
  creation_time?: boolean;
  /**
   * Distance
   * @default false
   */
  distance?: boolean;
  /**
   * Explain Score
   * @default false
   */
  explain_score?: boolean;
  /**
   * Is Consistent
   * @default false
   */
  is_consistent?: boolean;
  /**
   * Last Update Time
   * @default false
   */
  last_update_time?: boolean;
  /**
   * Score
   * @default false
   */
  score?: boolean;
}

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

/** ModelProvider */
export type ModelProvider = "anthropic" | "openai" | "gemini";

/** ModelProviderList */
export interface ModelProviderList {
  /**
   * Providers
   * List of model providers
   */
  providers: ModelProviderResponse[];
}

/** ModelProviderModelList */
export interface ModelProviderModelList {
  /**
   * Available Models
   * Available models from the provider
   */
  available_models: string[];
  /** Provider of the models */
  provider: ModelProvider;
}

/** ModelProviderResponse */
export interface ModelProviderResponse {
  /**
   * Enabled
   * Whether the provider is enabled with credentials
   */
  enabled: boolean;
  /** The model provider */
  provider: ModelProvider;
}

/** _MultiTargetVectorJoin */
export interface MultiTargetVectorJoin {
  /** Define how multi target vector searches should be combined. */
  combination: MultiTargetVectorJoinEnum;
  /** Target Vectors */
  target_vectors: string[];
  /** Weights */
  weights?: Record<string, number | number[]> | null;
}

/**
 * _MultiTargetVectorJoinEnum
 * Define how multi target vector searches should be combined.
 */
export type MultiTargetVectorJoinEnum = 1 | 2 | 3 | 4 | 5;

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
  /**
   * Completion Token Cost
   * Cost of completion tokens in USD
   */
  completion_token_cost?: number | null;
  /**
   * Completion Token Count
   * Number of completion tokens
   */
  completion_token_count?: number | null;
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
   * Input Content
   * Span input value from raw_data.attributes.input.value
   */
  input_content?: string | null;
  /**
   * Metric Results
   * List of metric results for this span
   * @default []
   */
  metric_results?: MetricResultResponse[];
  /**
   * Output Content
   * Span output value from raw_data.attributes.output.value
   */
  output_content?: string | null;
  /** Parent Span Id */
  parent_span_id?: string | null;
  /**
   * Prompt Token Cost
   * Cost of prompt tokens in USD
   */
  prompt_token_cost?: number | null;
  /**
   * Prompt Token Count
   * Number of prompt tokens
   */
  prompt_token_count?: number | null;
  /** Raw Data */
  raw_data: Record<string, any>;
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
  /** Task Id */
  task_id?: string | null;
  /**
   * Total Token Cost
   * Total cost in USD
   */
  total_token_cost?: number | null;
  /**
   * Total Token Count
   * Total number of tokens
   */
  total_token_count?: number | null;
  /** Trace Id */
  trace_id: string;
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
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

/** NewDatasetRequest */
export interface NewDatasetRequest {
  /**
   * Description
   * Description of the dataset.
   */
  description?: string | null;
  /**
   * Metadata
   * Any metadata to include that describes additional information about the dataset.
   */
  metadata?: Record<string, any> | null;
  /**
   * Name
   * Name of the dataset.
   */
  name: string;
}

/** NewDatasetTransformRequest */
export interface NewDatasetTransformRequest {
  /**
   * Definition
   * Transform definition in JSON format specifying extraction rules.
   */
  definition: Record<string, any>;
  /**
   * Description
   * Description of the transform.
   */
  description?: string | null;
  /**
   * Name
   * Name of the transform.
   */
  name: string;
}

/** NewDatasetVersionRequest */
export interface NewDatasetVersionRequest {
  /**
   * Rows To Add
   * List of rows to be added to the new dataset version.
   */
  rows_to_add: NewDatasetVersionRowRequest[];
  /**
   * Rows To Delete
   * List of IDs of rows to be deleted from the new dataset version.
   */
  rows_to_delete: string[];
  /**
   * Rows To Delete Filter
   * Optional list of column name and value filters. Rows matching ALL specified column name-value pairs (AND condition) will be deleted from the new dataset version. This filter is applied in addition to rows_to_delete.
   */
  rows_to_delete_filter?: NewDatasetVersionRowColumnItemRequest[] | null;
  /**
   * Rows To Update
   * List of IDs of rows to be updated in the new dataset version with their new values. Should include the value in the row for every column in the dataset, not just the updated column values.
   */
  rows_to_update: NewDatasetVersionUpdateRowRequest[];
}

/**
 * NewDatasetVersionRowColumnItemRequest
 * Represents a single column-value pair in a dataset row.
 */
export interface NewDatasetVersionRowColumnItemRequest {
  /**
   * Column Name
   * Name of column.
   */
  column_name: string;
  /**
   * Column Value
   * Value of column for the row.
   */
  column_value: string;
}

/**
 * NewDatasetVersionRowRequest
 * Represents a row to be added to a dataset version.
 */
export interface NewDatasetVersionRowRequest {
  /**
   * Data
   * List of column-value pairs in the new dataset row.
   */
  data: NewDatasetVersionRowColumnItemRequest[];
}

/**
 * NewDatasetVersionUpdateRowRequest
 * Represents a row to be updated in a dataset version.
 */
export interface NewDatasetVersionUpdateRowRequest {
  /**
   * Data
   * List of column-value pairs in the updated row.
   */
  data: NewDatasetVersionRowColumnItemRequest[];
  /**
   * Id
   * UUID of row to be updated.
   * @format uuid
   */
  id: string;
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
 * NotebookDetail
 * Detailed notebook information
 */
export interface NotebookDetail {
  /**
   * Created At
   * ISO timestamp when created
   */
  created_at: string;
  /**
   * Description
   * Description
   */
  description?: string | null;
  /**
   * Experiments
   * History of experiments run from this notebook
   */
  experiments: PromptExperimentSummary[];
  /**
   * Id
   * Notebook ID
   */
  id: string;
  /**
   * Name
   * Notebook name
   */
  name: string;
  /** Current draft state */
  state: NotebookStateOutput;
  /**
   * Task Id
   * Associated task ID
   */
  task_id: string;
  /**
   * Updated At
   * ISO timestamp when last updated
   */
  updated_at: string;
}

/**
 * NotebookListResponse
 * Paginated list of notebooks
 */
export interface NotebookListResponse {
  /**
   * Data
   * List of notebook summaries
   */
  data: NotebookSummary[];
  /**
   * Page
   * Current page number (0-indexed)
   */
  page: number;
  /**
   * Page Size
   * Number of items per page
   */
  page_size: number;
  /**
   * Total Count
   * Total number of notebooks
   */
  total_count: number;
  /**
   * Total Pages
   * Total number of pages
   */
  total_pages: number;
}

/**
 * NotebookState
 * Draft state of a notebook - mirrors experiment config but all fields optional.
 */
export interface NotebookStateInput {
  /** Dataset reference */
  dataset_ref?: DatasetRef | null;
  /**
   * Dataset Row Filter
   * Optional list of column name and value filters. Only rows matching ALL specified column name-value pairs (AND condition) will be included.
   */
  dataset_row_filter?: NewDatasetVersionRowColumnItemRequest[] | null;
  /**
   * Eval List
   * List of evaluations
   */
  eval_list?: EvalRefInput[] | null;
  /**
   * Prompt Configs
   * List of prompt configurations
   */
  prompt_configs?:
    | (
        | ({
            type: "saved";
          } & SavedPromptConfig)
        | ({
            type: "unsaved";
          } & UnsavedPromptConfig)
      )[]
    | null;
  /**
   * Prompt Variable Mapping
   * Variable mappings for prompts
   */
  prompt_variable_mapping?: PromptVariableMappingInput[] | null;
}

/**
 * NotebookState
 * Draft state of a notebook - mirrors experiment config but all fields optional.
 */
export interface NotebookStateOutput {
  /** Dataset reference */
  dataset_ref?: DatasetRef | null;
  /**
   * Dataset Row Filter
   * Optional list of column name and value filters. Only rows matching ALL specified column name-value pairs (AND condition) will be included.
   */
  dataset_row_filter?: NewDatasetVersionRowColumnItemRequest[] | null;
  /**
   * Eval List
   * List of evaluations
   */
  eval_list?: EvalRefOutput[] | null;
  /**
   * Prompt Configs
   * List of prompt configurations
   */
  prompt_configs?:
    | (
        | ({
            type: "saved";
          } & SavedPromptConfig)
        | ({
            type: "unsaved";
          } & UnsavedPromptConfig)
      )[]
    | null;
  /**
   * Prompt Variable Mapping
   * Variable mappings for prompts
   */
  prompt_variable_mapping?: PromptVariableMappingOutput[] | null;
}

/**
 * NotebookSummary
 * Summary of a notebook
 */
export interface NotebookSummary {
  /**
   * Created At
   * ISO timestamp when created
   */
  created_at: string;
  /**
   * Description
   * Description
   */
  description?: string | null;
  /**
   * Id
   * Notebook ID
   */
  id: string;
  /**
   * Latest Run Id
   * ID of most recent experiment run
   */
  latest_run_id?: string | null;
  /** Status of most recent experiment */
  latest_run_status?: ExperimentStatus | null;
  /**
   * Name
   * Notebook name
   */
  name: string;
  /**
   * Run Count
   * Number of experiments run from this notebook
   */
  run_count: number;
  /**
   * Task Id
   * Associated task ID
   */
  task_id: string;
  /**
   * Updated At
   * ISO timestamp when last updated
   */
  updated_at: string;
}

/**
 * OpenAIMessage
 * The message schema class for the prompts playground.
 * This class adheres to OpenAI's message schema.
 */
export interface OpenAIMessageInput {
  /**
   * Content
   * Content of the message
   */
  content?: string | OpenAIMessageItem[] | null;
  /**
   * Name
   * An optional name for the participant. Provides the model information to differentiate between participants of the same role.
   */
  name?: string | null;
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
  tool_calls?: ToolCall[] | null;
}

/** OpenAIMessageItem */
export interface OpenAIMessageItem {
  /** Image URL content of the message if type is 'image_url' */
  image_url?: ImageURL | null;
  /** Input audio content of the message if type is 'input_audio' */
  input_audio?: InputAudio | null;
  /**
   * Text
   * Text content of the message if type is 'text'
   */
  text?: string | null;
  /** Type of the message (either 'text', 'image_url', or 'input_audio') */
  type: OpenAIMessageType;
}

/**
 * OpenAIMessage
 * The message schema class for the prompts playground.
 * This class adheres to OpenAI's message schema.
 */
export interface OpenAIMessageOutput {
  /**
   * Content
   * Content of the message
   */
  content?: string | OpenAIMessageItem[] | null;
  /**
   * Name
   * An optional name for the participant. Provides the model information to differentiate between participants of the same role.
   */
  name?: string | null;
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
  tool_calls?: ToolCall[] | null;
}

/** OpenAIMessageType */
export type OpenAIMessageType = "text" | "image_url" | "input_audio";

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

/** Page[ConversationBaseResponse] */
export interface PageConversationBaseResponse {
  /** Items */
  items: ConversationBaseResponse[];
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

/**
 * PromptCompletionRequest
 * Request schema for running an agentic prompt
 */
export interface PromptCompletionRequest {
  /**
   * Stream
   * Whether to stream the response
   * @default false
   */
  stream?: boolean | null;
  /**
   * Strict
   * Whether to enforce strict validation of variables. If True, any variables that are found in the prompt but not in the variables list will raise an error.
   * @default false
   */
  strict?: boolean | null;
  /**
   * Variables
   * List of VariableTemplateValue fields that specify the values to fill in for each template in the prompt
   * @default []
   */
  variables?: VariableTemplateValue[] | null;
}

/**
 * PromptEvalResultSummaries
 * Summary of evaluation results for a prompt version
 */
export interface PromptEvalResultSummaries {
  /**
   * Eval Results
   * Results for each evaluation run on this prompt version
   */
  eval_results: EvalResultSummary[];
  /**
   * Prompt Key
   * Prompt key: 'saved:name:version' or 'unsaved:auto_name'
   */
  prompt_key?: string | null;
  /**
   * Prompt Name
   * Name of the prompt (for saved prompts, or auto_name for unsaved)
   */
  prompt_name?: string | null;
  /**
   * Prompt Type
   * Type: 'saved' or 'unsaved'
   */
  prompt_type?: string | null;
  /**
   * Prompt Version
   * Version of the prompt (for saved prompts only)
   */
  prompt_version?: string | null;
}

/**
 * PromptExperimentDetail
 * Detailed information about a prompt experiment
 */
export interface PromptExperimentDetail {
  /**
   * Completed Rows
   * Number of test rows completed successfully
   */
  completed_rows: number;
  /**
   * Created At
   * ISO timestamp when experiment was created
   */
  created_at: string;
  /** Reference to the dataset used */
  dataset_ref: DatasetRef;
  /**
   * Dataset Row Filter
   * Optional list of column name and value filters applied to dataset rows. Only rows matching ALL specified column name-value pairs (AND condition) were included in the experiment.
   */
  dataset_row_filter?: NewDatasetVersionRowColumnItemRequest[] | null;
  /**
   * Description
   * Description of the experiment
   */
  description?: string | null;
  /**
   * Eval List
   * List of evaluations being run
   */
  eval_list: EvalRefOutput[];
  /**
   * Failed Rows
   * Number of test rows that failed
   */
  failed_rows: number;
  /**
   * Finished At
   * ISO timestamp when experiment finished
   */
  finished_at?: string | null;
  /**
   * Id
   * Unique identifier for the experiment
   */
  id: string;
  /**
   * Name
   * Name of the experiment
   */
  name: string;
  /**
   * Prompt Configs
   * List of prompts being tested
   */
  prompt_configs: (
    | ({
        type: "saved";
      } & SavedPromptConfig)
    | ({
        type: "unsaved";
      } & UnsavedPromptConfig)
  )[];
  /**
   * Prompt Variable Mapping
   * Shared variable mapping for all prompts
   */
  prompt_variable_mapping: PromptVariableMappingOutput[];
  /** Current status of the experiment */
  status: ExperimentStatus;
  /** Summary of results across all test cases */
  summary_results: SummaryResults;
  /**
   * Total Cost
   * Total cost of running the experiment
   */
  total_cost?: string | null;
  /**
   * Total Rows
   * Total number of test rows in the experiment
   */
  total_rows: number;
}

/**
 * PromptExperimentListResponse
 * Paginated list of prompt experiments
 */
export interface PromptExperimentListResponse {
  /**
   * Data
   * List of prompt experiment summaries
   */
  data: PromptExperimentSummary[];
  /**
   * Page
   * Current page number (0-indexed)
   */
  page: number;
  /**
   * Page Size
   * Number of items per page
   */
  page_size: number;
  /**
   * Total Count
   * Total number of prompt experiments
   */
  total_count: number;
  /**
   * Total Pages
   * Total number of pages
   */
  total_pages: number;
}

/**
 * PromptExperimentSummary
 * Summary of a prompt experiment
 */
export interface PromptExperimentSummary {
  /**
   * Completed Rows
   * Number of test rows completed successfully
   */
  completed_rows: number;
  /**
   * Created At
   * ISO timestamp when experiment was created
   */
  created_at: string;
  /**
   * Description
   * Description of the experiment
   */
  description?: string | null;
  /**
   * Failed Rows
   * Number of test rows that failed
   */
  failed_rows: number;
  /**
   * Finished At
   * ISO timestamp when experiment finished
   */
  finished_at?: string | null;
  /**
   * Id
   * Unique identifier for the experiment
   */
  id: string;
  /**
   * Name
   * Name of the experiment
   */
  name: string;
  /**
   * Prompt Configs
   * List of prompts being tested
   */
  prompt_configs: (
    | ({
        type: "saved";
      } & SavedPromptConfig)
    | ({
        type: "unsaved";
      } & UnsavedPromptConfig)
  )[];
  /** Current status of the experiment */
  status: ExperimentStatus;
  /**
   * Total Cost
   * Total cost of running the experiment
   */
  total_cost?: string | null;
  /**
   * Total Rows
   * Total number of test rows in the experiment
   */
  total_rows: number;
}

/**
 * PromptOutput
 * Output from a prompt execution
 */
export interface PromptOutput {
  /**
   * Content
   * Content of the prompt response
   */
  content: string;
  /**
   * Cost
   * Cost of the prompt execution
   */
  cost: string;
  /**
   * Tool Calls
   * Tool calls made by the prompt
   */
  tool_calls?: any[];
}

/**
 * PromptResult
 * Results from a prompt execution with evals
 */
export interface PromptResult {
  /**
   * Evals
   * Evaluation results for this prompt output
   */
  evals: EvalExecution[];
  /**
   * Name
   * Name of the prompt (for saved prompts)
   */
  name?: string | null;
  /** Output from the prompt (None if not yet executed) */
  output?: PromptOutput | null;
  /**
   * Prompt Key
   * Prompt key: 'saved:name:version' or 'unsaved:auto_name'
   */
  prompt_key: string;
  /**
   * Prompt Type
   * Type: 'saved' or 'unsaved'
   */
  prompt_type: string;
  /**
   * Rendered Prompt
   * Prompt with variables replaced
   */
  rendered_prompt: string;
  /**
   * Version
   * Version of the prompt (for saved prompts)
   */
  version?: string | null;
}

/** PromptValidationRequest */
export interface PromptValidationRequest {
  /**
   * Conversation Id
   * The unique conversation ID this prompt belongs to. All prompts and responses from this         conversation can later be reconstructed with this ID.
   */
  conversation_id?: string | null;
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

/**
 * PromptVariableMapping
 * Mapping of a prompt variable to a dataset column source
 */
export interface PromptVariableMappingInput {
  /** Dataset column source */
  source: DatasetColumnVariableSource;
  /**
   * Variable Name
   * Name of the prompt variable
   */
  variable_name: string;
}

/**
 * PromptVariableMapping
 * Mapping of a prompt variable to a dataset column source
 */
export interface PromptVariableMappingOutput {
  /** Dataset column source */
  source: DatasetColumnVariableSource;
  /**
   * Variable Name
   * Name of the prompt variable
   */
  variable_name: string;
}

/**
 * PromptVersionResult
 * Result for a specific prompt version within a test case
 */
export interface PromptVersionResult {
  /**
   * Dataset Row Id
   * ID of the dataset row
   */
  dataset_row_id: string;
  /**
   * Evals
   * Evaluation results for this prompt output
   */
  evals: EvalExecution[];
  /** Output from the prompt (None if not yet executed) */
  output?: PromptOutput | null;
  /**
   * Prompt Input Variables
   * Input variables for the prompt
   */
  prompt_input_variables: InputVariable[];
  /**
   * Rendered Prompt
   * Prompt with variables replaced
   */
  rendered_prompt: string;
  /** Status of the test case */
  status: TestCaseStatus;
  /**
   * Total Cost
   * Total cost for this specific prompt execution
   */
  total_cost?: string | null;
}

/**
 * PromptVersionResultListResponse
 * Paginated list of results for a specific prompt version
 */
export interface PromptVersionResultListResponse {
  /**
   * Data
   * List of results for the prompt version
   */
  data: PromptVersionResult[];
  /**
   * Page
   * Current page number (0-indexed)
   */
  page: number;
  /**
   * Page Size
   * Number of items per page
   */
  page_size: number;
  /**
   * Total Count
   * Total number of results
   */
  total_count: number;
  /**
   * Total Pages
   * Total number of pages
   */
  total_pages: number;
}

/** PutModelProviderCredentials */
export interface PutModelProviderCredentials {
  /**
   * Api Key
   * The API key for the provider.
   * @format password
   */
  api_key: string;
}

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
  target?: InferenceFeedbackTarget | InferenceFeedbackTarget[] | null;
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

/** RagAPIKeyAuthenticationProviderEnum */
export type RagAPIKeyAuthenticationProviderEnum = "weaviate";

/** RagHybridSearchSettingRequest */
export interface RagHybridSearchSettingRequest {
  /** Settings for the hybrid search request to the vector database. */
  settings: WeaviateHybridSearchSettingsRequest;
}

/** RagKeywordSearchSettingRequest */
export interface RagKeywordSearchSettingRequest {
  /** Settings for the keyword search request to the vector database. */
  settings: WeaviateKeywordSearchSettingsRequest;
}

/** RagProviderAuthenticationMethodEnum */
export type RagProviderAuthenticationMethodEnum = "api_key";

/** RagProviderCollectionResponse */
export interface RagProviderCollectionResponse {
  /**
   * Description
   * Description of the collection.
   */
  description?: string | null;
  /**
   * Identifier
   * Unique identifier of the collection.
   */
  identifier: string;
}

/** RagProviderConfigurationRequest */
export interface RagProviderConfigurationRequest {
  /** Configuration of the authentication strategy. */
  authentication_config: ApiKeyRagAuthenticationConfigRequest;
  /**
   * Description
   * Description of RAG provider configuration.
   */
  description?: string | null;
  /**
   * Name
   * Name of RAG provider configuration.
   */
  name: string;
}

/** RagProviderConfigurationResponse */
export interface RagProviderConfigurationResponse {
  /** Configuration of the authentication strategy. */
  authentication_config: ApiKeyRagAuthenticationConfigResponse;
  /**
   * Created At
   * Time the RAG provider configuration was created in unix milliseconds
   */
  created_at: number;
  /**
   * Description
   * Description of RAG provider configuration.
   */
  description?: string | null;
  /**
   * Id
   * Unique identifier of the RAG provider configuration.
   * @format uuid
   */
  id: string;
  /**
   * Name
   * Name of RAG provider configuration.
   */
  name: string;
  /**
   * Task Id
   * ID of parent task.
   */
  task_id: string;
  /**
   * Updated At
   * Time the RAG provider configuration was updated in unix milliseconds
   */
  updated_at: number;
}

/** RagProviderConfigurationUpdateRequest */
export interface RagProviderConfigurationUpdateRequest {
  /** Configuration of the authentication strategy. */
  authentication_config?: ApiKeyRagAuthenticationConfigUpdateRequest | null;
  /**
   * Description
   * Description of RAG provider configuration.
   */
  description?: string | null;
  /**
   * Name
   * Name of RAG provider configuration.
   */
  name?: string | null;
}

/** RagProviderQueryResponse */
export interface RagProviderQueryResponse {
  /** Response from Weaviate similarity text search */
  response: WeaviateQueryResults;
}

/** RagProviderTestConfigurationRequest */
export interface RagProviderTestConfigurationRequest {
  /** Configuration of the authentication strategy. */
  authentication_config: ApiKeyRagAuthenticationConfigRequest;
}

/** RagSearchSettingConfigurationNewVersionRequest */
export interface RagSearchSettingConfigurationNewVersionRequest {
  /**
   * Settings
   * Settings configuration for a search request to a RAG provider.
   */
  settings:
    | WeaviateHybridSearchSettingsConfigurationRequest
    | WeaviateKeywordSearchSettingsConfigurationRequest
    | WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest;
  /**
   * Tags
   * List of tags to configure for this version of the search settings configuration.
   */
  tags?: string[];
}

/** RagSearchSettingConfigurationRequest */
export interface RagSearchSettingConfigurationRequest {
  /**
   * Description
   * Description of the search setting configuration.
   */
  description?: string | null;
  /**
   * Name
   * Name of the search setting configuration.
   */
  name: string;
  /**
   * Rag Provider Id
   * ID of the rag provider to use with the settings.
   * @format uuid
   */
  rag_provider_id: string;
  /**
   * Settings
   * Settings configuration for a search request to a RAG provider.
   */
  settings:
    | WeaviateHybridSearchSettingsConfigurationRequest
    | WeaviateKeywordSearchSettingsConfigurationRequest
    | WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest;
  /**
   * Tags
   * List of tags to configure for this version of the search settings configuration.
   */
  tags?: string[];
}

/** RagSearchSettingConfigurationResponse */
export interface RagSearchSettingConfigurationResponse {
  /**
   * All Possible Tags
   * Set of all tags applied for any version of the settings configuration.
   */
  all_possible_tags?: string[] | null;
  /**
   * Created At
   * Time the RAG settings configuration was created in unix milliseconds.
   */
  created_at: number;
  /**
   * Description
   * Description of the setting configuration.
   */
  description?: string | null;
  /**
   * Id
   * ID of the setting configuration.
   * @format uuid
   */
  id: string;
  /** The latest version of the settings configuration. */
  latest_version: RagSearchSettingConfigurationVersionResponse;
  /**
   * Latest Version Number
   * The latest version number of the settings configuration.
   */
  latest_version_number: number;
  /**
   * Name
   * Name of the setting configuration.
   */
  name: string;
  /**
   * Rag Provider Id
   * ID of the rag provider to use with the settings. None if initial rag provider configuration was deleted.
   */
  rag_provider_id?: string | null;
  /**
   * Task Id
   * ID of the parent task.
   */
  task_id: string;
  /**
   * Updated At
   * Time the RAG settings configuration was updated in unix milliseconds. Will be updated if a new version of the configuration was created.
   */
  updated_at: number;
}

/** RagSearchSettingConfigurationUpdateRequest */
export interface RagSearchSettingConfigurationUpdateRequest {
  /**
   * Description
   * Description of the setting configuration.
   */
  description?: string | null;
  /**
   * Name
   * Name of the setting configuration.
   */
  name?: string | null;
  /**
   * Rag Provider Id
   * ID of the rag provider configuration to use the settings with.
   */
  rag_provider_id?: string | null;
}

/** RagSearchSettingConfigurationVersionResponse */
export interface RagSearchSettingConfigurationVersionResponse {
  /**
   * Created At
   * Time the RAG provider settings configuration version was created in unix milliseconds
   */
  created_at: number;
  /**
   * Deleted At
   * Time the RAG provider settings configuration version was soft-deleted in unix milliseconds
   */
  deleted_at?: number | null;
  /**
   * Setting Configuration Id
   * ID of the parent setting configuration.
   * @format uuid
   */
  setting_configuration_id: string;
  /**
   * Settings
   * Settings configuration for a search request to a RAG provider. None if version has been soft-deleted.
   */
  settings?:
    | WeaviateHybridSearchSettingsConfigurationResponse
    | WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse
    | WeaviateKeywordSearchSettingsConfigurationResponse
    | null;
  /**
   * Tags
   * Optional list of tags configured for this version of the settings configuration.
   */
  tags?: string[] | null;
  /**
   * Updated At
   * Time the RAG provider settings configuration version was updated in unix milliseconds
   */
  updated_at: number;
  /**
   * Version Number
   * Version number of the setting configuration.
   */
  version_number: number;
}

/** RagSearchSettingConfigurationVersionUpdateRequest */
export interface RagSearchSettingConfigurationVersionUpdateRequest {
  /**
   * Tags
   * List of tags to update this version of the search settings configuration with.
   */
  tags: string[];
}

/** RagVectorSimilarityTextSearchSettingRequest */
export interface RagVectorSimilarityTextSearchSettingRequest {
  /** Settings for the similarity text search request to the vector database. */
  settings: WeaviateVectorSimilarityTextSearchSettingsRequest;
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

export type RenderSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionRendersPostData = RenderedPromptResponse;

export type RenderSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionRendersPostError = HTTPValidationError;

export type RenderUnsavedAgenticPromptApiV1PromptRendersPostData = RenderedPromptResponse;

export type RenderUnsavedAgenticPromptApiV1PromptRendersPostError = HTTPValidationError;

/** RenderedPromptResponse */
export interface RenderedPromptResponse {
  /**
   * Messages
   * List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])
   */
  messages: OpenAIMessageOutput[];
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

export type RotateSecretsApiV1SecretsRotationPostData = any;

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
export type RuleResultEnum = "Pass" | "Fail" | "Skipped" | "Unavailable" | "Partially Unavailable" | "Model Not Available";

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

export type RunSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionCompletionsPostData = AgenticPromptRunResponse;

export type RunSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionCompletionsPostError = HTTPValidationError;

export type RunSavedLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionCompletionsPostData = LLMEvalRunResponse;

export type RunSavedLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionCompletionsPostError = HTTPValidationError;

export type SaveAgenticPromptApiV1TasksTaskIdPromptsPromptNamePostData = AgenticPrompt;

export type SaveAgenticPromptApiV1TasksTaskIdPromptsPromptNamePostError = HTTPValidationError;

export type SaveLlmEvalApiV1TasksTaskIdLlmEvalsEvalNamePostData = LLMEval;

export type SaveLlmEvalApiV1TasksTaskIdLlmEvalsEvalNamePostError = HTTPValidationError;

/**
 * SavedPromptConfig
 * Configuration for a saved prompt
 */
export interface SavedPromptConfig {
  /**
   * Name
   * Name of the saved prompt
   */
  name: string;
  /**
   * Type
   * @default "saved"
   */
  type?: "saved";
  /**
   * Version
   * Version of the saved prompt
   */
  version: number;
}

/**
 * SavedPromptRenderingRequest
 * Request schema for rendering an unsaved agentic prompt with variables
 */
export interface SavedPromptRenderingRequest {
  /** Rendering configuration for the unsaved prompt */
  completion_request?: VariableRenderingRequest;
}

/** SearchDatasetsResponse */
export interface SearchDatasetsResponse {
  /**
   * Count
   * The total number of datasets matching the parameters.
   */
  count: number;
  /**
   * Datasets
   * List of datasets matching the search filters. Length is less than or equal to page_size parameter
   */
  datasets: DatasetResponse[];
}

/** SearchRagProviderCollectionsResponse */
export interface SearchRagProviderCollectionsResponse {
  /**
   * Count
   * The total number of RAG provider collections matching the parameters.
   */
  count: number;
  /** Rag Provider Collections */
  rag_provider_collections: RagProviderCollectionResponse[];
}

/** SearchRagProviderConfigurationsResponse */
export interface SearchRagProviderConfigurationsResponse {
  /**
   * Count
   * The total number of RAG provider configurations matching the parameters.
   */
  count: number;
  /**
   * Rag Provider Configurations
   * List of RAG provider configurations matching the search filters. Length is less than or equal to page_size parameter
   */
  rag_provider_configurations: RagProviderConfigurationResponse[];
}

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
   * Completion Token Cost
   * Cost of completion tokens in USD
   */
  completion_token_cost?: number | null;
  /**
   * Completion Token Count
   * Number of completion tokens
   */
  completion_token_count?: number | null;
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
   * Prompt Token Cost
   * Cost of prompt tokens in USD
   */
  prompt_token_cost?: number | null;
  /**
   * Prompt Token Count
   * Number of prompt tokens
   */
  prompt_token_count?: number | null;
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
   * Total Token Cost
   * Total cost in USD
   */
  total_token_cost?: number | null;
  /**
   * Total Token Count
   * Total number of tokens
   */
  total_token_count?: number | null;
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
  /**
   * User Id
   * User ID if available
   */
  user_id?: string | null;
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

export type SetModelProviderApiV1ModelProvidersProviderPutData = any;

export type SetModelProviderApiV1ModelProvidersProviderPutError = HTTPValidationError;

export type SetNotebookStateApiV1NotebooksNotebookIdStatePutData = NotebookDetail;

export type SetNotebookStateApiV1NotebooksNotebookIdStatePutError = HTTPValidationError;

/**
 * SetNotebookStateRequest
 * Request to set the notebook state
 */
export interface SetNotebookStateRequest {
  /** New state for the notebook */
  state: NotebookStateInput;
}

export type SoftDeleteLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionDeleteData = any;

export type SoftDeleteLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionDeleteError = HTTPValidationError;

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
   * Completion Token Cost
   * Cost of completion tokens in USD
   */
  completion_token_cost?: number | null;
  /**
   * Completion Token Count
   * Number of completion tokens
   */
  completion_token_count?: number | null;
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
   * Input Content
   * Span input value from raw_data.attributes.input.value
   */
  input_content?: string | null;
  /**
   * Output Content
   * Span output value from raw_data.attributes.output.value
   */
  output_content?: string | null;
  /**
   * Parent Span Id
   * Parent span ID
   */
  parent_span_id?: string | null;
  /**
   * Prompt Token Cost
   * Cost of prompt tokens in USD
   */
  prompt_token_cost?: number | null;
  /**
   * Prompt Token Count
   * Number of prompt tokens
   */
  prompt_token_count?: number | null;
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
   * Total Token Cost
   * Total cost in USD
   */
  total_token_cost?: number | null;
  /**
   * Total Token Count
   * Total number of tokens
   */
  total_token_count?: number | null;
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
  /**
   * User Id
   * User ID if available
   */
  user_id?: string | null;
}

/** SpanWithMetricsResponse */
export interface SpanWithMetricsResponse {
  /**
   * Completion Token Cost
   * Cost of completion tokens in USD
   */
  completion_token_cost?: number | null;
  /**
   * Completion Token Count
   * Number of completion tokens
   */
  completion_token_count?: number | null;
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
   * Input Content
   * Span input value from raw_data.attributes.input.value
   */
  input_content?: string | null;
  /**
   * Metric Results
   * List of metric results for this span
   * @default []
   */
  metric_results?: MetricResultResponse[];
  /**
   * Output Content
   * Span output value from raw_data.attributes.output.value
   */
  output_content?: string | null;
  /** Parent Span Id */
  parent_span_id?: string | null;
  /**
   * Prompt Token Cost
   * Cost of prompt tokens in USD
   */
  prompt_token_cost?: number | null;
  /**
   * Prompt Token Count
   * Number of prompt tokens
   */
  prompt_token_count?: number | null;
  /** Raw Data */
  raw_data: Record<string, any>;
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
  /** Task Id */
  task_id?: string | null;
  /**
   * Total Token Cost
   * Total cost in USD
   */
  total_token_cost?: number | null;
  /**
   * Total Token Count
   * Total number of tokens
   */
  total_token_count?: number | null;
  /** Trace Id */
  trace_id: string;
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
}

/** StreamOptions */
export interface StreamOptions {
  /**
   * Include Usage
   * Whether to include usage information in the stream
   */
  include_usage?: boolean | null;
}

/**
 * SummaryResults
 * Summary results across all prompt versions and evaluations
 */
export interface SummaryResults {
  /**
   * Prompt Eval Summaries
   * Summary for each prompt version tested
   */
  prompt_eval_summaries: PromptEvalResultSummaries[];
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

/**
 * TestCase
 * Individual test case result
 */
export interface TestCase {
  /**
   * Dataset Row Id
   * ID of the dataset row
   */
  dataset_row_id: string;
  /**
   * Prompt Input Variables
   * Input variables for the prompt
   */
  prompt_input_variables: InputVariable[];
  /**
   * Prompt Results
   * Results for each prompt version tested
   */
  prompt_results: PromptResult[];
  /** Status of the test case */
  status: TestCaseStatus;
  /**
   * Total Cost
   * Total cost for this test case
   */
  total_cost?: string | null;
}

/**
 * TestCaseListResponse
 * Paginated list of test cases
 */
export interface TestCaseListResponse {
  /**
   * Data
   * List of test cases
   */
  data: TestCase[];
  /**
   * Page
   * Current page number (0-indexed)
   */
  page: number;
  /**
   * Page Size
   * Number of items per page
   */
  page_size: number;
  /**
   * Total Count
   * Total number of test cases
   */
  total_count: number;
  /**
   * Total Pages
   * Total number of pages
   */
  total_pages: number;
}

/**
 * TestCaseStatus
 * Status of a test case
 */
export type TestCaseStatus = "queued" | "running" | "evaluating" | "failed" | "completed";

export type TestRagProviderConnectionApiV1TasksTaskIdRagProvidersTestConnectionPostData = ConnectionCheckResult;

export type TestRagProviderConnectionApiV1TasksTaskIdRagProvidersTestConnectionPostError = HTTPValidationError;

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

/** ToolCall */
export interface ToolCall {
  /** Function details */
  function: ToolCallFunction;
  /**
   * Id
   * Unique identifier for the tool call
   */
  id: string;
  /**
   * Type
   * The type of tool call. Currently the only type supported is 'function'.
   * @default "function"
   */
  type?: string;
}

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

/** ToolChoice */
export interface ToolChoice {
  /** The tool choice fucntion name */
  function?: ToolChoiceFunction | null;
  /**
   * Type
   * The type of tool choice. Should always be 'function'
   * @default "function"
   */
  type?: string;
}

/** ToolChoiceEnum */
export type ToolChoiceEnum = "auto" | "none" | "required";

/** ToolChoiceFunction */
export interface ToolChoiceFunction {
  /**
   * Name
   * The name of the function
   */
  name: string;
}

/** ToolClassEnum */
export type ToolClassEnum = 0 | 1 | 2;

/** ToolFunction */
export interface ToolFunctionInput {
  /**
   * Description
   * Description of what the tool does
   */
  description?: string | null;
  /**
   * Name
   * The name of the tool/function
   */
  name: string;
  /** The function's parameter schema */
  parameters?: JsonSchema | null;
}

/** ToolFunction */
export interface ToolFunctionOutput {
  /**
   * Description
   * Description of what the tool does
   */
  description?: string | null;
  /**
   * Name
   * The name of the tool/function
   */
  name: string;
  /** The function's parameter schema */
  parameters?: JsonSchema | null;
}

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
  /** Annotation for the trace. */
  annotation?: AgenticAnnotationResponse | null;
  /**
   * Completion Token Cost
   * Cost of completion tokens in USD
   */
  completion_token_cost?: number | null;
  /**
   * Completion Token Count
   * Number of completion tokens
   */
  completion_token_count?: number | null;
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
   * Input Content
   * Root span input value from trace metadata
   */
  input_content?: string | null;
  /**
   * Output Content
   * Root span output value from trace metadata
   */
  output_content?: string | null;
  /**
   * Prompt Token Cost
   * Cost of prompt tokens in USD
   */
  prompt_token_cost?: number | null;
  /**
   * Prompt Token Count
   * Number of prompt tokens
   */
  prompt_token_count?: number | null;
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
   * Total Token Cost
   * Total cost in USD
   */
  total_token_cost?: number | null;
  /**
   * Total Token Count
   * Total number of tokens
   */
  total_token_count?: number | null;
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
  /**
   * User Id
   * User ID if available
   */
  user_id?: string | null;
}

/**
 * TraceResponse
 * Response model for a single trace containing nested spans
 */
export interface TraceResponse {
  /** Annotation for this trace. */
  annotation?: AgenticAnnotationResponse | null;
  /**
   * Completion Token Cost
   * Cost of completion tokens in USD
   */
  completion_token_cost?: number | null;
  /**
   * Completion Token Count
   * Number of completion tokens
   */
  completion_token_count?: number | null;
  /**
   * End Time
   * End time of the latest span in this trace
   * @format date-time
   */
  end_time: string;
  /**
   * Input Content
   * Root span input value from trace metadata
   */
  input_content?: string | null;
  /**
   * Output Content
   * Root span output value from trace metadata
   */
  output_content?: string | null;
  /**
   * Prompt Token Cost
   * Cost of prompt tokens in USD
   */
  prompt_token_cost?: number | null;
  /**
   * Prompt Token Count
   * Number of prompt tokens
   */
  prompt_token_count?: number | null;
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
   * Total Token Cost
   * Total cost in USD
   */
  total_token_cost?: number | null;
  /**
   * Total Token Count
   * Total number of tokens
   */
  total_token_count?: number | null;
  /**
   * Trace Id
   * ID of the trace
   */
  trace_id: string;
}

/**
 * TraceUserListResponse
 * Response for trace user list endpoint
 */
export interface TraceUserListResponse {
  /**
   * Count
   * Total number of users matching filters
   */
  count: number;
  /**
   * Users
   * List of user metadata
   */
  users: TraceUserMetadataResponse[];
}

/**
 * TraceUserMetadataResponse
 * User summary metadata in trace context
 */
export interface TraceUserMetadataResponse {
  /**
   * Completion Token Cost
   * Cost of completion tokens in USD
   */
  completion_token_cost?: number | null;
  /**
   * Completion Token Count
   * Number of completion tokens
   */
  completion_token_count?: number | null;
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
   * Prompt Token Cost
   * Cost of prompt tokens in USD
   */
  prompt_token_cost?: number | null;
  /**
   * Prompt Token Count
   * Number of prompt tokens
   */
  prompt_token_count?: number | null;
  /**
   * Session Count
   * Number of sessions for this user
   */
  session_count: number;
  /**
   * Session Ids
   * List of session IDs for this user
   */
  session_ids: string[];
  /**
   * Span Count
   * Total number of spans for this user
   */
  span_count: number;
  /**
   * Task Id
   * Task ID this user belongs to
   */
  task_id: string;
  /**
   * Total Token Cost
   * Total cost in USD
   */
  total_token_cost?: number | null;
  /**
   * Total Token Count
   * Total number of tokens
   */
  total_token_count?: number | null;
  /**
   * Trace Count
   * Number of traces for this user
   */
  trace_count: number;
  /**
   * Trace Ids
   * List of trace IDs for this user
   */
  trace_ids: string[];
  /**
   * User Id
   * User identifier
   */
  user_id: string;
}

/**
 * UnsavedPromptConfig
 * Configuration for an unsaved prompt
 */
export interface UnsavedPromptConfig {
  /**
   * Auto Name
   * Auto-generated name (set by backend)
   */
  auto_name?: string | null;
  /**
   * Config
   * LLM config settings
   */
  config?: Record<string, any> | null;
  /**
   * Messages
   * Prompt messages
   */
  messages: Record<string, any>[];
  /**
   * Model Name
   * LLM model name
   */
  model_name: string;
  /** LLM provider */
  model_provider: ModelProvider;
  /**
   * Tools
   * Available tools
   */
  tools?: Record<string, any>[] | null;
  /**
   * Type
   * @default "unsaved"
   */
  type?: "unsaved";
  /**
   * Variables
   * Variables (auto-detected if not provided)
   */
  variables?: string[] | null;
}

/**
 * UnsavedPromptRenderingRequest
 * Request schema for rendering an unsaved agentic prompt with variables
 */
export interface UnsavedPromptRenderingRequest {
  /** Rendering configuration for the unsaved prompt */
  completion_request?: VariableRenderingRequest;
  /**
   * Messages
   * List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])
   */
  messages: OpenAIMessageInput[];
}

/** UnsavedPromptVariablesListResponse */
export interface UnsavedPromptVariablesListResponse {
  /**
   * Variables
   * List of variables needed to run an unsaved prompt
   */
  variables: string[];
}

/**
 * UnsavedPromptVariablesRequest
 * Request schema for getting the list of variables needed from an unsaved prompt's messages
 */
export interface UnsavedPromptVariablesRequest {
  /**
   * Messages
   * List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])
   */
  messages: OpenAIMessageInput[];
}

export type UpdateDatasetApiV2DatasetsDatasetIdPatchData = DatasetResponse;

export type UpdateDatasetApiV2DatasetsDatasetIdPatchError = HTTPValidationError;

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

export type UpdateNotebookApiV1NotebooksNotebookIdPutData = NotebookDetail;

export type UpdateNotebookApiV1NotebooksNotebookIdPutError = HTTPValidationError;

/**
 * UpdateNotebookRequest
 * Request to update a notebook
 */
export interface UpdateNotebookRequest {
  /**
   * Description
   * New description
   */
  description?: string | null;
  /**
   * Name
   * New name
   */
  name?: string | null;
}

export type UpdateRagProviderApiV1RagProvidersProviderIdPatchData = RagProviderConfigurationResponse;

export type UpdateRagProviderApiV1RagProvidersProviderIdPatchError = HTTPValidationError;

export type UpdateRagSearchSettingsApiV1RagSearchSettingsSettingConfigurationIdPatchData = RagSearchSettingConfigurationResponse;

export type UpdateRagSearchSettingsApiV1RagSearchSettingsSettingConfigurationIdPatchError = HTTPValidationError;

export type UpdateRagSearchSettingsVersionApiV1RagSearchSettingsSettingConfigurationIdVersionsVersionNumberPatchData =
  RagSearchSettingConfigurationVersionResponse;

export type UpdateRagSearchSettingsVersionApiV1RagSearchSettingsSettingConfigurationIdVersionsVersionNumberPatchError = HTTPValidationError;

/** UpdateRuleRequest */
export interface UpdateRuleRequest {
  /**
   * Enabled
   * Boolean value to enable or disable the rule.
   */
  enabled: boolean;
}

export type UpdateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatchData = TaskResponse;

export type UpdateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatchError = HTTPValidationError;

export type UpdateTaskRulesApiV2TasksTaskIdRulesRuleIdPatchData = TaskResponse;

export type UpdateTaskRulesApiV2TasksTaskIdRulesRuleIdPatchError = HTTPValidationError;

export type UpdateTransformApiV2DatasetsDatasetIdTransformsTransformIdPutData = DatasetTransformResponse;

export type UpdateTransformApiV2DatasetsDatasetIdTransformsTransformIdPutError = HTTPValidationError;

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

export type ValidateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPostError = HTTPError | HTTPValidationError;

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

/** VariableRenderingRequest */
export interface VariableRenderingRequest {
  /**
   * Strict
   * Whether to enforce strict validation of variables. If True, any variables that are found in the prompt but not in the variables list will raise an error.
   * @default false
   */
  strict?: boolean | null;
  /**
   * Variables
   * List of VariableTemplateValue fields that specify the values to fill in for each template in the prompt
   * @default []
   */
  variables?: VariableTemplateValue[] | null;
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

/** WeaviateHybridSearchSettingsConfigurationRequest */
export interface WeaviateHybridSearchSettingsConfigurationRequest {
  /**
   * Alpha
   * Balance between the relative weights of the keyword and vector search. 1 is pure vector search, 0 is pure keyword search.
   * @default 0.7
   */
  alpha?: number;
  /**
   * And Operator
   * Search returns objects that contain all tokens in the search string. Cannot be used with minimum_match_or_operator. Applies to keyword search only.
   */
  and_operator?: boolean | null;
  /**
   * Auto Limit
   * Automatically limit search results to groups of objects with similar distances, stopping after auto_limit number of significant jumps.
   */
  auto_limit?: number | null;
  /**
   * Collection Name
   * Name of the vector collection used for the search.
   */
  collection_name: string;
  /** Set the fusion algorithm to use. Default is Relative Score Fusion. */
  fusion_type?: HybridFusion | null;
  /**
   * Include Vector
   * Boolean value whether to include vector embeddings in the response or can be used to specify the names of the vectors to include in the response if your collection uses named vectors. Will be included as a dictionary in the vector property in the response.
   * @default false
   */
  include_vector?: boolean | string | string[] | null;
  /**
   * Limit
   * Maximum number of objects to return.
   */
  limit?: number | null;
  /**
   * Max Vector Distance
   * Maximum threshold for the vector search component.
   */
  max_vector_distance?: number | null;
  /**
   * Minimum Match Or Operator
   * Minimum number of keywords that define a match. Objects returned will have to have at least this many matches. Applies to keyword search only.
   */
  minimum_match_or_operator?: number | null;
  /**
   * Offset
   * Skips first N results in similarity response. Useful for pagination.
   */
  offset?: number | null;
  /**
   * Query Properties
   * Apply keyword search to only a specified subset of object properties.
   */
  query_properties?: string[] | null;
  /**
   * Rag Provider
   * @default "weaviate"
   */
  rag_provider?: "weaviate";
  /**
   * Return Metadata
   * Specify metadata fields to return.
   */
  return_metadata?: WeaviateHybridSearchSettingsConfigurationRequestReturnMetadataEnum[] | MetadataQuery | null;
  /**
   * Return Properties
   * Specify which properties to return for each object.
   */
  return_properties?: string[] | null;
  /**
   * Search Kind
   * @default "hybrid_search"
   */
  search_kind?: "hybrid_search";
  /**
   * Target Vector
   * Specifies vector to use for vector search when using named vectors.
   */
  target_vector?: string | string[] | MultiTargetVectorJoin | null;
}

export type WeaviateHybridSearchSettingsConfigurationRequestReturnMetadataEnum =
  | "creation_time"
  | "last_update_time"
  | "distance"
  | "certainty"
  | "score"
  | "explain_score"
  | "is_consistent";

/** WeaviateHybridSearchSettingsConfigurationResponse */
export interface WeaviateHybridSearchSettingsConfigurationResponse {
  /**
   * Alpha
   * Balance between the relative weights of the keyword and vector search. 1 is pure vector search, 0 is pure keyword search.
   * @default 0.7
   */
  alpha?: number;
  /**
   * And Operator
   * Search returns objects that contain all tokens in the search string. Cannot be used with minimum_match_or_operator. Applies to keyword search only.
   */
  and_operator?: boolean | null;
  /**
   * Auto Limit
   * Automatically limit search results to groups of objects with similar distances, stopping after auto_limit number of significant jumps.
   */
  auto_limit?: number | null;
  /**
   * Collection Name
   * Name of the vector collection used for the search.
   */
  collection_name: string;
  /** Set the fusion algorithm to use. Default is Relative Score Fusion. */
  fusion_type?: HybridFusion | null;
  /**
   * Include Vector
   * Boolean value whether to include vector embeddings in the response or can be used to specify the names of the vectors to include in the response if your collection uses named vectors. Will be included as a dictionary in the vector property in the response.
   * @default false
   */
  include_vector?: boolean | string | string[] | null;
  /**
   * Limit
   * Maximum number of objects to return.
   */
  limit?: number | null;
  /**
   * Max Vector Distance
   * Maximum threshold for the vector search component.
   */
  max_vector_distance?: number | null;
  /**
   * Minimum Match Or Operator
   * Minimum number of keywords that define a match. Objects returned will have to have at least this many matches. Applies to keyword search only.
   */
  minimum_match_or_operator?: number | null;
  /**
   * Offset
   * Skips first N results in similarity response. Useful for pagination.
   */
  offset?: number | null;
  /**
   * Query Properties
   * Apply keyword search to only a specified subset of object properties.
   */
  query_properties?: string[] | null;
  /**
   * Rag Provider
   * @default "weaviate"
   */
  rag_provider?: "weaviate";
  /**
   * Return Metadata
   * Specify metadata fields to return.
   */
  return_metadata?: WeaviateHybridSearchSettingsConfigurationResponseReturnMetadataEnum[] | MetadataQuery | null;
  /**
   * Return Properties
   * Specify which properties to return for each object.
   */
  return_properties?: string[] | null;
  /**
   * Search Kind
   * @default "hybrid_search"
   */
  search_kind?: "hybrid_search";
  /**
   * Target Vector
   * Specifies vector to use for vector search when using named vectors.
   */
  target_vector?: string | string[] | MultiTargetVectorJoin | null;
}

export type WeaviateHybridSearchSettingsConfigurationResponseReturnMetadataEnum =
  | "creation_time"
  | "last_update_time"
  | "distance"
  | "certainty"
  | "score"
  | "explain_score"
  | "is_consistent";

/** WeaviateHybridSearchSettingsRequest */
export interface WeaviateHybridSearchSettingsRequest {
  /**
   * Alpha
   * Balance between the relative weights of the keyword and vector search. 1 is pure vector search, 0 is pure keyword search.
   * @default 0.7
   */
  alpha?: number;
  /**
   * And Operator
   * Search returns objects that contain all tokens in the search string. Cannot be used with minimum_match_or_operator. Applies to keyword search only.
   */
  and_operator?: boolean | null;
  /**
   * Auto Limit
   * Automatically limit search results to groups of objects with similar distances, stopping after auto_limit number of significant jumps.
   */
  auto_limit?: number | null;
  /**
   * Collection Name
   * Name of the vector collection used for the search.
   */
  collection_name: string;
  /** Set the fusion algorithm to use. Default is Relative Score Fusion. */
  fusion_type?: HybridFusion | null;
  /**
   * Include Vector
   * Boolean value whether to include vector embeddings in the response or can be used to specify the names of the vectors to include in the response if your collection uses named vectors. Will be included as a dictionary in the vector property in the response.
   * @default false
   */
  include_vector?: boolean | string | string[] | null;
  /**
   * Limit
   * Maximum number of objects to return.
   */
  limit?: number | null;
  /**
   * Max Vector Distance
   * Maximum threshold for the vector search component.
   */
  max_vector_distance?: number | null;
  /**
   * Minimum Match Or Operator
   * Minimum number of keywords that define a match. Objects returned will have to have at least this many matches. Applies to keyword search only.
   */
  minimum_match_or_operator?: number | null;
  /**
   * Offset
   * Skips first N results in similarity response. Useful for pagination.
   */
  offset?: number | null;
  /**
   * Query
   * Input text to find objects with near vectors or keyword matches.
   */
  query: string;
  /**
   * Query Properties
   * Apply keyword search to only a specified subset of object properties.
   */
  query_properties?: string[] | null;
  /**
   * Rag Provider
   * @default "weaviate"
   */
  rag_provider?: "weaviate";
  /**
   * Return Metadata
   * Specify metadata fields to return.
   */
  return_metadata?: WeaviateHybridSearchSettingsRequestReturnMetadataEnum[] | MetadataQuery | null;
  /**
   * Return Properties
   * Specify which properties to return for each object.
   */
  return_properties?: string[] | null;
  /**
   * Target Vector
   * Specifies vector to use for vector search when using named vectors.
   */
  target_vector?: string | string[] | MultiTargetVectorJoin | null;
}

export type WeaviateHybridSearchSettingsRequestReturnMetadataEnum =
  | "creation_time"
  | "last_update_time"
  | "distance"
  | "certainty"
  | "score"
  | "explain_score"
  | "is_consistent";

/** WeaviateKeywordSearchSettingsConfigurationRequest */
export interface WeaviateKeywordSearchSettingsConfigurationRequest {
  /**
   * And Operator
   * Search returns objects that contain all tokens in the search string. Cannot be used with minimum_match_or_operator
   */
  and_operator?: boolean | null;
  /**
   * Auto Limit
   * Automatically limit search results to groups of objects with similar distances, stopping after auto_limit number of significant jumps.
   */
  auto_limit?: number | null;
  /**
   * Collection Name
   * Name of the vector collection used for the search.
   */
  collection_name: string;
  /**
   * Include Vector
   * Boolean value whether to include vector embeddings in the response or can be used to specify the names of the vectors to include in the response if your collection uses named vectors. Will be included as a dictionary in the vector property in the response.
   * @default false
   */
  include_vector?: boolean | string | string[] | null;
  /**
   * Limit
   * Maximum number of objects to return.
   */
  limit?: number | null;
  /**
   * Minimum Match Or Operator
   * Minimum number of keywords that define a match. Objects returned will have to have at least this many matches.
   */
  minimum_match_or_operator?: number | null;
  /**
   * Offset
   * Skips first N results in similarity response. Useful for pagination.
   */
  offset?: number | null;
  /**
   * Rag Provider
   * @default "weaviate"
   */
  rag_provider?: "weaviate";
  /**
   * Return Metadata
   * Specify metadata fields to return.
   */
  return_metadata?: WeaviateKeywordSearchSettingsConfigurationRequestReturnMetadataEnum[] | MetadataQuery | null;
  /**
   * Return Properties
   * Specify which properties to return for each object.
   */
  return_properties?: string[] | null;
  /**
   * Search Kind
   * @default "keyword_search"
   */
  search_kind?: "keyword_search";
}

export type WeaviateKeywordSearchSettingsConfigurationRequestReturnMetadataEnum =
  | "creation_time"
  | "last_update_time"
  | "distance"
  | "certainty"
  | "score"
  | "explain_score"
  | "is_consistent";

/** WeaviateKeywordSearchSettingsConfigurationResponse */
export interface WeaviateKeywordSearchSettingsConfigurationResponse {
  /**
   * And Operator
   * Search returns objects that contain all tokens in the search string. Cannot be used with minimum_match_or_operator
   */
  and_operator?: boolean | null;
  /**
   * Auto Limit
   * Automatically limit search results to groups of objects with similar distances, stopping after auto_limit number of significant jumps.
   */
  auto_limit?: number | null;
  /**
   * Collection Name
   * Name of the vector collection used for the search.
   */
  collection_name: string;
  /**
   * Include Vector
   * Boolean value whether to include vector embeddings in the response or can be used to specify the names of the vectors to include in the response if your collection uses named vectors. Will be included as a dictionary in the vector property in the response.
   * @default false
   */
  include_vector?: boolean | string | string[] | null;
  /**
   * Limit
   * Maximum number of objects to return.
   */
  limit?: number | null;
  /**
   * Minimum Match Or Operator
   * Minimum number of keywords that define a match. Objects returned will have to have at least this many matches.
   */
  minimum_match_or_operator?: number | null;
  /**
   * Offset
   * Skips first N results in similarity response. Useful for pagination.
   */
  offset?: number | null;
  /**
   * Rag Provider
   * @default "weaviate"
   */
  rag_provider?: "weaviate";
  /**
   * Return Metadata
   * Specify metadata fields to return.
   */
  return_metadata?: WeaviateKeywordSearchSettingsConfigurationResponseReturnMetadataEnum[] | MetadataQuery | null;
  /**
   * Return Properties
   * Specify which properties to return for each object.
   */
  return_properties?: string[] | null;
  /**
   * Search Kind
   * @default "keyword_search"
   */
  search_kind?: "keyword_search";
}

export type WeaviateKeywordSearchSettingsConfigurationResponseReturnMetadataEnum =
  | "creation_time"
  | "last_update_time"
  | "distance"
  | "certainty"
  | "score"
  | "explain_score"
  | "is_consistent";

/** WeaviateKeywordSearchSettingsRequest */
export interface WeaviateKeywordSearchSettingsRequest {
  /**
   * And Operator
   * Search returns objects that contain all tokens in the search string. Cannot be used with minimum_match_or_operator
   */
  and_operator?: boolean | null;
  /**
   * Auto Limit
   * Automatically limit search results to groups of objects with similar distances, stopping after auto_limit number of significant jumps.
   */
  auto_limit?: number | null;
  /**
   * Collection Name
   * Name of the vector collection used for the search.
   */
  collection_name: string;
  /**
   * Include Vector
   * Boolean value whether to include vector embeddings in the response or can be used to specify the names of the vectors to include in the response if your collection uses named vectors. Will be included as a dictionary in the vector property in the response.
   * @default false
   */
  include_vector?: boolean | string | string[] | null;
  /**
   * Limit
   * Maximum number of objects to return.
   */
  limit?: number | null;
  /**
   * Minimum Match Or Operator
   * Minimum number of keywords that define a match. Objects returned will have to have at least this many matches.
   */
  minimum_match_or_operator?: number | null;
  /**
   * Offset
   * Skips first N results in similarity response. Useful for pagination.
   */
  offset?: number | null;
  /**
   * Query
   * Input text to find objects with keyword matches.
   */
  query: string;
  /**
   * Rag Provider
   * @default "weaviate"
   */
  rag_provider?: "weaviate";
  /**
   * Return Metadata
   * Specify metadata fields to return.
   */
  return_metadata?: WeaviateKeywordSearchSettingsRequestReturnMetadataEnum[] | MetadataQuery | null;
  /**
   * Return Properties
   * Specify which properties to return for each object.
   */
  return_properties?: string[] | null;
}

export type WeaviateKeywordSearchSettingsRequestReturnMetadataEnum =
  | "creation_time"
  | "last_update_time"
  | "distance"
  | "certainty"
  | "score"
  | "explain_score"
  | "is_consistent";

/**
 * WeaviateQueryResult
 * Individual search result from Weaviate
 */
export interface WeaviateQueryResult {
  /** Search metadata including distance, score, etc. */
  metadata?: WeaviateQueryResultMetadata | null;
  /**
   * Properties
   * Properties of the result object
   */
  properties: Record<string, any>;
  /**
   * Uuid
   * Unique identifier of the result
   * @format uuid
   */
  uuid: string;
  /**
   * Vector
   * Vector representation
   */
  vector?: Record<string, number[] | number[][]> | null;
}

/**
 * WeaviateQueryResultMetadata
 * Metadata from weaviate for a vector object:
 * https://weaviate-python-client.readthedocs.io/en/latest/weaviate.collections.classes.html#module-weaviate.collections.classes.internal
 */
export interface WeaviateQueryResultMetadata {
  /**
   * Certainty
   * Similarity score measure between 0 and 1. Higher values correspond to more similar reesults.
   */
  certainty?: number | null;
  /**
   * Creation Time
   * Vector object creation time.
   */
  creation_time?: string | null;
  /**
   * Distance
   * Raw distance metric used in the vector search. Lower values indicate closer vectors.
   */
  distance?: number | null;
  /**
   * Explain Score
   * Explanation of how the score was calculated.
   */
  explain_score?: string | null;
  /**
   * Is Consistent
   * Indicates if the object is consistent across all replicates in a multi-node Weaviate cluster.
   */
  is_consistent?: boolean | null;
  /**
   * Last Update Time
   * Vector object last update time.
   */
  last_update_time?: string | null;
  /**
   * Score
   * Normalized relevance metric that ranks search results.
   */
  score?: number | null;
}

/**
 * WeaviateQueryResults
 * Response from Weaviate similarity text search
 */
export interface WeaviateQueryResults {
  /**
   * Objects
   * List of search result objects
   */
  objects: WeaviateQueryResult[];
  /**
   * Rag Provider
   * @default "weaviate"
   */
  rag_provider?: "weaviate";
}

/** WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest */
export interface WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest {
  /**
   * Auto Limit
   * Automatically limit search results to groups of objects with similar distances, stopping after auto_limit number of significant jumps.
   */
  auto_limit?: number | null;
  /**
   * Certainty
   * Minimum similarity score to return. Higher values correspond to more similar results. Only one of distance and certainty can be specified.
   */
  certainty?: number | null;
  /**
   * Collection Name
   * Name of the vector collection used for the search.
   */
  collection_name: string;
  /**
   * Distance
   * Maximum allowed distance between the query and result vectors. Lower values corresponds to more similar results. Only one of distance and certainty can be specified.
   */
  distance?: number | null;
  /**
   * Include Vector
   * Boolean value whether to include vector embeddings in the response or can be used to specify the names of the vectors to include in the response if your collection uses named vectors. Will be included as a dictionary in the vector property in the response.
   * @default false
   */
  include_vector?: boolean | string | string[] | null;
  /**
   * Limit
   * Maximum number of objects to return.
   */
  limit?: number | null;
  /**
   * Offset
   * Skips first N results in similarity response. Useful for pagination.
   */
  offset?: number | null;
  /**
   * Rag Provider
   * @default "weaviate"
   */
  rag_provider?: "weaviate";
  /**
   * Return Metadata
   * Specify metadata fields to return.
   */
  return_metadata?: WeaviateVectorSimilarityTextSearchSettingsConfigurationRequestReturnMetadataEnum[] | MetadataQuery | null;
  /**
   * Return Properties
   * Specify which properties to return for each object.
   */
  return_properties?: string[] | null;
  /**
   * Search Kind
   * @default "vector_similarity_text_search"
   */
  search_kind?: "vector_similarity_text_search";
  /**
   * Target Vector
   * Specifies vector to use for similarity search when using named vectors.
   */
  target_vector?: string | string[] | MultiTargetVectorJoin | null;
}

export type WeaviateVectorSimilarityTextSearchSettingsConfigurationRequestReturnMetadataEnum =
  | "creation_time"
  | "last_update_time"
  | "distance"
  | "certainty"
  | "score"
  | "explain_score"
  | "is_consistent";

/** WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse */
export interface WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse {
  /**
   * Auto Limit
   * Automatically limit search results to groups of objects with similar distances, stopping after auto_limit number of significant jumps.
   */
  auto_limit?: number | null;
  /**
   * Certainty
   * Minimum similarity score to return. Higher values correspond to more similar results. Only one of distance and certainty can be specified.
   */
  certainty?: number | null;
  /**
   * Collection Name
   * Name of the vector collection used for the search.
   */
  collection_name: string;
  /**
   * Distance
   * Maximum allowed distance between the query and result vectors. Lower values corresponds to more similar results. Only one of distance and certainty can be specified.
   */
  distance?: number | null;
  /**
   * Include Vector
   * Boolean value whether to include vector embeddings in the response or can be used to specify the names of the vectors to include in the response if your collection uses named vectors. Will be included as a dictionary in the vector property in the response.
   * @default false
   */
  include_vector?: boolean | string | string[] | null;
  /**
   * Limit
   * Maximum number of objects to return.
   */
  limit?: number | null;
  /**
   * Offset
   * Skips first N results in similarity response. Useful for pagination.
   */
  offset?: number | null;
  /**
   * Rag Provider
   * @default "weaviate"
   */
  rag_provider?: "weaviate";
  /**
   * Return Metadata
   * Specify metadata fields to return.
   */
  return_metadata?: WeaviateVectorSimilarityTextSearchSettingsConfigurationResponseReturnMetadataEnum[] | MetadataQuery | null;
  /**
   * Return Properties
   * Specify which properties to return for each object.
   */
  return_properties?: string[] | null;
  /**
   * Search Kind
   * @default "vector_similarity_text_search"
   */
  search_kind?: "vector_similarity_text_search";
  /**
   * Target Vector
   * Specifies vector to use for similarity search when using named vectors.
   */
  target_vector?: string | string[] | MultiTargetVectorJoin | null;
}

export type WeaviateVectorSimilarityTextSearchSettingsConfigurationResponseReturnMetadataEnum =
  | "creation_time"
  | "last_update_time"
  | "distance"
  | "certainty"
  | "score"
  | "explain_score"
  | "is_consistent";

/** WeaviateVectorSimilarityTextSearchSettingsRequest */
export interface WeaviateVectorSimilarityTextSearchSettingsRequest {
  /**
   * Auto Limit
   * Automatically limit search results to groups of objects with similar distances, stopping after auto_limit number of significant jumps.
   */
  auto_limit?: number | null;
  /**
   * Certainty
   * Minimum similarity score to return. Higher values correspond to more similar results. Only one of distance and certainty can be specified.
   */
  certainty?: number | null;
  /**
   * Collection Name
   * Name of the vector collection used for the search.
   */
  collection_name: string;
  /**
   * Distance
   * Maximum allowed distance between the query and result vectors. Lower values corresponds to more similar results. Only one of distance and certainty can be specified.
   */
  distance?: number | null;
  /**
   * Include Vector
   * Boolean value whether to include vector embeddings in the response or can be used to specify the names of the vectors to include in the response if your collection uses named vectors. Will be included as a dictionary in the vector property in the response.
   * @default false
   */
  include_vector?: boolean | string | string[] | null;
  /**
   * Limit
   * Maximum number of objects to return.
   */
  limit?: number | null;
  /**
   * Offset
   * Skips first N results in similarity response. Useful for pagination.
   */
  offset?: number | null;
  /**
   * Query
   * Input text to find objects with near vectors for.
   */
  query: string[] | string;
  /**
   * Rag Provider
   * @default "weaviate"
   */
  rag_provider?: "weaviate";
  /**
   * Return Metadata
   * Specify metadata fields to return.
   */
  return_metadata?: WeaviateVectorSimilarityTextSearchSettingsRequestReturnMetadataEnum[] | MetadataQuery | null;
  /**
   * Return Properties
   * Specify which properties to return for each object.
   */
  return_properties?: string[] | null;
  /**
   * Target Vector
   * Specifies vector to use for similarity search when using named vectors.
   */
  target_vector?: string | string[] | MultiTargetVectorJoin | null;
}

export type WeaviateVectorSimilarityTextSearchSettingsRequestReturnMetadataEnum =
  | "creation_time"
  | "last_update_time"
  | "distance"
  | "certainty"
  | "score"
  | "explain_score"
  | "is_consistent";

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
  securityWorker?: (securityData: SecurityDataType | null) => Promise<AxiosRequestConfig | void> | AxiosRequestConfig | void;
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
      ((typeof secure === "boolean" ? secure : this.secure) && this.securityWorker && (await this.securityWorker(this.securityData))) || {};
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
 * @version 2.1.213
 */
export class Api<SecurityDataType extends unknown> extends HttpClient<SecurityDataType> {
  api = {
    /**
     * @description Add a tag to an agentic prompt version
     *
     * @tags Prompts
     * @name AddTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPut
     * @summary Add a tag to an agentic prompt version
     * @request PUT:/api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/tags
     * @secure
     */
    addTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPut: (
      promptName: string,
      promptVersion: string,
      taskId: string,
      data: BodyAddTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPut,
      params: RequestParams = {}
    ) =>
      this.request<
        AddTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPutData,
        AddTagToAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsPutError
      >({
        path: `/api/v1/tasks/${taskId}/prompts/${promptName}/versions/${promptVersion}/tags`,
        method: "PUT",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Add a tag to an llm eval version
     *
     * @tags LLMEvals
     * @name AddTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPut
     * @summary Add a tag to an llm eval version
     * @request PUT:/api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}/tags
     * @secure
     */
    addTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPut: (
      evalName: string,
      evalVersion: string,
      taskId: string,
      data: BodyAddTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPut,
      params: RequestParams = {}
    ) =>
      this.request<
        AddTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPutData,
        AddTagToLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsPutError
      >({
        path: `/api/v1/tasks/${taskId}/llm_evals/${evalName}/versions/${evalVersion}/tags`,
        method: "PUT",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Annotate a trace with a score and description (1 = liked, 0 = disliked)
     *
     * @tags Traces
     * @name AnnotateTraceApiV1TracesTraceIdAnnotationsPost
     * @summary Annotate a Trace
     * @request POST:/api/v1/traces/{trace_id}/annotations
     * @secure
     */
    annotateTraceApiV1TracesTraceIdAnnotationsPost: (traceId: string, data: AgenticAnnotationRequest, params: RequestParams = {}) =>
      this.request<AnnotateTraceApiV1TracesTraceIdAnnotationsPostData, AnnotateTraceApiV1TracesTraceIdAnnotationsPostError>({
        path: `/api/v1/traces/${traceId}/annotations`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

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
      this.request<ArchiveDefaultRuleApiV2DefaultRulesRuleIdDeleteData, ArchiveDefaultRuleApiV2DefaultRulesRuleIdDeleteError>({
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
    archiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDelete: (taskId: string, metricId: string, params: RequestParams = {}) =>
      this.request<ArchiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDeleteData, ArchiveTaskMetricApiV2TasksTaskIdMetricsMetricIdDeleteError>({
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
      this.request<ArchiveTaskRuleApiV2TasksTaskIdRulesRuleIdDeleteData, ArchiveTaskRuleApiV2TasksTaskIdRulesRuleIdDeleteError>({
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
     * @name ComputeSessionMetricsApiV1TracesSessionsSessionIdMetricsGet
     * @summary Compute Missing Session Metrics
     * @request GET:/api/v1/traces/sessions/{session_id}/metrics
     * @secure
     */
    computeSessionMetricsApiV1TracesSessionsSessionIdMetricsGet: (
      { sessionId, ...query }: ComputeSessionMetricsApiV1TracesSessionsSessionIdMetricsGetParams,
      params: RequestParams = {}
    ) =>
      this.request<ComputeSessionMetricsApiV1TracesSessionsSessionIdMetricsGetData, ComputeSessionMetricsApiV1TracesSessionsSessionIdMetricsGetError>(
        {
          path: `/api/v1/traces/sessions/${sessionId}/metrics`,
          method: "GET",
          query: query,
          secure: true,
          format: "json",
          ...params,
        }
      ),

    /**
     * @description Compute all missing metrics for a single span on-demand. Returns span with computed metrics.
     *
     * @tags Spans
     * @name ComputeSpanMetricsApiV1TracesSpansSpanIdMetricsGet
     * @summary Compute Missing Span Metrics
     * @request GET:/api/v1/traces/spans/{span_id}/metrics
     * @secure
     */
    computeSpanMetricsApiV1TracesSpansSpanIdMetricsGet: (spanId: string, params: RequestParams = {}) =>
      this.request<ComputeSpanMetricsApiV1TracesSpansSpanIdMetricsGetData, ComputeSpanMetricsApiV1TracesSpansSpanIdMetricsGetError>({
        path: `/api/v1/traces/spans/${spanId}/metrics`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

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
      this.request<ComputeTraceMetricsApiV1TracesTraceIdMetricsGetData, ComputeTraceMetricsApiV1TracesTraceIdMetricsGetError>({
        path: `/api/v1/traces/${traceId}/metrics`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Register a new dataset.
     *
     * @tags Datasets
     * @name CreateDatasetApiV2DatasetsPost
     * @summary Create Dataset
     * @request POST:/api/v2/datasets
     * @secure
     */
    createDatasetApiV2DatasetsPost: (data: NewDatasetRequest, params: RequestParams = {}) =>
      this.request<CreateDatasetApiV2DatasetsPostData, CreateDatasetApiV2DatasetsPostError>({
        path: `/api/v2/datasets`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Create a new dataset version.
     *
     * @tags Datasets
     * @name CreateDatasetVersionApiV2DatasetsDatasetIdVersionsPost
     * @summary Create Dataset Version
     * @request POST:/api/v2/datasets/{dataset_id}/versions
     * @secure
     */
    createDatasetVersionApiV2DatasetsDatasetIdVersionsPost: (datasetId: string, data: NewDatasetVersionRequest, params: RequestParams = {}) =>
      this.request<CreateDatasetVersionApiV2DatasetsDatasetIdVersionsPostData, CreateDatasetVersionApiV2DatasetsDatasetIdVersionsPostError>({
        path: `/api/v2/datasets/${datasetId}/versions`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
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
     * @description Create a new notebook for organizing experiments within a task
     *
     * @tags Notebooks
     * @name CreateNotebookApiV1TasksTaskIdNotebooksPost
     * @summary Create a notebook
     * @request POST:/api/v1/tasks/{task_id}/notebooks
     * @secure
     */
    createNotebookApiV1TasksTaskIdNotebooksPost: (taskId: string, data: CreateNotebookRequest, params: RequestParams = {}) =>
      this.request<CreateNotebookApiV1TasksTaskIdNotebooksPostData, CreateNotebookApiV1TasksTaskIdNotebooksPostError>({
        path: `/api/v1/tasks/${taskId}/notebooks`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Create a new prompt experiment and initiate execution
     *
     * @tags Prompt Experiments
     * @name CreatePromptExperimentApiV1TasksTaskIdPromptExperimentsPost
     * @summary Create and run a prompt experiment
     * @request POST:/api/v1/tasks/{task_id}/prompt_experiments
     * @secure
     */
    createPromptExperimentApiV1TasksTaskIdPromptExperimentsPost: (taskId: string, data: CreatePromptExperimentRequest, params: RequestParams = {}) =>
      this.request<CreatePromptExperimentApiV1TasksTaskIdPromptExperimentsPostData, CreatePromptExperimentApiV1TasksTaskIdPromptExperimentsPostError>(
        {
          path: `/api/v1/tasks/${taskId}/prompt_experiments`,
          method: "POST",
          body: data,
          secure: true,
          type: ContentType.Json,
          format: "json",
          ...params,
        }
      ),

    /**
     * @description Register a new RAG provider connection configuration.
     *
     * @tags RAG Providers
     * @name CreateRagProviderApiV1TasksTaskIdRagProvidersPost
     * @summary Create Rag Provider
     * @request POST:/api/v1/tasks/{task_id}/rag_providers
     * @secure
     */
    createRagProviderApiV1TasksTaskIdRagProvidersPost: (taskId: string, data: RagProviderConfigurationRequest, params: RequestParams = {}) =>
      this.request<CreateRagProviderApiV1TasksTaskIdRagProvidersPostData, CreateRagProviderApiV1TasksTaskIdRagProvidersPostError>({
        path: `/api/v1/tasks/${taskId}/rag_providers`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Create a new RAG search settings configuration.
     *
     * @tags RAG Settings
     * @name CreateRagSearchSettings
     * @summary Create Rag Search Settings
     * @request POST:/api/v1/tasks/{task_id}/rag_search_settings
     * @secure
     */
    createRagSearchSettings: (taskId: string, data: RagSearchSettingConfigurationRequest, params: RequestParams = {}) =>
      this.request<CreateRagSearchSettingsData, CreateRagSearchSettingsError>({
        path: `/api/v1/tasks/${taskId}/rag_search_settings`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Create a new version for an existing RAG search settings configuration.
     *
     * @tags RAG Settings
     * @name CreateRagSearchSettingsVersion
     * @summary Create Rag Search Settings Version
     * @request POST:/api/v1/rag_search_settings/{setting_configuration_id}/versions
     * @secure
     */
    createRagSearchSettingsVersion: (
      settingConfigurationId: string,
      data: RagSearchSettingConfigurationNewVersionRequest,
      params: RequestParams = {}
    ) =>
      this.request<CreateRagSearchSettingsVersionData, CreateRagSearchSettingsVersionError>({
        path: `/api/v1/rag_search_settings/${settingConfigurationId}/versions`,
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
     * @description Create a new transform for a dataset.
     *
     * @tags Datasets
     * @name CreateTransformApiV2DatasetsDatasetIdTransformsPost
     * @summary Create Transform
     * @request POST:/api/v2/datasets/{dataset_id}/transforms
     * @secure
     */
    createTransformApiV2DatasetsDatasetIdTransformsPost: (datasetId: string, data: NewDatasetTransformRequest, params: RequestParams = {}) =>
      this.request<CreateTransformApiV2DatasetsDatasetIdTransformsPostData, CreateTransformApiV2DatasetsDatasetIdTransformsPostError>({
        path: `/api/v2/datasets/${datasetId}/transforms`,
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
      this.request<DefaultValidatePromptApiV2ValidatePromptPostData, DefaultValidatePromptApiV2ValidatePromptPostError>({
        path: `/api/v2/validate_prompt`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

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
    defaultValidateResponseApiV2ValidateResponseInferenceIdPost: (inferenceId: string, data: ResponseValidationRequest, params: RequestParams = {}) =>
      this.request<DefaultValidateResponseApiV2ValidateResponseInferenceIdPostData, DefaultValidateResponseApiV2ValidateResponseInferenceIdPostError>(
        {
          path: `/api/v2/validate_response/${inferenceId}`,
          method: "POST",
          body: data,
          secure: true,
          type: ContentType.Json,
          format: "json",
          ...params,
        }
      ),

    /**
     * @description Deletes an entire agentic prompt
     *
     * @tags Prompts
     * @name DeleteAgenticPromptApiV1TasksTaskIdPromptsPromptNameDelete
     * @summary Delete an agentic prompt
     * @request DELETE:/api/v1/tasks/{task_id}/prompts/{prompt_name}
     * @secure
     */
    deleteAgenticPromptApiV1TasksTaskIdPromptsPromptNameDelete: (promptName: string, taskId: string, params: RequestParams = {}) =>
      this.request<DeleteAgenticPromptApiV1TasksTaskIdPromptsPromptNameDeleteData, DeleteAgenticPromptApiV1TasksTaskIdPromptsPromptNameDeleteError>({
        path: `/api/v1/tasks/${taskId}/prompts/${promptName}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Deletes a specific version of an agentic prompt
     *
     * @tags Prompts
     * @name DeleteAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionDelete
     * @summary Delete an agentic prompt version
     * @request DELETE:/api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}
     * @secure
     */
    deleteAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionDelete: (
      promptName: string,
      promptVersion: string,
      taskId: string,
      params: RequestParams = {}
    ) =>
      this.request<
        DeleteAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionDeleteData,
        DeleteAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionDeleteError
      >({
        path: `/api/v1/tasks/${taskId}/prompts/${promptName}/versions/${promptVersion}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Delete an annotation from a trace
     *
     * @tags Traces
     * @name DeleteAnnotationFromTraceApiV1TracesTraceIdAnnotationsDelete
     * @summary Delete an annotation from a trace
     * @request DELETE:/api/v1/traces/{trace_id}/annotations
     * @secure
     */
    deleteAnnotationFromTraceApiV1TracesTraceIdAnnotationsDelete: (traceId: string, params: RequestParams = {}) =>
      this.request<
        DeleteAnnotationFromTraceApiV1TracesTraceIdAnnotationsDeleteData,
        DeleteAnnotationFromTraceApiV1TracesTraceIdAnnotationsDeleteError
      >({
        path: `/api/v1/traces/${traceId}/annotations`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Delete a dataset.
     *
     * @tags Datasets
     * @name DeleteDatasetApiV2DatasetsDatasetIdDelete
     * @summary Delete Dataset
     * @request DELETE:/api/v2/datasets/{dataset_id}
     * @secure
     */
    deleteDatasetApiV2DatasetsDatasetIdDelete: (datasetId: string, params: RequestParams = {}) =>
      this.request<DeleteDatasetApiV2DatasetsDatasetIdDeleteData, DeleteDatasetApiV2DatasetsDatasetIdDeleteError>({
        path: `/api/v2/datasets/${datasetId}`,
        method: "DELETE",
        secure: true,
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
     * @description Deletes an entire llm eval
     *
     * @tags LLMEvals
     * @name DeleteLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameDelete
     * @summary Delete an llm eval
     * @request DELETE:/api/v1/tasks/{task_id}/llm_evals/{eval_name}
     * @secure
     */
    deleteLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameDelete: (evalName: string, taskId: string, params: RequestParams = {}) =>
      this.request<DeleteLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameDeleteData, DeleteLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameDeleteError>({
        path: `/api/v1/tasks/${taskId}/llm_evals/${evalName}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Disables the configuration for a model provider
     *
     * @tags Model Providers
     * @name DeleteModelProviderApiV1ModelProvidersProviderDelete
     * @summary Disables the configuration for a model provider.
     * @request DELETE:/api/v1/model_providers/{provider}
     * @secure
     */
    deleteModelProviderApiV1ModelProvidersProviderDelete: (provider: ModelProvider, params: RequestParams = {}) =>
      this.request<DeleteModelProviderApiV1ModelProvidersProviderDeleteData, DeleteModelProviderApiV1ModelProvidersProviderDeleteError>({
        path: `/api/v1/model_providers/${provider}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Delete a notebook (experiments are kept)
     *
     * @tags Notebooks
     * @name DeleteNotebookApiV1NotebooksNotebookIdDelete
     * @summary Delete notebook
     * @request DELETE:/api/v1/notebooks/{notebook_id}
     * @secure
     */
    deleteNotebookApiV1NotebooksNotebookIdDelete: (notebookId: string, params: RequestParams = {}) =>
      this.request<DeleteNotebookApiV1NotebooksNotebookIdDeleteData, DeleteNotebookApiV1NotebooksNotebookIdDeleteError>({
        path: `/api/v1/notebooks/${notebookId}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Delete a prompt experiment and all its associated data
     *
     * @tags Prompt Experiments
     * @name DeletePromptExperimentApiV1PromptExperimentsExperimentIdDelete
     * @summary Delete prompt experiment
     * @request DELETE:/api/v1/prompt_experiments/{experiment_id}
     * @secure
     */
    deletePromptExperimentApiV1PromptExperimentsExperimentIdDelete: (experimentId: string, params: RequestParams = {}) =>
      this.request<
        DeletePromptExperimentApiV1PromptExperimentsExperimentIdDeleteData,
        DeletePromptExperimentApiV1PromptExperimentsExperimentIdDeleteError
      >({
        path: `/api/v1/prompt_experiments/${experimentId}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Delete a RAG provider connection configuration.
     *
     * @tags RAG Providers
     * @name DeleteRagProviderApiV1RagProvidersProviderIdDelete
     * @summary Delete Rag Provider
     * @request DELETE:/api/v1/rag_providers/{provider_id}
     * @secure
     */
    deleteRagProviderApiV1RagProvidersProviderIdDelete: (providerId: string, params: RequestParams = {}) =>
      this.request<DeleteRagProviderApiV1RagProvidersProviderIdDeleteData, DeleteRagProviderApiV1RagProvidersProviderIdDeleteError>({
        path: `/api/v1/rag_providers/${providerId}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Delete a RAG search setting configuration.
     *
     * @tags RAG Settings
     * @name DeleteRagSearchSetting
     * @summary Delete Rag Search Setting
     * @request DELETE:/api/v1/rag_search_settings/{setting_configuration_id}
     * @secure
     */
    deleteRagSearchSetting: (settingConfigurationId: string, params: RequestParams = {}) =>
      this.request<DeleteRagSearchSettingData, DeleteRagSearchSettingError>({
        path: `/api/v1/rag_search_settings/${settingConfigurationId}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Soft delete a RAG search setting configuration version.
     *
     * @tags RAG Settings
     * @name DeleteRagSearchSettingVersion
     * @summary Delete Rag Search Setting Version
     * @request DELETE:/api/v1/rag_search_settings/{setting_configuration_id}/versions/{version_number}
     * @secure
     */
    deleteRagSearchSettingVersion: (settingConfigurationId: string, versionNumber: number, params: RequestParams = {}) =>
      this.request<DeleteRagSearchSettingVersionData, DeleteRagSearchSettingVersionError>({
        path: `/api/v1/rag_search_settings/${settingConfigurationId}/versions/${versionNumber}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Remove a tag from an agentic prompt version
     *
     * @tags Prompts
     * @name DeleteTagFromAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsTagDelete
     * @summary Remove a tag from an agentic prompt version
     * @request DELETE:/api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/tags/{tag}
     * @secure
     */
    deleteTagFromAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsTagDelete: (
      promptName: string,
      promptVersion: string,
      tag: string,
      taskId: string,
      params: RequestParams = {}
    ) =>
      this.request<
        DeleteTagFromAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsTagDeleteData,
        DeleteTagFromAgenticPromptVersionApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionTagsTagDeleteError
      >({
        path: `/api/v1/tasks/${taskId}/prompts/${promptName}/versions/${promptVersion}/tags/${tag}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Remove a tag from an llm eval version
     *
     * @tags LLMEvals
     * @name DeleteTagFromLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsTagDelete
     * @summary Remove a tag from an llm eval version
     * @request DELETE:/api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}/tags/{tag}
     * @secure
     */
    deleteTagFromLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsTagDelete: (
      evalName: string,
      evalVersion: string,
      tag: string,
      taskId: string,
      params: RequestParams = {}
    ) =>
      this.request<
        DeleteTagFromLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsTagDeleteData,
        DeleteTagFromLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionTagsTagDeleteError
      >({
        path: `/api/v1/tasks/${taskId}/llm_evals/${evalName}/versions/${evalVersion}/tags/${tag}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Delete a transform.
     *
     * @tags Datasets
     * @name DeleteTransformApiV2DatasetsDatasetIdTransformsTransformIdDelete
     * @summary Delete Transform
     * @request DELETE:/api/v2/datasets/{dataset_id}/transforms/{transform_id}
     * @secure
     */
    deleteTransformApiV2DatasetsDatasetIdTransformsTransformIdDelete: (datasetId: string, transformId: string, params: RequestParams = {}) =>
      this.request<
        DeleteTransformApiV2DatasetsDatasetIdTransformsTransformIdDeleteData,
        DeleteTransformApiV2DatasetsDatasetIdTransformsTransformIdDeleteError
      >({
        path: `/api/v2/datasets/${datasetId}/transforms/${transformId}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Execute a RAG provider hybrid (keyword and vector similarity) search.
     *
     * @tags RAG Providers
     * @name ExecuteHybridSearchApiV1RagProvidersProviderIdHybridSearchPost
     * @summary Execute Hybrid Search
     * @request POST:/api/v1/rag_providers/{provider_id}/hybrid_search
     * @secure
     */
    executeHybridSearchApiV1RagProvidersProviderIdHybridSearchPost: (
      providerId: string,
      data: RagHybridSearchSettingRequest,
      params: RequestParams = {}
    ) =>
      this.request<
        ExecuteHybridSearchApiV1RagProvidersProviderIdHybridSearchPostData,
        ExecuteHybridSearchApiV1RagProvidersProviderIdHybridSearchPostError
      >({
        path: `/api/v1/rag_providers/${providerId}/hybrid_search`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Execute a RAG Provider Keyword (BM25/Sparse Vector) Search.
     *
     * @tags RAG Providers
     * @name ExecuteKeywordSearchApiV1RagProvidersProviderIdKeywordSearchPost
     * @summary Execute Keyword Search
     * @request POST:/api/v1/rag_providers/{provider_id}/keyword_search
     * @secure
     */
    executeKeywordSearchApiV1RagProvidersProviderIdKeywordSearchPost: (
      providerId: string,
      data: RagKeywordSearchSettingRequest,
      params: RequestParams = {}
    ) =>
      this.request<
        ExecuteKeywordSearchApiV1RagProvidersProviderIdKeywordSearchPostData,
        ExecuteKeywordSearchApiV1RagProvidersProviderIdKeywordSearchPostError
      >({
        path: `/api/v1/rag_providers/${providerId}/keyword_search`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Execute a RAG Provider Similarity Text Search.
     *
     * @tags RAG Providers
     * @name ExecuteSimilarityTextSearchApiV1RagProvidersProviderIdSimilarityTextSearchPost
     * @summary Execute Similarity Text Search
     * @request POST:/api/v1/rag_providers/{provider_id}/similarity_text_search
     * @secure
     */
    executeSimilarityTextSearchApiV1RagProvidersProviderIdSimilarityTextSearchPost: (
      providerId: string,
      data: RagVectorSimilarityTextSearchSettingRequest,
      params: RequestParams = {}
    ) =>
      this.request<
        ExecuteSimilarityTextSearchApiV1RagProvidersProviderIdSimilarityTextSearchPostData,
        ExecuteSimilarityTextSearchApiV1RagProvidersProviderIdSimilarityTextSearchPostError
      >({
        path: `/api/v1/rag_providers/${providerId}/similarity_text_search`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Execute a transform against a trace to extract data for dataset rows. Returns data in the format expected by the create dataset version API's rows_to_add parameter.
     *
     * @tags Datasets
     * @name ExecuteTransformEndpointApiV2DatasetsDatasetIdTransformsTransformIdExtractionsPost
     * @summary Execute Transform Endpoint
     * @request POST:/api/v2/datasets/{dataset_id}/transforms/{transform_id}/extractions
     * @secure
     */
    executeTransformEndpointApiV2DatasetsDatasetIdTransformsTransformIdExtractionsPost: (
      datasetId: string,
      transformId: string,
      data: ExecuteTransformRequest,
      params: RequestParams = {}
    ) =>
      this.request<
        ExecuteTransformEndpointApiV2DatasetsDatasetIdTransformsTransformIdExtractionsPostData,
        ExecuteTransformEndpointApiV2DatasetsDatasetIdTransformsTransformIdExtractionsPostError
      >({
        path: `/api/v2/datasets/${datasetId}/transforms/${transformId}/extractions`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Get an agentic prompt by name and version
     *
     * @tags Prompts
     * @name GetAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet
     * @summary Get an agentic prompt
     * @request GET:/api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}
     * @secure
     */
    getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet: (
      promptName: string,
      promptVersion: string,
      taskId: string,
      params: RequestParams = {}
    ) =>
      this.request<
        GetAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGetData,
        GetAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGetError
      >({
        path: `/api/v1/tasks/${taskId}/prompts/${promptName}/versions/${promptVersion}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get an agentic prompt by name and tag
     *
     * @tags Prompts
     * @name GetAgenticPromptByTagApiV1TasksTaskIdPromptsPromptNameVersionsTagsTagGet
     * @summary Get an agentic prompt by name and tag
     * @request GET:/api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/tags/{tag}
     * @secure
     */
    getAgenticPromptByTagApiV1TasksTaskIdPromptsPromptNameVersionsTagsTagGet: (
      promptName: string,
      tag: string,
      taskId: string,
      params: RequestParams = {}
    ) =>
      this.request<
        GetAgenticPromptByTagApiV1TasksTaskIdPromptsPromptNameVersionsTagsTagGetData,
        GetAgenticPromptByTagApiV1TasksTaskIdPromptsPromptNameVersionsTagsTagGetError
      >({
        path: `/api/v1/tasks/${taskId}/prompts/${promptName}/versions/tags/${tag}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get all agentic prompts for a given task with optional filtering.
     *
     * @tags Prompts
     * @name GetAllAgenticPromptsApiV1TasksTaskIdPromptsGet
     * @summary Get all agentic prompts
     * @request GET:/api/v1/tasks/{task_id}/prompts
     * @secure
     */
    getAllAgenticPromptsApiV1TasksTaskIdPromptsGet: (
      { taskId, ...query }: GetAllAgenticPromptsApiV1TasksTaskIdPromptsGetParams,
      params: RequestParams = {}
    ) =>
      this.request<GetAllAgenticPromptsApiV1TasksTaskIdPromptsGetData, GetAllAgenticPromptsApiV1TasksTaskIdPromptsGetError>({
        path: `/api/v1/tasks/${taskId}/prompts`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description List all versions of an agentic prompt with optional filtering.
     *
     * @tags Prompts
     * @name GetAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGet
     * @summary List all versions of an agentic prompt
     * @request GET:/api/v1/tasks/{task_id}/prompts/{prompt_name}/versions
     * @secure
     */
    getAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGet: (
      { promptName, taskId, ...query }: GetAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGetParams,
      params: RequestParams = {}
    ) =>
      this.request<
        GetAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGetData,
        GetAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGetError
      >({
        path: `/api/v1/tasks/${taskId}/prompts/${promptName}/versions`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get all llm evals for a given task with optional filtering.
     *
     * @tags LLMEvals
     * @name GetAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet
     * @summary Get all llm evals
     * @request GET:/api/v1/tasks/{task_id}/llm_evals
     * @secure
     */
    getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet: ({ taskId, ...query }: GetAllLlmEvalsApiV1TasksTaskIdLlmEvalsGetParams, params: RequestParams = {}) =>
      this.request<GetAllLlmEvalsApiV1TasksTaskIdLlmEvalsGetData, GetAllLlmEvalsApiV1TasksTaskIdLlmEvalsGetError>({
        path: `/api/v1/tasks/${taskId}/llm_evals`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description List all versions of an llm eval with optional filtering.
     *
     * @tags LLMEvals
     * @name GetAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet
     * @summary List all versions of an llm eval
     * @request GET:/api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions
     * @secure
     */
    getAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet: (
      { evalName, taskId, ...query }: GetAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGetParams,
      params: RequestParams = {}
    ) =>
      this.request<
        GetAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGetData,
        GetAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGetError
      >({
        path: `/api/v1/tasks/${taskId}/llm_evals/${evalName}/versions`,
        method: "GET",
        query: query,
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
    getConversationsApiChatConversationsGet: (query: GetConversationsApiChatConversationsGetParams, params: RequestParams = {}) =>
      this.request<GetConversationsApiChatConversationsGetData, GetConversationsApiChatConversationsGetError>({
        path: `/api/chat/conversations`,
        method: "GET",
        query: query,
        format: "json",
        ...params,
      }),

    /**
     * @description Get a dataset.
     *
     * @tags Datasets
     * @name GetDatasetApiV2DatasetsDatasetIdGet
     * @summary Get Dataset
     * @request GET:/api/v2/datasets/{dataset_id}
     * @secure
     */
    getDatasetApiV2DatasetsDatasetIdGet: (datasetId: string, params: RequestParams = {}) =>
      this.request<GetDatasetApiV2DatasetsDatasetIdGetData, GetDatasetApiV2DatasetsDatasetIdGetError>({
        path: `/api/v2/datasets/${datasetId}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Search datasets. Optionally can filter by dataset IDs and dataset name.
     *
     * @tags Datasets
     * @name GetDatasetsApiV2DatasetsSearchGet
     * @summary Get Datasets
     * @request GET:/api/v2/datasets/search
     * @secure
     */
    getDatasetsApiV2DatasetsSearchGet: (query: GetDatasetsApiV2DatasetsSearchGetParams, params: RequestParams = {}) =>
      this.request<GetDatasetsApiV2DatasetsSearchGetData, GetDatasetsApiV2DatasetsSearchGetError>({
        path: `/api/v2/datasets/search`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Fetch a dataset version.
     *
     * @tags Datasets
     * @name GetDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet
     * @summary Get Dataset Version
     * @request GET:/api/v2/datasets/{dataset_id}/versions/{version_number}
     * @secure
     */
    getDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGet: (
      { datasetId, versionNumber, ...query }: GetDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGetParams,
      params: RequestParams = {}
    ) =>
      this.request<
        GetDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGetData,
        GetDatasetVersionApiV2DatasetsDatasetIdVersionsVersionNumberGetError
      >({
        path: `/api/v2/datasets/${datasetId}/versions/${versionNumber}`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Fetch a specific row from a dataset version by row ID.
     *
     * @tags Datasets
     * @name GetDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGet
     * @summary Get Dataset Version Row
     * @request GET:/api/v2/datasets/{dataset_id}/versions/{version_number}/rows/{row_id}
     * @secure
     */
    getDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGet: (
      datasetId: string,
      versionNumber: number,
      rowId: string,
      params: RequestParams = {}
    ) =>
      this.request<
        GetDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGetData,
        GetDatasetVersionRowApiV2DatasetsDatasetIdVersionsVersionNumberRowsRowIdGetError
      >({
        path: `/api/v2/datasets/${datasetId}/versions/${versionNumber}/rows/${rowId}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description List dataset versions.
     *
     * @tags Datasets
     * @name GetDatasetVersionsApiV2DatasetsDatasetIdVersionsGet
     * @summary Get Dataset Versions
     * @request GET:/api/v2/datasets/{dataset_id}/versions
     * @secure
     */
    getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet: (
      { datasetId, ...query }: GetDatasetVersionsApiV2DatasetsDatasetIdVersionsGetParams,
      params: RequestParams = {}
    ) =>
      this.request<GetDatasetVersionsApiV2DatasetsDatasetIdVersionsGetData, GetDatasetVersionsApiV2DatasetsDatasetIdVersionsGetError>({
        path: `/api/v2/datasets/${datasetId}/versions`,
        method: "GET",
        query: query,
        secure: true,
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
     * @description Get paginated list of test case results for a prompt experiment
     *
     * @tags Prompt Experiments
     * @name GetExperimentTestCasesApiV1PromptExperimentsExperimentIdTestCasesGet
     * @summary Get experiment test cases
     * @request GET:/api/v1/prompt_experiments/{experiment_id}/test_cases
     * @secure
     */
    getExperimentTestCasesApiV1PromptExperimentsExperimentIdTestCasesGet: (
      { experimentId, ...query }: GetExperimentTestCasesApiV1PromptExperimentsExperimentIdTestCasesGetParams,
      params: RequestParams = {}
    ) =>
      this.request<
        GetExperimentTestCasesApiV1PromptExperimentsExperimentIdTestCasesGetData,
        GetExperimentTestCasesApiV1PromptExperimentsExperimentIdTestCasesGetError
      >({
        path: `/api/v1/prompt_experiments/${experimentId}/test_cases`,
        method: "GET",
        query: query,
        secure: true,
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
      this.request<GetInferenceDocumentContextApiChatContextInferenceIdGetData, GetInferenceDocumentContextApiChatContextInferenceIdGetError>({
        path: `/api/chat/context/${inferenceId}`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @description Get an llm eval by name and version
     *
     * @tags LLMEvals
     * @name GetLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet
     * @summary Get an llm eval
     * @request GET:/api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}
     * @secure
     */
    getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet: (
      evalName: string,
      evalVersion: string,
      taskId: string,
      params: RequestParams = {}
    ) =>
      this.request<
        GetLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGetData,
        GetLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGetError
      >({
        path: `/api/v1/tasks/${taskId}/llm_evals/${evalName}/versions/${evalVersion}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get an llm eval by name and tag
     *
     * @tags LLMEvals
     * @name GetLlmEvalByTagApiV1TasksTaskIdLlmEvalsEvalNameVersionsTagsTagGet
     * @summary Get an llm eval by name and tag
     * @request GET:/api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/tags/{tag}
     * @secure
     */
    getLlmEvalByTagApiV1TasksTaskIdLlmEvalsEvalNameVersionsTagsTagGet: (evalName: string, tag: string, taskId: string, params: RequestParams = {}) =>
      this.request<
        GetLlmEvalByTagApiV1TasksTaskIdLlmEvalsEvalNameVersionsTagsTagGetData,
        GetLlmEvalByTagApiV1TasksTaskIdLlmEvalsEvalNameVersionsTagsTagGetError
      >({
        path: `/api/v1/tasks/${taskId}/llm_evals/${evalName}/versions/tags/${tag}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Shows all model providers and if they're enabled.
     *
     * @tags Model Providers
     * @name GetModelProvidersApiV1ModelProvidersGet
     * @summary List the model providers.
     * @request GET:/api/v1/model_providers
     * @secure
     */
    getModelProvidersApiV1ModelProvidersGet: (params: RequestParams = {}) =>
      this.request<GetModelProvidersApiV1ModelProvidersGetData, any>({
        path: `/api/v1/model_providers`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Returns a list of the names of all available models for a provider.
     *
     * @tags Model Providers
     * @name GetModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGet
     * @summary List the models available from a provider.
     * @request GET:/api/v1/model_providers/{provider}/available_models
     * @secure
     */
    getModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGet: (provider: ModelProvider, params: RequestParams = {}) =>
      this.request<
        GetModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGetData,
        GetModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGetError
      >({
        path: `/api/v1/model_providers/${provider}/available_models`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get detailed information about a notebook including state and experiment history
     *
     * @tags Notebooks
     * @name GetNotebookApiV1NotebooksNotebookIdGet
     * @summary Get notebook details
     * @request GET:/api/v1/notebooks/{notebook_id}
     * @secure
     */
    getNotebookApiV1NotebooksNotebookIdGet: (notebookId: string, params: RequestParams = {}) =>
      this.request<GetNotebookApiV1NotebooksNotebookIdGetData, GetNotebookApiV1NotebooksNotebookIdGetError>({
        path: `/api/v1/notebooks/${notebookId}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get paginated list of experiments run from this notebook
     *
     * @tags Notebooks
     * @name GetNotebookHistoryApiV1NotebooksNotebookIdHistoryGet
     * @summary Get notebook history
     * @request GET:/api/v1/notebooks/{notebook_id}/history
     * @secure
     */
    getNotebookHistoryApiV1NotebooksNotebookIdHistoryGet: (
      { notebookId, ...query }: GetNotebookHistoryApiV1NotebooksNotebookIdHistoryGetParams,
      params: RequestParams = {}
    ) =>
      this.request<GetNotebookHistoryApiV1NotebooksNotebookIdHistoryGetData, GetNotebookHistoryApiV1NotebooksNotebookIdHistoryGetError>({
        path: `/api/v1/notebooks/${notebookId}/history`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get the current state (draft configuration) of a notebook
     *
     * @tags Notebooks
     * @name GetNotebookStateApiV1NotebooksNotebookIdStateGet
     * @summary Get notebook state
     * @request GET:/api/v1/notebooks/{notebook_id}/state
     * @secure
     */
    getNotebookStateApiV1NotebooksNotebookIdStateGet: (notebookId: string, params: RequestParams = {}) =>
      this.request<GetNotebookStateApiV1NotebooksNotebookIdStateGetData, GetNotebookStateApiV1NotebooksNotebookIdStateGetError>({
        path: `/api/v1/notebooks/${notebookId}/state`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get detailed information about a specific prompt experiment including summary results
     *
     * @tags Prompt Experiments
     * @name GetPromptExperimentApiV1PromptExperimentsExperimentIdGet
     * @summary Get prompt experiment details
     * @request GET:/api/v1/prompt_experiments/{experiment_id}
     * @secure
     */
    getPromptExperimentApiV1PromptExperimentsExperimentIdGet: (experimentId: string, params: RequestParams = {}) =>
      this.request<GetPromptExperimentApiV1PromptExperimentsExperimentIdGetData, GetPromptExperimentApiV1PromptExperimentsExperimentIdGetError>({
        path: `/api/v1/prompt_experiments/${experimentId}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get paginated list of results for a specific prompt within an experiment (supports both saved and unsaved prompts)
     *
     * @tags Prompt Experiments
     * @name GetPromptVersionResultsApiV1PromptExperimentsExperimentIdPromptsPromptKeyResultsGet
     * @summary Get prompt results
     * @request GET:/api/v1/prompt_experiments/{experiment_id}/prompts/{prompt_key}/results
     * @secure
     */
    getPromptVersionResultsApiV1PromptExperimentsExperimentIdPromptsPromptKeyResultsGet: (
      { experimentId, promptKey, ...query }: GetPromptVersionResultsApiV1PromptExperimentsExperimentIdPromptsPromptKeyResultsGetParams,
      params: RequestParams = {}
    ) =>
      this.request<
        GetPromptVersionResultsApiV1PromptExperimentsExperimentIdPromptsPromptKeyResultsGetData,
        GetPromptVersionResultsApiV1PromptExperimentsExperimentIdPromptsPromptKeyResultsGetError
      >({
        path: `/api/v1/prompt_experiments/${experimentId}/prompts/${promptKey}/results`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get a single RAG provider connection configuration.
     *
     * @tags RAG Providers
     * @name GetRagProviderApiV1RagProvidersProviderIdGet
     * @summary Get Rag Provider
     * @request GET:/api/v1/rag_providers/{provider_id}
     * @secure
     */
    getRagProviderApiV1RagProvidersProviderIdGet: (providerId: string, params: RequestParams = {}) =>
      this.request<GetRagProviderApiV1RagProvidersProviderIdGetData, GetRagProviderApiV1RagProvidersProviderIdGetError>({
        path: `/api/v1/rag_providers/${providerId}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get list of RAG provider connection configurations for the task.
     *
     * @tags RAG Providers
     * @name GetRagProvidersApiV1TasksTaskIdRagProvidersGet
     * @summary Get Rag Providers
     * @request GET:/api/v1/tasks/{task_id}/rag_providers
     * @secure
     */
    getRagProvidersApiV1TasksTaskIdRagProvidersGet: (
      { taskId, ...query }: GetRagProvidersApiV1TasksTaskIdRagProvidersGetParams,
      params: RequestParams = {}
    ) =>
      this.request<GetRagProvidersApiV1TasksTaskIdRagProvidersGetData, GetRagProvidersApiV1TasksTaskIdRagProvidersGetError>({
        path: `/api/v1/tasks/${taskId}/rag_providers`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get a single RAG setting configuration.
     *
     * @tags RAG Settings
     * @name GetRagSearchSetting
     * @summary Get Rag Search Setting
     * @request GET:/api/v1/rag_search_settings/{setting_configuration_id}
     * @secure
     */
    getRagSearchSetting: (settingConfigurationId: string, params: RequestParams = {}) =>
      this.request<GetRagSearchSettingData, GetRagSearchSettingError>({
        path: `/api/v1/rag_search_settings/${settingConfigurationId}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get list of versions for the RAG search setting configuration.
     *
     * @tags RAG Settings
     * @name GetRagSearchSettingConfigurationVersionsApiV1RagSearchSettingsSettingConfigurationIdVersionsGet
     * @summary Get Rag Search Setting Configuration Versions
     * @request GET:/api/v1/rag_search_settings/{setting_configuration_id}/versions
     * @secure
     */
    getRagSearchSettingConfigurationVersionsApiV1RagSearchSettingsSettingConfigurationIdVersionsGet: (
      { settingConfigurationId, ...query }: GetRagSearchSettingConfigurationVersionsApiV1RagSearchSettingsSettingConfigurationIdVersionsGetParams,
      params: RequestParams = {}
    ) =>
      this.request<
        GetRagSearchSettingConfigurationVersionsApiV1RagSearchSettingsSettingConfigurationIdVersionsGetData,
        GetRagSearchSettingConfigurationVersionsApiV1RagSearchSettingsSettingConfigurationIdVersionsGetError
      >({
        path: `/api/v1/rag_search_settings/${settingConfigurationId}/versions`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get a single RAG setting configuration version.
     *
     * @tags RAG Settings
     * @name GetRagSearchSettingVersion
     * @summary Get Rag Search Setting Version
     * @request GET:/api/v1/rag_search_settings/{setting_configuration_id}/versions/{version_number}
     * @secure
     */
    getRagSearchSettingVersion: (settingConfigurationId: string, versionNumber: number, params: RequestParams = {}) =>
      this.request<GetRagSearchSettingVersionData, GetRagSearchSettingVersionError>({
        path: `/api/v1/rag_search_settings/${settingConfigurationId}/versions/${versionNumber}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get a single RAG setting configuration version by tag.
     *
     * @tags RAG Settings
     * @name GetRagSearchSettingVersionByTag
     * @summary Get Rag Search Setting Version By Tag
     * @request GET:/api/v1/rag_search_settings/{setting_configuration_id}/versions/tags/{tag}
     * @secure
     */
    getRagSearchSettingVersionByTag: (settingConfigurationId: string, tag: string, params: RequestParams = {}) =>
      this.request<GetRagSearchSettingVersionByTagData, GetRagSearchSettingVersionByTagError>({
        path: `/api/v1/rag_search_settings/${settingConfigurationId}/versions/tags/${tag}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get all traces in a session. Returns list of full trace trees with existing metrics (no computation).
     *
     * @tags Sessions
     * @name GetSessionTracesApiV1TracesSessionsSessionIdGet
     * @summary Get Session Traces
     * @request GET:/api/v1/traces/sessions/{session_id}
     * @secure
     */
    getSessionTracesApiV1TracesSessionsSessionIdGet: (
      { sessionId, ...query }: GetSessionTracesApiV1TracesSessionsSessionIdGetParams,
      params: RequestParams = {}
    ) =>
      this.request<GetSessionTracesApiV1TracesSessionsSessionIdGetData, GetSessionTracesApiV1TracesSessionsSessionIdGetError>({
        path: `/api/v1/traces/sessions/${sessionId}`,
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
     * @name GetSpanByIdApiV1TracesSpansSpanIdGet
     * @summary Get Single Span
     * @request GET:/api/v1/traces/spans/{span_id}
     * @secure
     */
    getSpanByIdApiV1TracesSpansSpanIdGet: (spanId: string, params: RequestParams = {}) =>
      this.request<GetSpanByIdApiV1TracesSpansSpanIdGetData, GetSpanByIdApiV1TracesSpansSpanIdGetError>({
        path: `/api/v1/traces/spans/${spanId}`,
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
     * @description Get list of RAG search setting configurations for the task.
     *
     * @tags RAG Settings
     * @name GetTaskRagSearchSettingsApiV1TasksTaskIdRagSearchSettingsGet
     * @summary Get Task Rag Search Settings
     * @request GET:/api/v1/tasks/{task_id}/rag_search_settings
     * @secure
     */
    getTaskRagSearchSettingsApiV1TasksTaskIdRagSearchSettingsGet: (
      { taskId, ...query }: GetTaskRagSearchSettingsApiV1TasksTaskIdRagSearchSettingsGetParams,
      params: RequestParams = {}
    ) =>
      this.request<
        GetTaskRagSearchSettingsApiV1TasksTaskIdRagSearchSettingsGetData,
        GetTaskRagSearchSettingsApiV1TasksTaskIdRagSearchSettingsGetError
      >({
        path: `/api/v1/tasks/${taskId}/rag_search_settings`,
        method: "GET",
        query: query,
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
     * @description Get a specific transform.
     *
     * @tags Datasets
     * @name GetTransformApiV2DatasetsDatasetIdTransformsTransformIdGet
     * @summary Get Transform
     * @request GET:/api/v2/datasets/{dataset_id}/transforms/{transform_id}
     * @secure
     */
    getTransformApiV2DatasetsDatasetIdTransformsTransformIdGet: (datasetId: string, transformId: string, params: RequestParams = {}) =>
      this.request<GetTransformApiV2DatasetsDatasetIdTransformsTransformIdGetData, GetTransformApiV2DatasetsDatasetIdTransformsTransformIdGetError>({
        path: `/api/v2/datasets/${datasetId}/transforms/${transformId}`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Gets the list of variables needed from an unsaved prompt's messages
     *
     * @tags Prompts
     * @name GetUnsavedPromptVariablesListApiV1PromptVariablesPost
     * @summary Gets the list of variables needed from an unsaved prompt's messages
     * @request POST:/api/v1/prompt_variables
     * @secure
     */
    getUnsavedPromptVariablesListApiV1PromptVariablesPost: (data: UnsavedPromptVariablesRequest, params: RequestParams = {}) =>
      this.request<GetUnsavedPromptVariablesListApiV1PromptVariablesPostData, GetUnsavedPromptVariablesListApiV1PromptVariablesPostError>({
        path: `/api/v1/prompt_variables`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Get detailed information for a single user including session and trace metadata.
     *
     * @tags Users
     * @name GetUserDetailsApiV1TracesUsersUserIdGet
     * @summary Get User Details
     * @request GET:/api/v1/traces/users/{user_id}
     * @secure
     */
    getUserDetailsApiV1TracesUsersUserIdGet: ({ userId, ...query }: GetUserDetailsApiV1TracesUsersUserIdGetParams, params: RequestParams = {}) =>
      this.request<GetUserDetailsApiV1TracesUsersUserIdGetData, GetUserDetailsApiV1TracesUsersUserIdGetError>({
        path: `/api/v1/traces/users/${userId}`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description List all notebooks for a task with pagination
     *
     * @tags Notebooks
     * @name ListNotebooksApiV1TasksTaskIdNotebooksGet
     * @summary List notebooks
     * @request GET:/api/v1/tasks/{task_id}/notebooks
     * @secure
     */
    listNotebooksApiV1TasksTaskIdNotebooksGet: ({ taskId, ...query }: ListNotebooksApiV1TasksTaskIdNotebooksGetParams, params: RequestParams = {}) =>
      this.request<ListNotebooksApiV1TasksTaskIdNotebooksGetData, ListNotebooksApiV1TasksTaskIdNotebooksGetError>({
        path: `/api/v1/tasks/${taskId}/notebooks`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description List all prompt experiments for a task with optional filtering and pagination
     *
     * @tags Prompt Experiments
     * @name ListPromptExperimentsApiV1TasksTaskIdPromptExperimentsGet
     * @summary List prompt experiments
     * @request GET:/api/v1/tasks/{task_id}/prompt_experiments
     * @secure
     */
    listPromptExperimentsApiV1TasksTaskIdPromptExperimentsGet: (
      { taskId, ...query }: ListPromptExperimentsApiV1TasksTaskIdPromptExperimentsGetParams,
      params: RequestParams = {}
    ) =>
      this.request<ListPromptExperimentsApiV1TasksTaskIdPromptExperimentsGetData, ListPromptExperimentsApiV1TasksTaskIdPromptExperimentsGetError>({
        path: `/api/v1/tasks/${taskId}/prompt_experiments`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Lists all available vector database collections.
     *
     * @tags RAG Providers
     * @name ListRagProviderCollectionsApiV1RagProvidersProviderIdCollectionsGet
     * @summary List Rag Provider Collections
     * @request GET:/api/v1/rag_providers/{provider_id}/collections
     * @secure
     */
    listRagProviderCollectionsApiV1RagProvidersProviderIdCollectionsGet: (providerId: string, params: RequestParams = {}) =>
      this.request<
        ListRagProviderCollectionsApiV1RagProvidersProviderIdCollectionsGetData,
        ListRagProviderCollectionsApiV1RagProvidersProviderIdCollectionsGetError
      >({
        path: `/api/v1/rag_providers/${providerId}/collections`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get session metadata with pagination and filtering. Returns aggregated session information.
     *
     * @tags Sessions
     * @name ListSessionsMetadataApiV1TracesSessionsGet
     * @summary List Session Metadata
     * @request GET:/api/v1/traces/sessions
     * @secure
     */
    listSessionsMetadataApiV1TracesSessionsGet: (query: ListSessionsMetadataApiV1TracesSessionsGetParams, params: RequestParams = {}) =>
      this.request<ListSessionsMetadataApiV1TracesSessionsGetData, ListSessionsMetadataApiV1TracesSessionsGetError>({
        path: `/api/v1/traces/sessions`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get lightweight span metadata with comprehensive filtering support. Returns individual spans that match filtering criteria with the same filtering capabilities as trace filtering. Supports trace-level filters, span-level filters, and metric filters.
     *
     * @tags Spans
     * @name ListSpansMetadataApiV1TracesSpansGet
     * @summary List Span Metadata with Filtering
     * @request GET:/api/v1/traces/spans
     * @secure
     */
    listSpansMetadataApiV1TracesSpansGet: (query: ListSpansMetadataApiV1TracesSpansGetParams, params: RequestParams = {}) =>
      this.request<ListSpansMetadataApiV1TracesSpansGetData, ListSpansMetadataApiV1TracesSpansGetError>({
        path: `/api/v1/traces/spans`,
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
     * @description List all transforms for a dataset.
     *
     * @tags Datasets
     * @name ListTransformsApiV2DatasetsDatasetIdTransformsGet
     * @summary List Transforms
     * @request GET:/api/v2/datasets/{dataset_id}/transforms
     * @secure
     */
    listTransformsApiV2DatasetsDatasetIdTransformsGet: (datasetId: string, params: RequestParams = {}) =>
      this.request<ListTransformsApiV2DatasetsDatasetIdTransformsGetData, ListTransformsApiV2DatasetsDatasetIdTransformsGetError>({
        path: `/api/v2/datasets/${datasetId}/transforms`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Get user metadata with pagination and filtering. Returns aggregated user information across sessions and traces.
     *
     * @tags Users
     * @name ListUsersMetadataApiV1TracesUsersGet
     * @summary List User Metadata
     * @request GET:/api/v1/traces/users
     * @secure
     */
    listUsersMetadataApiV1TracesUsersGet: (query: ListUsersMetadataApiV1TracesUsersGetParams, params: RequestParams = {}) =>
      this.request<ListUsersMetadataApiV1TracesUsersGetData, ListUsersMetadataApiV1TracesUsersGetError>({
        path: `/api/v1/traces/users`,
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
    postChatFeedbackApiChatFeedbackInferenceIdPost: (inferenceId: string, data: FeedbackRequest, params: RequestParams = {}) =>
      this.request<PostChatFeedbackApiChatFeedbackInferenceIdPostData, PostChatFeedbackApiChatFeedbackInferenceIdPostError>({
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
    postFeedbackApiV2FeedbackInferenceIdPost: (inferenceId: string, data: FeedbackRequest, params: RequestParams = {}) =>
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
    queryInferencesApiV2InferencesQueryGet: (query: QueryInferencesApiV2InferencesQueryGetParams, params: RequestParams = {}) =>
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
     * @description Render a specific version of an existing agentic prompt by replacing template variables with provided values. Returns the rendered messages.
     *
     * @tags Prompts
     * @name RenderSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionRendersPost
     * @summary Render a specific version of an agentic prompt with variables
     * @request POST:/api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/renders
     * @secure
     */
    renderSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionRendersPost: (
      promptName: string,
      promptVersion: string,
      taskId: string,
      data: SavedPromptRenderingRequest,
      params: RequestParams = {}
    ) =>
      this.request<
        RenderSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionRendersPostData,
        RenderSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionRendersPostError
      >({
        path: `/api/v1/tasks/${taskId}/prompts/${promptName}/versions/${promptVersion}/renders`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Render an unsaved prompt by replacing template variables with provided values. Accepts messages directly in the request body instead of loading from database.
     *
     * @tags Prompts
     * @name RenderUnsavedAgenticPromptApiV1PromptRendersPost
     * @summary Render an unsaved prompt with variables
     * @request POST:/api/v1/prompt_renders
     * @secure
     */
    renderUnsavedAgenticPromptApiV1PromptRendersPost: (data: UnsavedPromptRenderingRequest, params: RequestParams = {}) =>
      this.request<RenderUnsavedAgenticPromptApiV1PromptRendersPostData, RenderUnsavedAgenticPromptApiV1PromptRendersPostError>({
        path: `/api/v1/prompt_renders`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description This endpoint re-encrypts all the secrets in the database. The procedure calling this endpoint is as follows: First: Deploy a new version of the service with GENAI_ENGINE_SECRET_STORE_KEY set to a value like 'new-key::old-key'. Second: call this endpoint - all secrets will be re-encrypted with 'new-key'. Third: Deploy a new version of the service removing the old key from GENAI_ENGINE_SECRET_STORE_KEY, like 'new-key'. At this point all existing and new secrets will be managed by 'new-key'.
     *
     * @tags Secrets
     * @name RotateSecretsApiV1SecretsRotationPost
     * @summary Rotates secrets
     * @request POST:/api/v1/secrets/rotation
     * @secure
     */
    rotateSecretsApiV1SecretsRotationPost: (params: RequestParams = {}) =>
      this.request<RotateSecretsApiV1SecretsRotationPostData, any>({
        path: `/api/v1/secrets/rotation`,
        method: "POST",
        secure: true,
        ...params,
      }),

    /**
     * @description Runs or streams an unsaved agentic prompt
     *
     * @tags Prompts
     * @name RunAgenticPromptApiV1CompletionsPost
     * @summary Run/Stream an unsaved agentic prompt
     * @request POST:/api/v1/completions
     * @secure
     */
    runAgenticPromptApiV1CompletionsPost: (data: CompletionRequest, params: RequestParams = {}) =>
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
     * @description Run or stream a specific version of an existing agentic prompt
     *
     * @tags Prompts
     * @name RunSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionCompletionsPost
     * @summary Run/Stream a specific version of an agentic prompt
     * @request POST:/api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/completions
     * @secure
     */
    runSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionCompletionsPost: (
      promptName: string,
      promptVersion: string,
      taskId: string,
      data: PromptCompletionRequest,
      params: RequestParams = {}
    ) =>
      this.request<
        RunSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionCompletionsPostData,
        RunSavedAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionCompletionsPostError
      >({
        path: `/api/v1/tasks/${taskId}/prompts/${promptName}/versions/${promptVersion}/completions`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Run a saved llm eval
     *
     * @tags LLMEvals
     * @name RunSavedLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionCompletionsPost
     * @summary Run a saved llm eval
     * @request POST:/api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}/completions
     * @secure
     */
    runSavedLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionCompletionsPost: (
      evalName: string,
      evalVersion: string,
      taskId: string,
      data: BaseCompletionRequest,
      params: RequestParams = {}
    ) =>
      this.request<
        RunSavedLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionCompletionsPostData,
        RunSavedLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionCompletionsPostError
      >({
        path: `/api/v1/tasks/${taskId}/llm_evals/${evalName}/versions/${evalVersion}/completions`,
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
     * @tags Prompts
     * @name SaveAgenticPromptApiV1TasksTaskIdPromptsPromptNamePost
     * @summary Save an agentic prompt
     * @request POST:/api/v1/tasks/{task_id}/prompts/{prompt_name}
     * @secure
     */
    saveAgenticPromptApiV1TasksTaskIdPromptsPromptNamePost: (
      promptName: string,
      taskId: string,
      data: CreateAgenticPromptRequest,
      params: RequestParams = {}
    ) =>
      this.request<SaveAgenticPromptApiV1TasksTaskIdPromptsPromptNamePostData, SaveAgenticPromptApiV1TasksTaskIdPromptsPromptNamePostError>({
        path: `/api/v1/tasks/${taskId}/prompts/${promptName}`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Save an llm eval to the database
     *
     * @tags LLMEvals
     * @name SaveLlmEvalApiV1TasksTaskIdLlmEvalsEvalNamePost
     * @summary Save an llm eval
     * @request POST:/api/v1/tasks/{task_id}/llm_evals/{eval_name}
     * @secure
     */
    saveLlmEvalApiV1TasksTaskIdLlmEvalsEvalNamePost: (evalName: string, taskId: string, data: CreateEvalRequest, params: RequestParams = {}) =>
      this.request<SaveLlmEvalApiV1TasksTaskIdLlmEvalsEvalNamePostData, SaveLlmEvalApiV1TasksTaskIdLlmEvalsEvalNamePostError>({
        path: `/api/v1/tasks/${taskId}/llm_evals/${evalName}`,
        method: "POST",
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
    searchRulesApiV2RulesSearchPost: (query: SearchRulesApiV2RulesSearchPostParams, data: SearchRulesRequest, params: RequestParams = {}) =>
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
    searchTasksApiV2TasksSearchPost: (query: SearchTasksApiV2TasksSearchPostParams, data: SearchTasksRequest, params: RequestParams = {}) =>
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
     * @description Set the configuration for a model provider
     *
     * @tags Model Providers
     * @name SetModelProviderApiV1ModelProvidersProviderPut
     * @summary Set the configuration for a model provider.
     * @request PUT:/api/v1/model_providers/{provider}
     * @secure
     */
    setModelProviderApiV1ModelProvidersProviderPut: (provider: ModelProvider, data: PutModelProviderCredentials, params: RequestParams = {}) =>
      this.request<SetModelProviderApiV1ModelProvidersProviderPutData, SetModelProviderApiV1ModelProvidersProviderPutError>({
        path: `/api/v1/model_providers/${provider}`,
        method: "PUT",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Set the state (draft configuration) of a notebook
     *
     * @tags Notebooks
     * @name SetNotebookStateApiV1NotebooksNotebookIdStatePut
     * @summary Set notebook state
     * @request PUT:/api/v1/notebooks/{notebook_id}/state
     * @secure
     */
    setNotebookStateApiV1NotebooksNotebookIdStatePut: (notebookId: string, data: SetNotebookStateRequest, params: RequestParams = {}) =>
      this.request<SetNotebookStateApiV1NotebooksNotebookIdStatePutData, SetNotebookStateApiV1NotebooksNotebookIdStatePutError>({
        path: `/api/v1/notebooks/${notebookId}/state`,
        method: "PUT",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Deletes a specific version of an llm eval
     *
     * @tags LLMEvals
     * @name SoftDeleteLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionDelete
     * @summary Delete an llm eval version
     * @request DELETE:/api/v1/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}
     * @secure
     */
    softDeleteLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionDelete: (
      evalName: string,
      evalVersion: string,
      taskId: string,
      params: RequestParams = {}
    ) =>
      this.request<
        SoftDeleteLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionDeleteData,
        SoftDeleteLlmEvalVersionApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionDeleteError
      >({
        path: `/api/v1/tasks/${taskId}/llm_evals/${evalName}/versions/${evalVersion}`,
        method: "DELETE",
        secure: true,
        ...params,
      }),

    /**
     * @description Test a new RAG provider connection configuration.
     *
     * @tags RAG Providers
     * @name TestRagProviderConnectionApiV1TasksTaskIdRagProvidersTestConnectionPost
     * @summary Test Rag Provider Connection
     * @request POST:/api/v1/tasks/{task_id}/rag_providers/test_connection
     * @secure
     */
    testRagProviderConnectionApiV1TasksTaskIdRagProvidersTestConnectionPost: (
      taskId: string,
      data: RagProviderTestConfigurationRequest,
      params: RequestParams = {}
    ) =>
      this.request<
        TestRagProviderConnectionApiV1TasksTaskIdRagProvidersTestConnectionPostData,
        TestRagProviderConnectionApiV1TasksTaskIdRagProvidersTestConnectionPostError
      >({
        path: `/api/v1/tasks/${taskId}/rag_providers/test_connection`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Update a dataset.
     *
     * @tags Datasets
     * @name UpdateDatasetApiV2DatasetsDatasetIdPatch
     * @summary Update Dataset
     * @request PATCH:/api/v2/datasets/{dataset_id}
     * @secure
     */
    updateDatasetApiV2DatasetsDatasetIdPatch: (datasetId: string, data: DatasetUpdateRequest, params: RequestParams = {}) =>
      this.request<UpdateDatasetApiV2DatasetsDatasetIdPatchData, UpdateDatasetApiV2DatasetsDatasetIdPatchError>({
        path: `/api/v2/datasets/${datasetId}`,
        method: "PATCH",
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
     * @description Update notebook name or description (not the state)
     *
     * @tags Notebooks
     * @name UpdateNotebookApiV1NotebooksNotebookIdPut
     * @summary Update notebook metadata
     * @request PUT:/api/v1/notebooks/{notebook_id}
     * @secure
     */
    updateNotebookApiV1NotebooksNotebookIdPut: (notebookId: string, data: UpdateNotebookRequest, params: RequestParams = {}) =>
      this.request<UpdateNotebookApiV1NotebooksNotebookIdPutData, UpdateNotebookApiV1NotebooksNotebookIdPutError>({
        path: `/api/v1/notebooks/${notebookId}`,
        method: "PUT",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Update a single RAG provider connection configuration.
     *
     * @tags RAG Providers
     * @name UpdateRagProviderApiV1RagProvidersProviderIdPatch
     * @summary Update Rag Provider
     * @request PATCH:/api/v1/rag_providers/{provider_id}
     * @secure
     */
    updateRagProviderApiV1RagProvidersProviderIdPatch: (
      providerId: string,
      data: RagProviderConfigurationUpdateRequest,
      params: RequestParams = {}
    ) =>
      this.request<UpdateRagProviderApiV1RagProvidersProviderIdPatchData, UpdateRagProviderApiV1RagProvidersProviderIdPatchError>({
        path: `/api/v1/rag_providers/${providerId}`,
        method: "PATCH",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Update a single RAG search setting configuration.
     *
     * @tags RAG Settings
     * @name UpdateRagSearchSettingsApiV1RagSearchSettingsSettingConfigurationIdPatch
     * @summary Update Rag Search Settings
     * @request PATCH:/api/v1/rag_search_settings/{setting_configuration_id}
     * @secure
     */
    updateRagSearchSettingsApiV1RagSearchSettingsSettingConfigurationIdPatch: (
      settingConfigurationId: string,
      data: RagSearchSettingConfigurationUpdateRequest,
      params: RequestParams = {}
    ) =>
      this.request<
        UpdateRagSearchSettingsApiV1RagSearchSettingsSettingConfigurationIdPatchData,
        UpdateRagSearchSettingsApiV1RagSearchSettingsSettingConfigurationIdPatchError
      >({
        path: `/api/v1/rag_search_settings/${settingConfigurationId}`,
        method: "PATCH",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Update a single RAG search setting configuration version metadata.
     *
     * @tags RAG Settings
     * @name UpdateRagSearchSettingsVersionApiV1RagSearchSettingsSettingConfigurationIdVersionsVersionNumberPatch
     * @summary Update Rag Search Settings Version
     * @request PATCH:/api/v1/rag_search_settings/{setting_configuration_id}/versions/{version_number}
     * @secure
     */
    updateRagSearchSettingsVersionApiV1RagSearchSettingsSettingConfigurationIdVersionsVersionNumberPatch: (
      settingConfigurationId: string,
      versionNumber: number,
      data: RagSearchSettingConfigurationVersionUpdateRequest,
      params: RequestParams = {}
    ) =>
      this.request<
        UpdateRagSearchSettingsVersionApiV1RagSearchSettingsSettingConfigurationIdVersionsVersionNumberPatchData,
        UpdateRagSearchSettingsVersionApiV1RagSearchSettingsSettingConfigurationIdVersionsVersionNumberPatchError
      >({
        path: `/api/v1/rag_search_settings/${settingConfigurationId}/versions/${versionNumber}`,
        method: "PATCH",
        body: data,
        secure: true,
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
    updateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatch: (taskId: string, metricId: string, data: UpdateMetricRequest, params: RequestParams = {}) =>
      this.request<UpdateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatchData, UpdateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatchError>({
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
    updateTaskRulesApiV2TasksTaskIdRulesRuleIdPatch: (taskId: string, ruleId: string, data: UpdateRuleRequest, params: RequestParams = {}) =>
      this.request<UpdateTaskRulesApiV2TasksTaskIdRulesRuleIdPatchData, UpdateTaskRulesApiV2TasksTaskIdRulesRuleIdPatchError>({
        path: `/api/v2/tasks/${taskId}/rules/${ruleId}`,
        method: "PATCH",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Update a transform.
     *
     * @tags Datasets
     * @name UpdateTransformApiV2DatasetsDatasetIdTransformsTransformIdPut
     * @summary Update Transform
     * @request PUT:/api/v2/datasets/{dataset_id}/transforms/{transform_id}
     * @secure
     */
    updateTransformApiV2DatasetsDatasetIdTransformsTransformIdPut: (
      datasetId: string,
      transformId: string,
      data: DatasetTransformUpdateRequest,
      params: RequestParams = {}
    ) =>
      this.request<
        UpdateTransformApiV2DatasetsDatasetIdTransformsTransformIdPutData,
        UpdateTransformApiV2DatasetsDatasetIdTransformsTransformIdPutError
      >({
        path: `/api/v2/datasets/${datasetId}/transforms/${transformId}`,
        method: "PUT",
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
      params: RequestParams = {}
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
    validatePromptEndpointApiV2TasksTaskIdValidatePromptPost: (taskId: string, data: PromptValidationRequest, params: RequestParams = {}) =>
      this.request<ValidatePromptEndpointApiV2TasksTaskIdValidatePromptPostData, ValidatePromptEndpointApiV2TasksTaskIdValidatePromptPostError>({
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
      params: RequestParams = {}
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
      this.request<DeactivateApiKeyAuthApiKeysDeactivateApiKeyIdDeleteData, DeactivateApiKeyAuthApiKeysDeactivateApiKeyIdDeleteError>({
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
    querySpansWithMetricsV1TracesMetricsGet: (query: QuerySpansWithMetricsV1TracesMetricsGetParams, params: RequestParams = {}) =>
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
    checkUserPermissionUsersPermissionsCheckGet: (query: CheckUserPermissionUsersPermissionsCheckGetParams, params: RequestParams = {}) =>
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
    resetUserPasswordUsersUserIdResetPasswordPost: (userId: string, data: PasswordResetRequest, params: RequestParams = {}) =>
      this.request<ResetUserPasswordUsersUserIdResetPasswordPostData, ResetUserPasswordUsersUserIdResetPasswordPostError>({
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
