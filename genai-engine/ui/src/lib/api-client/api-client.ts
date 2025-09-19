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
export enum APIKeysRolesEnum {
  DEFAULTRULEADMIN = "DEFAULT-RULE-ADMIN",
  TASKADMIN = "TASK-ADMIN",
  VALIDATIONUSER = "VALIDATION-USER",
  ORGAUDITOR = "ORG-AUDITOR",
  ORGADMIN = "ORG-ADMIN",
}

/** ApiKeyResponse */
export interface ApiKeyResponse {
  /**
   * Id
   * ID of the key
   */
  id: string;
  /**
   * Key
   * The generated GenAI Engine API key. The key is displayed on key creation request only.
   */
  key?: string | null;
  /**
   * Description
   * Description of the API key
   */
  description?: string | null;
  /**
   * Is Active
   * Status of the key.
   */
  is_active: boolean;
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

/** AuthUserRole */
export interface AuthUserRole {
  /** Id */
  id?: string | null;
  /** Name */
  name: string;
  /** Description */
  description: string;
  /** Composite */
  composite: boolean;
}

/** BaseDetailsResponse */
export interface BaseDetailsResponse {
  /** Score */
  score?: boolean | null;
  /** Message */
  message?: string | null;
}

/** Body_upload_embeddings_file_api_chat_files_post */
export interface BodyUploadEmbeddingsFileApiChatFilesPost {
  /**
   * File
   * @format binary
   */
  file: File;
}

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
  /** Id */
  id: string;
  /** Seq Num */
  seq_num: number;
  /** Context */
  context: string;
}

/** ChatRequest */
export interface ChatRequest {
  /**
   * User Prompt
   * Prompt user wants to send to chat.
   */
  user_prompt: string;
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
}

/** ChatResponse */
export interface ChatResponse {
  /**
   * Inference Id
   * ID of the inference sent to the chat
   */
  inference_id: string;
  /**
   * Conversation Id
   * ID of the conversation session
   */
  conversation_id: string;
  /**
   * Timestamp
   * Time the inference was made in unix milliseconds
   */
  timestamp: number;
  /**
   * Retrieved Context
   * related sections of documents that were most relevant to the inference prompt. Formatted as a list of retrieved context chunks which include document name, seq num, and context.
   */
  retrieved_context: ChatDocumentContext[];
  /**
   * Llm Response
   * response from the LLM for the original user prompt
   */
  llm_response: string;
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

/** CreateUserRequest */
export interface CreateUserRequest {
  /** Email */
  email: string;
  /** Password */
  password: string;
  /**
   * Temporary
   * @default true
   */
  temporary?: boolean;
  /** Roles */
  roles: string[];
  /** Firstname */
  firstName: string;
  /** Lastname */
  lastName: string;
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

/** ExternalDocument */
export interface ExternalDocument {
  /** Id */
  id: string;
  /** Name */
  name: string;
  /** Type */
  type: string;
  /** Owner Id */
  owner_id: string;
}

/** ExternalInference */
export interface ExternalInference {
  /** Id */
  id: string;
  result: RuleResultEnum;
  /** Created At */
  created_at: number;
  /** Updated At */
  updated_at: number;
  /** Task Id */
  task_id?: string | null;
  /** Task Name */
  task_name?: string | null;
  /** Conversation Id */
  conversation_id?: string | null;
  inference_prompt: ExternalInferencePrompt;
  inference_response?: ExternalInferenceResponse | null;
  /** Inference Feedback */
  inference_feedback: InferenceFeedbackResponse[];
  /** User Id */
  user_id?: string | null;
}

/** ExternalInferencePrompt */
export interface ExternalInferencePrompt {
  /** Id */
  id: string;
  /** Inference Id */
  inference_id: string;
  result: RuleResultEnum;
  /** Created At */
  created_at: number;
  /** Updated At */
  updated_at: number;
  /** Message */
  message: string;
  /** Prompt Rule Results */
  prompt_rule_results: ExternalRuleResult[];
  /** Tokens */
  tokens?: number | null;
}

/** ExternalInferenceResponse */
export interface ExternalInferenceResponse {
  /** Id */
  id: string;
  /** Inference Id */
  inference_id: string;
  result: RuleResultEnum;
  /** Created At */
  created_at: number;
  /** Updated At */
  updated_at: number;
  /** Message */
  message: string;
  /** Context */
  context?: string | null;
  /** Response Rule Results */
  response_rule_results: ExternalRuleResult[];
  /** Tokens */
  tokens?: number | null;
}

/**
 * ExternalRuleResult
 * @example {"id":"90f18c69-d793-4913-9bde-a0c7f3643de0","name":"PII Rule","result":"Pass"}
 */
export interface ExternalRuleResult {
  /**
   * Id
   *  ID of the rule
   */
  id: string;
  /**
   * Name
   * Name of the rule
   */
  name: string;
  /** Type of the rule */
  rule_type: RuleType;
  /** Scope of the rule. The rule can be set at default level or task level. */
  scope: RuleScope;
  /** Result if the rule */
  result: RuleResultEnum;
  /**
   * Latency Ms
   * Duration in millisesconds of rule execution
   */
  latency_ms: number;
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
}

/** FeedbackRequest */
export interface FeedbackRequest {
  target: InferenceFeedbackTarget;
  /** Score */
  score: number;
  /** Reason */
  reason: string | null;
  /** User Id */
  user_id?: string | null;
}

/** FileUploadResult */
export interface FileUploadResult {
  /** Id */
  id: string;
  /** Name */
  name: string;
  /** Type */
  type: string;
  /** Word Count */
  word_count: number;
  /** Success */
  success: boolean;
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
  /** Valid */
  valid: boolean;
  /** Reason */
  reason: string;
  /**
   * Order Number
   * This field is a helper for ordering the claims
   * @default -1
   */
  order_number?: number | null;
}

/** HallucinationDetailsResponse */
export interface HallucinationDetailsResponse {
  /** Score */
  score?: boolean | null;
  /** Message */
  message?: string | null;
  /** Claims */
  claims: HallucinationClaimResponse[];
}

/** InferenceFeedbackResponse */
export interface InferenceFeedbackResponse {
  /** Id */
  id: string;
  /** Inference Id */
  inference_id: string;
  target: InferenceFeedbackTarget;
  /** Score */
  score: number;
  /** Reason */
  reason?: string | null;
  /** User Id */
  user_id?: string | null;
  /**
   * Created At
   * @format date-time
   */
  created_at: string;
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
}

/** InferenceFeedbackTarget */
export enum InferenceFeedbackTarget {
  Context = "context",
  ResponseResults = "response_results",
  PromptResults = "prompt_results",
}

/** KeywordDetailsResponse */
export interface KeywordDetailsResponse {
  /** Score */
  score?: boolean | null;
  /** Message */
  message?: string | null;
  /**
   * Keyword Matches
   * Each keyword in this list corresponds to a keyword that was both configured in the rule that was run and found in the input text.
   * @default []
   */
  keyword_matches?: KeywordSpanResponse[];
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

/** MetricResponse */
export interface MetricResponse {
  /**
   * Id
   * ID of the Metric
   */
  id: string;
  /**
   * Name
   * Name of the Metric
   */
  name: string;
  /** Type of the Metric */
  type: MetricType;
  /**
   * Metric Metadata
   * Metadata of the Metric
   */
  metric_metadata: string;
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
   * Updated At
   * Time the Metric was updated in unix milliseconds
   * @format date-time
   */
  updated_at: string;
  /**
   * Enabled
   * Whether the Metric is enabled
   */
  enabled?: boolean | null;
}

/** MetricResultResponse */
export interface MetricResultResponse {
  /**
   * Id
   * ID of the metric result
   */
  id: string;
  /** Type of the metric */
  metric_type: MetricType;
  /**
   * Details
   * JSON-serialized metric details
   */
  details?: string | null;
  /**
   * Prompt Tokens
   * Number of prompt tokens used
   */
  prompt_tokens: number;
  /**
   * Completion Tokens
   * Number of completion tokens used
   */
  completion_tokens: number;
  /**
   * Latency Ms
   * Latency in milliseconds
   */
  latency_ms: number;
  /**
   * Span Id
   * ID of the span this result belongs to
   */
  span_id: string;
  /**
   * Metric Id
   * ID of the metric that generated this result
   */
  metric_id: string;
  /**
   * Created At
   * Time the result was created
   * @format date-time
   */
  created_at: string;
  /**
   * Updated At
   * Time the result was last updated
   * @format date-time
   */
  updated_at: string;
}

/** MetricType */
export enum MetricType {
  QueryRelevance = "QueryRelevance",
  ResponseRelevance = "ResponseRelevance",
  ToolSelection = "ToolSelection",
}

/**
 * NestedSpanWithMetricsResponse
 * Nested span response with children for building span trees
 */
export interface NestedSpanWithMetricsResponse {
  /** Id */
  id: string;
  /** Trace Id */
  trace_id: string;
  /** Span Id */
  span_id: string;
  /** Parent Span Id */
  parent_span_id?: string | null;
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
   * End Time
   * @format date-time
   */
  end_time: string;
  /** Task Id */
  task_id?: string | null;
  /**
   * Created At
   * @format date-time
   */
  created_at: string;
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
  /** Raw Data */
  raw_data: Record<string, any>;
  /** System Prompt */
  system_prompt?: string | null;
  /** User Query */
  user_query?: string | null;
  /** Response */
  response?: string | null;
  /** Context */
  context?: Record<string, any>[] | null;
  /**
   * Metric Results
   * List of metric results for this span
   * @default []
   */
  metric_results?: MetricResultResponse[];
  /**
   * Children
   * Child spans nested under this span
   * @default []
   */
  children?: NestedSpanWithMetricsResponse[];
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
  /** Type of the metric. It can only be one of QueryRelevance, ResponseRelevance, ToolSelection */
  type: MetricType;
  /**
   * Name
   * Name of metric
   */
  name: string;
  /**
   * Metric Metadata
   * Additional metadata for the metric
   */
  metric_metadata: string;
  /** Configuration for the metric. Currently only applies to UserQueryRelevance and ResponseRelevance metric types. */
  config?: RelevanceMetricConfig | null;
}

/** NewRuleRequest */
export interface NewRuleRequest {
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
   * Config for the rule
   */
  config?: RegexConfig | KeywordsConfig | ToxicityConfig | PIIConfig | ExamplesConfig | null;
}

/** NewTaskRequest */
export interface NewTaskRequest {
  /**
   * Name
   * Name of the task.
   * @minLength 1
   */
  name: string;
  /**
   * Is Agentic
   * Whether the task is agentic or not.
   * @default false
   */
  is_agentic?: boolean;
}

/**
 * PIIConfig
 * @example {"allow_list":["arthur.ai","Arthur"],"confidence_threshold":"0.5","disabled_pii_entities":["PERSON","URL"]}
 */
export interface PIIConfig {
  /**
   * Disabled Pii Entities
   * Optional. List of PII entities to disable. Valid values are: CREDIT_CARD,CRYPTO,DATE_TIME,EMAIL_ADDRESS,IBAN_CODE,IP_ADDRESS,NRP,LOCATION,PERSON,PHONE_NUMBER,MEDICAL_LICENSE,URL,US_BANK_NUMBER,US_DRIVER_LICENSE,US_ITIN,US_PASSPORT,US_SSN
   */
  disabled_pii_entities?: string[] | null;
  /**
   * Confidence Threshold
   * Optional. Float (0, 1) indicating the level of tolerable PII to consider the rule passed or failed. Min: 0 (less confident) Max: 1 (very confident). Default: 0
   * @deprecated
   * @default 0
   */
  confidence_threshold?: number | null;
  /**
   * Allow List
   * Optional. List of strings to pass PII validation.
   */
  allow_list?: string[] | null;
}

/** PIIDetailsResponse */
export interface PIIDetailsResponse {
  /** Score */
  score?: boolean | null;
  /** Message */
  message?: string | null;
  /** Pii Entities */
  pii_entities: PIIEntitySpanResponse[];
}

/** PIIEntitySpanResponse */
export interface PIIEntitySpanResponse {
  entity: PIIEntityTypes;
  /**
   * Span
   * The subtext within the input string that was identified as PII.
   */
  span: string;
  /**
   * Confidence
   * Float value representing the confidence score of a given PII identification.
   */
  confidence?: number | null;
}

/** PIIEntityTypes */
export enum PIIEntityTypes {
  CREDIT_CARD = "CREDIT_CARD",
  CRYPTO = "CRYPTO",
  DATE_TIME = "DATE_TIME",
  EMAIL_ADDRESS = "EMAIL_ADDRESS",
  IBAN_CODE = "IBAN_CODE",
  IP_ADDRESS = "IP_ADDRESS",
  NRP = "NRP",
  LOCATION = "LOCATION",
  PERSON = "PERSON",
  PHONE_NUMBER = "PHONE_NUMBER",
  MEDICAL_LICENSE = "MEDICAL_LICENSE",
  URL = "URL",
  US_BANK_NUMBER = "US_BANK_NUMBER",
  US_DRIVER_LICENSE = "US_DRIVER_LICENSE",
  US_ITIN = "US_ITIN",
  US_PASSPORT = "US_PASSPORT",
  US_SSN = "US_SSN",
}

/** Page[List[ConversationBaseResponse]] */
export interface PageListConversationBaseResponse {
  /** Items */
  items: ConversationBaseResponse[][];
  /**
   * Total
   * @min 0
   */
  total: number;
  /**
   * Page
   * @min 1
   */
  page: number;
  /**
   * Size
   * @min 1
   */
  size: number;
  /**
   * Pages
   * @min 0
   */
  pages: number;
}

/** PaginationSortMethod */
export enum PaginationSortMethod {
  Asc = "asc",
  Desc = "desc",
}

/** PasswordResetRequest */
export interface PasswordResetRequest {
  /** Password */
  password: string;
}

/** PromptValidationRequest */
export interface PromptValidationRequest {
  /**
   * Prompt
   * Prompt to be validated by GenAI Engine
   */
  prompt: string;
  /**
   * Conversation Id
   * The unique conversation ID this prompt belongs to. All prompts and responses from this         conversation can later be reconstructed with this ID.
   */
  conversation_id?: string | null;
  /**
   * User Id
   * The user ID this prompt belongs to
   */
  user_id?: string | null;
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
   * Total Pages
   * The total number of pages
   */
  total_pages: number;
  /**
   * Total Count
   * The total number of feedback items matching the query parameters
   */
  total_count: number;
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
  /** Score */
  score?: boolean | null;
  /** Message */
  message?: string | null;
  /**
   * Regex Matches
   * Each string in this list corresponds to a matching span from the input text that matches the configured regex rule.
   * @default []
   */
  regex_matches?: RegexSpanResponse[];
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

/** ResponseValidationRequest */
export interface ResponseValidationRequest {
  /**
   * Response
   * LLM Response to be validated by GenAI Engine
   */
  response: string;
  /**
   * Context
   * Optional data provided as context for the validation.
   */
  context?: string | null;
}

/** RuleResponse */
export interface RuleResponse {
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
  /** Type of Rule */
  type: RuleType;
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
   * Enabled
   * Rule is enabled for the task
   */
  enabled?: boolean | null;
  /** Scope of the rule. The rule can be set at default level or task level. */
  scope: RuleScope;
  /**
   * Created At
   * Time the rule was created in unix milliseconds
   */
  created_at: number;
  /**
   * Updated At
   * Time the rule was updated in unix milliseconds
   */
  updated_at: number;
  /**
   * Config
   * Config of the rule
   */
  config?: KeywordsConfig | RegexConfig | ExamplesConfig | ToxicityConfig | PIIConfig | null;
}

/** RuleResultEnum */
export enum RuleResultEnum {
  Pass = "Pass",
  Fail = "Fail",
  Skipped = "Skipped",
  Unavailable = "Unavailable",
  PartiallyUnavailable = "Partially Unavailable",
  ModelNotAvailable = "Model Not Available",
}

/** RuleScope */
export enum RuleScope {
  Default = "default",
  Task = "task",
}

/** RuleType */
export enum RuleType {
  KeywordRule = "KeywordRule",
  ModelHallucinationRuleV2 = "ModelHallucinationRuleV2",
  ModelSensitiveDataRule = "ModelSensitiveDataRule",
  PIIDataRule = "PIIDataRule",
  PromptInjectionRule = "PromptInjectionRule",
  RegexRule = "RegexRule",
  ToxicityRule = "ToxicityRule",
}

/** SearchRulesRequest */
export interface SearchRulesRequest {
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

/** SearchTasksRequest */
export interface SearchTasksRequest {
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
  /**
   * Is Agentic
   * Filter tasks by agentic status. If not provided, returns both agentic and non-agentic tasks.
   */
  is_agentic?: boolean | null;
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

/** SpanWithMetricsResponse */
export interface SpanWithMetricsResponse {
  /** Id */
  id: string;
  /** Trace Id */
  trace_id: string;
  /** Span Id */
  span_id: string;
  /** Parent Span Id */
  parent_span_id?: string | null;
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
   * End Time
   * @format date-time
   */
  end_time: string;
  /** Task Id */
  task_id?: string | null;
  /**
   * Created At
   * @format date-time
   */
  created_at: string;
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
  /** Raw Data */
  raw_data: Record<string, any>;
  /** System Prompt */
  system_prompt?: string | null;
  /** User Query */
  user_query?: string | null;
  /** Response */
  response?: string | null;
  /** Context */
  context?: Record<string, any>[] | null;
  /**
   * Metric Results
   * List of metric results for this span
   * @default []
   */
  metric_results?: MetricResultResponse[];
}

/** TaskResponse */
export interface TaskResponse {
  /**
   * Id
   *  ID of the task
   */
  id: string;
  /**
   * Name
   * Name of the task
   */
  name: string;
  /**
   * Created At
   * Time the task was created in unix milliseconds
   */
  created_at: number;
  /**
   * Updated At
   * Time the task was created in unix milliseconds
   */
  updated_at: number;
  /**
   * Is Agentic
   * Whether the task is agentic or not
   */
  is_agentic?: boolean | null;
  /**
   * Rules
   * List of all the rules for the task.
   */
  rules: RuleResponse[];
  /**
   * Metrics
   * List of all the metrics for the task.
   */
  metrics?: MetricResponse[] | null;
}

/** TokenUsageCount */
export interface TokenUsageCount {
  /**
   * Inference
   * Number of inference tokens sent to Arthur.
   */
  inference: number;
  /**
   * Eval Prompt
   * Number of Prompt tokens incurred by Arthur rules.
   */
  eval_prompt: number;
  /**
   * Eval Completion
   * Number of Completion tokens incurred by Arthur rules.
   */
  eval_completion: number;
  /**
   * User Input
   * Number of user input tokens sent to Arthur. This field is deprecated and will be removed in the future. Use inference instead.
   * @deprecated
   */
  user_input: number;
  /**
   * Prompt
   * Number of Prompt tokens incurred by Arthur rules. This field is deprecated and will be removed in the future. Use eval_prompt instead.
   * @deprecated
   */
  prompt: number;
  /**
   * Completion
   * Number of Completion tokens incurred by Arthur rules. This field is deprecated and will be removed in the future. Use eval_completion instead.
   * @deprecated
   */
  completion: number;
}

/** TokenUsageResponse */
export interface TokenUsageResponse {
  /** Rule Type */
  rule_type?: string | null;
  /** Task Id */
  task_id?: string | null;
  count: TokenUsageCount;
}

/** TokenUsageScope */
export enum TokenUsageScope {
  RuleType = "rule_type",
  Task = "task",
}

/** ToolClassEnum */
export enum ToolClassEnum {
  Value0 = 0,
  Value1 = 1,
  Value2 = 2,
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
  /** Score */
  score?: boolean | null;
  /** Message */
  message?: string | null;
  /** Toxicity Score */
  toxicity_score?: number | null;
  toxicity_violation_type: ToxicityViolationType;
}

/** ToxicityViolationType */
export enum ToxicityViolationType {
  Benign = "benign",
  HarmfulRequest = "harmful_request",
  ToxicContent = "toxic_content",
  Profanity = "profanity",
  Unknown = "unknown",
}

/**
 * TraceResponse
 * Response model for a single trace containing nested spans
 */
export interface TraceResponse {
  /**
   * Trace Id
   * ID of the trace
   */
  trace_id: string;
  /**
   * Start Time
   * Start time of the earliest span in this trace
   * @format date-time
   */
  start_time: string;
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
}

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

/** UserPermissionAction */
export enum UserPermissionAction {
  Create = "create",
  Read = "read",
}

/** UserPermissionResource */
export enum UserPermissionResource {
  Prompts = "prompts",
  Responses = "responses",
  Rules = "rules",
  Tasks = "tasks",
}

/** UserResponse */
export interface UserResponse {
  /** Id */
  id: string;
  /** Email */
  email: string;
  /** First Name */
  first_name?: string | null;
  /** Last Name */
  last_name?: string | null;
  /** Roles */
  roles: AuthUserRole[];
}

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
 * @version 2.1.79
 */
export class Api<SecurityDataType extends unknown> extends HttpClient<SecurityDataType> {
  api = {
    /**
     * @description Get token usage.
     *
     * @tags Usage
     * @name GetTokenUsageApiV2UsageTokensGet
     * @summary Get Token Usage
     * @request GET:/api/v2/usage/tokens
     * @secure
     */
    getTokenUsageApiV2UsageTokensGet: (
      query?: {
        /**
         * Start Time
         * Inclusive start date in ISO8601 string format. Defaults to the beginning of the current day if not provided.
         * @format date-time
         */
        start_time?: string;
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
      },
      params: RequestParams = {},
    ) =>
      this.request<TokenUsageResponse[], HTTPValidationError>({
        path: `/api/v2/usage/tokens`,
        method: "GET",
        query: query,
        secure: true,
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
      this.request<InferenceFeedbackResponse, HTTPValidationError>({
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
    queryFeedbackApiV2FeedbackQueryGet: (
      query?: {
        /**
         * Start Time
         * Inclusive start date in ISO8601 string format
         */
        start_time?: string | null;
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
         * Inference Id
         * Inference ID to filter on
         */
        inference_id?: string | string[] | null;
        /**
         * Target
         * Target of the feedback. Must be one of ['context', 'response_results', 'prompt_results']
         */
        target?: string | string[] | null;
        /**
         * Score
         * Score of the feedback. Must be an integer.
         */
        score?: number | number[] | null;
        /**
         * Feedback User Id
         * User ID of the user giving feedback to filter on (query will perform fuzzy search)
         */
        feedback_user_id?: string | null;
        /**
         * Conversation Id
         * Conversation ID to filter on
         */
        conversation_id?: string | string[] | null;
        /**
         * Task Id
         * Task ID to filter on
         */
        task_id?: string | string[] | null;
        /**
         * Inference User Id
         * User ID of the user who created the inferences to filter on (query will perform fuzzy search)
         */
        inference_user_id?: string | null;
        /**
         * Sort the results (asc/desc)
         * @default "desc"
         */
        sort?: PaginationSortMethod;
        /**
         * Page Size
         * Page size. Default is 10. Must be greater than 0 and less than 5000.
         * @default 10
         */
        page_size?: number;
        /**
         * Page
         * Page number
         * @default 0
         */
        page?: number;
      },
      params: RequestParams = {},
    ) =>
      this.request<QueryFeedbackResponse, HTTPValidationError>({
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
      query?: {
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
         * Conversation Id
         * Conversation ID to filter on.
         */
        conversation_id?: string;
        /**
         * Inference Id
         * Inference ID to filter on.
         */
        inference_id?: string;
        /**
         * User Id
         * User ID to filter on.
         */
        user_id?: string;
        /**
         * Start Time
         * Inclusive start date in ISO8601 string format.
         * @format date-time
         */
        start_time?: string;
        /**
         * End Time
         * Exclusive end date in ISO8601 string format.
         * @format date-time
         */
        end_time?: string;
        /**
         * Rule Types
         * List of RuleType to query for. Any inference that ran any rule in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_statuses, will return inferences with rules in the intersection of rule_types and rule_statuses.
         * @default []
         */
        rule_types?: RuleType[];
        /**
         * Rule Statuses
         * List of RuleResultEnum to query for. Any inference with any rule status in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_types, will return inferences with rules in the intersection of rule_statuses and rule_types.
         * @default []
         */
        rule_statuses?: RuleResultEnum[];
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
         * Include Count
         * Whether to include the total count of matching inferences. Set to False to improve query performance for large datasets. Count will be returned as -1 if set to False.
         * @default true
         */
        include_count?: boolean;
        /**
         * Sort the results (asc/desc)
         * @default "desc"
         */
        sort?: PaginationSortMethod;
        /**
         * Page Size
         * Page size. Default is 10. Must be greater than 0 and less than 5000.
         * @default 10
         */
        page_size?: number;
        /**
         * Page
         * Page number
         * @default 0
         */
        page?: number;
      },
      params: RequestParams = {},
    ) =>
      this.request<QueryInferencesResponse, HTTPValidationError>({
        path: `/api/v2/inferences/query`,
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
      this.request<RuleResponse[], any>({
        path: `/api/v2/default_rules`,
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
      this.request<RuleResponse, HTTPValidationError>({
        path: `/api/v2/default_rules`,
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
      this.request<any, HTTPValidationError>({
        path: `/api/v2/default_rules/${ruleId}`,
        method: "DELETE",
        secure: true,
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
      data: SearchRulesRequest,
      query?: {
        /**
         * Sort the results (asc/desc)
         * @default "desc"
         */
        sort?: PaginationSortMethod;
        /**
         * Page Size
         * Page size. Default is 10. Must be greater than 0 and less than 5000.
         * @default 10
         */
        page_size?: number;
        /**
         * Page
         * Page number
         * @default 0
         */
        page?: number;
      },
      params: RequestParams = {},
    ) =>
      this.request<SearchRulesResponse, HTTPValidationError>({
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
      this.request<TaskResponse[], any>({
        path: `/api/v2/tasks`,
        method: "GET",
        secure: true,
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
      this.request<TaskResponse, HTTPValidationError>({
        path: `/api/v2/tasks`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
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
      this.request<any, HTTPValidationError>({
        path: `/api/v2/tasks/${taskId}`,
        method: "DELETE",
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
      this.request<TaskResponse, HTTPValidationError>({
        path: `/api/v2/tasks/${taskId}`,
        method: "GET",
        secure: true,
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
      this.request<any, any>({
        path: `/api/v2/task`,
        method: "POST",
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
      data: SearchTasksRequest,
      query?: {
        /**
         * Sort the results (asc/desc)
         * @default "desc"
         */
        sort?: PaginationSortMethod;
        /**
         * Page Size
         * Page size. Default is 10. Must be greater than 0 and less than 5000.
         * @default 10
         */
        page_size?: number;
        /**
         * Page
         * Page number
         * @default 0
         */
        page?: number;
      },
      params: RequestParams = {},
    ) =>
      this.request<SearchTasksResponse, HTTPValidationError>({
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
     * @description Create a rule to be applied only to this task. Available rule types are KeywordRule, ModelHallucinationRuleV2, ModelSensitiveDataRule, PIIDataRule, PromptInjectionRule, RegexRule, ToxicityRule.Note: The rules are cached by the validation endpoints for 60 seconds.
     *
     * @tags Tasks
     * @name CreateTaskRuleApiV2TasksTaskIdRulesPost
     * @summary Create Task Rule
     * @request POST:/api/v2/tasks/{task_id}/rules
     * @secure
     */
    createTaskRuleApiV2TasksTaskIdRulesPost: (taskId: string, data: NewRuleRequest, params: RequestParams = {}) =>
      this.request<RuleResponse, HTTPValidationError>({
        path: `/api/v2/tasks/${taskId}/rules`,
        method: "POST",
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
      this.request<TaskResponse, HTTPValidationError>({
        path: `/api/v2/tasks/${taskId}/rules/${ruleId}`,
        method: "PATCH",
        body: data,
        secure: true,
        type: ContentType.Json,
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
      this.request<any, HTTPValidationError>({
        path: `/api/v2/tasks/${taskId}/rules/${ruleId}`,
        method: "DELETE",
        secure: true,
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
      this.request<any, HTTPValidationError>({
        path: `/api/v2/tasks/${taskId}/metrics`,
        method: "POST",
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
    updateTaskMetricApiV2TasksTaskIdMetricsMetricIdPatch: (
      taskId: string,
      metricId: string,
      data: UpdateMetricRequest,
      params: RequestParams = {},
    ) =>
      this.request<any, HTTPValidationError>({
        path: `/api/v2/tasks/${taskId}/metrics/${metricId}`,
        method: "PATCH",
        body: data,
        secure: true,
        type: ContentType.Json,
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
      this.request<any, HTTPValidationError>({
        path: `/api/v2/tasks/${taskId}/metrics/${metricId}`,
        method: "DELETE",
        secure: true,
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
      this.request<ValidationResult, HTTPValidationError>({
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
    defaultValidateResponseApiV2ValidateResponseInferenceIdPost: (
      inferenceId: string,
      data: ResponseValidationRequest,
      params: RequestParams = {},
    ) =>
      this.request<ValidationResult, HTTPValidationError>({
        path: `/api/v2/validate_response/${inferenceId}`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
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
      this.request<ValidationResult, HTTPError | HTTPValidationError>({
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
      this.request<ValidationResult, HTTPError | HTTPValidationError>({
        path: `/api/v2/tasks/${taskId}/validate_response/${inferenceId}`,
        method: "POST",
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
      data: BodyUploadEmbeddingsFileApiChatFilesPost,
      query?: {
        /**
         * Is Global
         * @default false
         */
        is_global?: boolean;
      },
      params: RequestParams = {},
    ) =>
      this.request<FileUploadResult, HTTPValidationError>({
        path: `/api/chat/files`,
        method: "POST",
        query: query,
        body: data,
        type: ContentType.FormData,
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
      this.request<ExternalDocument[], any>({
        path: `/api/chat/files`,
        method: "GET",
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
      this.request<any, HTTPValidationError>({
        path: `/api/chat/files/${fileId}`,
        method: "DELETE",
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
      this.request<ChatResponse, HTTPValidationError>({
        path: `/api/chat/`,
        method: "POST",
        body: data,
        type: ContentType.Json,
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
      this.request<ChatDocumentContext[], HTTPValidationError>({
        path: `/api/chat/context/${inferenceId}`,
        method: "GET",
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
      this.request<any, HTTPValidationError>({
        path: `/api/chat/feedback/${inferenceId}`,
        method: "POST",
        body: data,
        type: ContentType.Json,
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
      query?: {
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
      },
      params: RequestParams = {},
    ) =>
      this.request<PageListConversationBaseResponse, HTTPValidationError>({
        path: `/api/chat/conversations`,
        method: "GET",
        query: query,
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
      this.request<ChatDefaultTaskResponse, any>({
        path: `/api/chat/default_task`,
        method: "GET",
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
      this.request<ChatDefaultTaskResponse, HTTPValidationError>({
        path: `/api/chat/default_task`,
        method: "PUT",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),
  };
  auth = {
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
      this.request<ApiKeyResponse[], any>({
        path: `/auth/api_keys/`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

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
      this.request<ApiKeyResponse, HTTPValidationError>({
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
     * @name GetApiKeyAuthApiKeysApiKeyIdGet
     * @summary Get Api Key
     * @request GET:/auth/api_keys/{api_key_id}
     * @secure
     */
    getApiKeyAuthApiKeysApiKeyIdGet: (apiKeyId: string, params: RequestParams = {}) =>
      this.request<ApiKeyResponse, HTTPValidationError>({
        path: `/auth/api_keys/${apiKeyId}`,
        method: "GET",
        secure: true,
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
      this.request<ApiKeyResponse, HTTPValidationError>({
        path: `/auth/api_keys/deactivate/${apiKeyId}`,
        method: "DELETE",
        secure: true,
        format: "json",
        ...params,
      }),
  };
  v1 = {
    /**
     * @description Receiver for OpenInference trace standard.
     *
     * @tags Traces
     * @name ReceiveTracesV1TracesPost
     * @summary Receive Traces
     * @request POST:/v1/traces
     * @secure
     */
    receiveTracesV1TracesPost: (data: File, params: RequestParams = {}) =>
      this.request<any, HTTPValidationError>({
        path: `/v1/traces`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
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
     * @secure
     */
    querySpansV1TracesQueryGet: (
      query: {
        /**
         * Sort the results (asc/desc)
         * @default "desc"
         */
        sort?: PaginationSortMethod;
        /**
         * Page Size
         * Page size. Default is 10. Must be greater than 0 and less than 5000.
         * @default 10
         */
        page_size?: number;
        /**
         * Page
         * Page number
         * @default 0
         */
        page?: number;
        /**
         * Task Ids
         * Task IDs to filter on. At least one is required.
         * @minItems 1
         */
        task_ids: string[];
        /**
         * Trace Ids
         * Trace IDs to filter on. Optional.
         */
        trace_ids?: string[];
        /**
         * Start Time
         * Inclusive start date in ISO8601 string format. Use local time (not UTC).
         * @format date-time
         */
        start_time?: string;
        /**
         * End Time
         * Exclusive end date in ISO8601 string format. Use local time (not UTC).
         * @format date-time
         */
        end_time?: string;
        /**
         * Tool Name
         * Return only results with this tool name.
         */
        tool_name?: string;
        /**
         * Span Types
         * Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
         */
        span_types?: string[];
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
      },
      params: RequestParams = {},
    ) =>
      this.request<QueryTracesWithMetricsResponse, HTTPValidationError>({
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
     * @secure
     */
    querySpansWithMetricsV1TracesMetricsGet: (
      query: {
        /**
         * Sort the results (asc/desc)
         * @default "desc"
         */
        sort?: PaginationSortMethod;
        /**
         * Page Size
         * Page size. Default is 10. Must be greater than 0 and less than 5000.
         * @default 10
         */
        page_size?: number;
        /**
         * Page
         * Page number
         * @default 0
         */
        page?: number;
        /**
         * Task Ids
         * Task IDs to filter on. At least one is required.
         * @minItems 1
         */
        task_ids: string[];
        /**
         * Trace Ids
         * Trace IDs to filter on. Optional.
         */
        trace_ids?: string[];
        /**
         * Start Time
         * Inclusive start date in ISO8601 string format. Use local time (not UTC).
         * @format date-time
         */
        start_time?: string;
        /**
         * End Time
         * Exclusive end date in ISO8601 string format. Use local time (not UTC).
         * @format date-time
         */
        end_time?: string;
        /**
         * Tool Name
         * Return only results with this tool name.
         */
        tool_name?: string;
        /**
         * Span Types
         * Span types to filter on. Optional. Valid values: AGENT, CHAIN, EMBEDDING, EVALUATOR, GUARDRAIL, LLM, RERANKER, RETRIEVER, TOOL, UNKNOWN
         */
        span_types?: string[];
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
      },
      params: RequestParams = {},
    ) =>
      this.request<QueryTracesWithMetricsResponse, HTTPValidationError>({
        path: `/v1/traces/metrics/`,
        method: "GET",
        query: query,
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
     * @secure
     */
    querySpansByTypeV1SpansQueryGet: (
      query: {
        /**
         * Task Ids
         * Task IDs to filter on. At least one is required.
         * @minItems 1
         */
        task_ids: string[];
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
         * End Time
         * Exclusive end date in ISO8601 string format. Use local time (not UTC).
         * @format date-time
         */
        end_time?: string;
        /**
         * Sort the results (asc/desc)
         * @default "desc"
         */
        sort?: PaginationSortMethod;
        /**
         * Page Size
         * Page size. Default is 10. Must be greater than 0 and less than 5000.
         * @default 10
         */
        page_size?: number;
        /**
         * Page
         * Page number
         * @default 0
         */
        page?: number;
      },
      params: RequestParams = {},
    ) =>
      this.request<QuerySpansResponse, void | HTTPValidationError>({
        path: `/v1/spans/query`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * @description Compute metrics for a single span. Validates that the span is an LLM span.
     *
     * @tags Spans
     * @name ComputeSpanMetricsV1SpanSpanIdMetricsGet
     * @summary Compute Metrics for Span
     * @request GET:/v1/span/{span_id}/metrics
     * @secure
     */
    computeSpanMetricsV1SpanSpanIdMetricsGet: (spanId: string, params: RequestParams = {}) =>
      this.request<SpanWithMetricsResponse, HTTPValidationError>({
        path: `/v1/span/${spanId}/metrics`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),
  };
  users = {
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
      this.request<any, HTTPValidationError>({
        path: `/users`,
        method: "POST",
        body: data,
        secure: true,
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
    searchUsersUsersGet: (
      query?: {
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
        /**
         * Page Size
         * Page size. Default is 10. Must be greater than 0 and less than 5000.
         * @default 10
         */
        page_size?: number;
        /**
         * Page
         * Page number
         * @default 0
         */
        page?: number;
      },
      params: RequestParams = {},
    ) =>
      this.request<UserResponse[], HTTPValidationError>({
        path: `/users`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

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
      query?: {
        /** Action to check permissions of. */
        action?: UserPermissionAction;
        /** Resource to check permissions of. */
        resource?: UserPermissionResource;
      },
      params: RequestParams = {},
    ) =>
      this.request<any, HTTPValidationError>({
        path: `/users/permissions/check`,
        method: "GET",
        query: query,
        secure: true,
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
      this.request<any, HTTPValidationError>({
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
      this.request<any, HTTPValidationError>({
        path: `/users/${userId}/reset_password`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),
  };
}
