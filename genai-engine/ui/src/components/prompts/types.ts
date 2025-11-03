import {
  ReasoningEffortEnum,
  AgenticPromptMessageInput,
  MessageRole,
  LogitBiasItem,
  StreamOptions,
  AnthropicThinkingParam,
  ToolChoiceEnum,
  LLMToolInput,
  ToolChoice,
  ModelProvider,
  AgenticPromptMetadataResponse,
  Api,
  AgenticPromptRunResponse,
  OpenAIMessageItem,
} from "@/lib/api-client/api-client";

// Frontend tool type that extends LLMToolInput with an id for UI purposes
type FrontendTool = LLMToolInput & { id: string };

const promptClassificationEnum = {
  EVAL: "eval",
  DEFAULT: "default",
};

type PromptAction =
  | { type: "addPrompt" }
  | { type: "deletePrompt"; payload: { id: string } }
  | { type: "duplicatePrompt"; payload: { id: string } }
  | { type: "hydratePrompt"; payload: { promptData: Partial<PromptType> } }
  | { type: "updatePromptName"; payload: { promptId: string; name: string } }
  | {
      type: "updatePromptProvider";
      payload: { promptId: string; modelProvider: ModelProvider | "" };
    }
  | {
      type: "updatePromptModelName";
      payload: { promptId: string; modelName: string };
    }
  | {
      type: "updatePrompt";
      payload: { promptId: string; prompt: Partial<PromptType> };
    }
  | {
      type: "updateBackendPrompts";
      payload: { prompts: AgenticPromptMetadataResponse[] };
    }
  | {
      type: "updateProviders";
      payload: { providers: ModelProvider[] };
    }
  | {
      type: "updateAvailableModels";
      payload: { availableModels: Map<ModelProvider, string[]> };
    }
  | { type: "addMessage"; payload: { parentId: string } }
  | { type: "deleteMessage"; payload: { parentId: string; id: string } }
  | { type: "duplicateMessage"; payload: { parentId: string; id: string } }
  | {
      type: "hydrateMessage";
      payload: { parentId: string; messageData: Partial<MessageType> };
    }
  | {
      type: "editMessage";
      payload: { parentId: string; id: string; content: string };
    }
  | {
      type: "changeMessageRole";
      payload: { parentId: string; id: string; role: string };
    }
  | {
      type: "updateKeywords";
      payload: { id: string; messageKeywords: string[] };
    }
  | {
      type: "updateKeywordValue";
      payload: { keyword: string; value: string };
    }
  | {
      type: "runPrompt";
      payload: { promptId: string };
    }
  | {
      type: "updateModelParameters";
      payload: { promptId: string; modelParameters: ModelParametersType };
    }
  | {
      type: "updateResponseFormat";
      payload: { promptId: string; responseFormat: string | undefined };
    }
  | { type: "addTool"; payload: { promptId: string } }
  | { type: "deleteTool"; payload: { promptId: string; toolId: string } }
  | {
      type: "updateTool";
      payload: {
        parentId: string;
        toolId: string;
        tool: Partial<FrontendTool>;
      };
    }
  | { type: "expandTools"; payload: { parentId: string } }
  | {
      type: "updateToolChoice";
      payload: { promptId: string; toolChoice: string };
    }
  | {
      type: "moveMessage";
      payload: { parentId: string; fromIndex: number; toIndex: number };
    };

// The id is used in the FE, but may not need to be stored in BE.
interface MessageType extends AgenticPromptMessageInput {
  id: string;
  disabled: boolean;
}

type ModelParametersType = {
  temperature?: number | null; // 0 < temperature <= 1 (or 2?)
  top_p?: number | null; // 0 < top_p <= 1
  timeout?: number | null; // In milliseconds
  stream?: boolean; // Whether to stream the response, defautl false
  stream_options?: StreamOptions | null;
  max_tokens?: number | null; // Length limit of generated response > 0
  max_completion_tokens?: number | null; // ??
  frequency_penalty?: number | null; // -2 < frequency_penalty <= 2
  presence_penalty?: number | null; // -2 < presence_penalty <= 2, default 0
  stop?: string | null; // Stop sequence
  seed?: number | null; // Random seed
  reasoning_effort?: ReasoningEffortEnum | null;
  // The following do not appear in the UI
  logprobs?: boolean | null; //Whether to return log probabilities of the output tokens or not. If true, returns the log probabilities of each output token returned in the content of message.
  top_logprobs?: number | null; //An integer between 0 and 5 specifying the number of most likely tokens to return at each token position, each with an associated log probability. logprobs must be set to true if this parameter is used.
  logit_bias?: LogitBiasItem[] | null;
  thinking?: AnthropicThinkingParam | null;
};

type PromptType = {
  id: string; // name + timestamp, probably
  classification: string;
  name: string;
  created_at: string | undefined;
  modelName: string;
  modelProvider: ModelProvider | "";
  messages: MessageType[];
  modelParameters: ModelParametersType;
  runResponse: AgenticPromptRunResponse | null; // The response from the last run
  responseFormat: string | undefined; //LLMResponseSchemaInput
  tools: FrontendTool[]; //LLMToolOutput
  toolChoice?: ToolChoiceEnum | ToolChoice;
  // tags: Array<string>; // TODO
  running?: boolean; // Whether the prompt is running
};

interface PromptPlaygroundState {
  keywords: Map<string, string>;
  keywordTracker: Map<string, Array<string>>;
  prompts: PromptType[];
  backendPrompts: AgenticPromptMetadataResponse[]; // prompt metadata
  enabledProviders: ModelProvider[];
  availableModels: Map<ModelProvider, string[]>; // provider -> models
}

interface MessageComponentProps {
  id: string;
  parentId: string;
  role?: string;
  defaultContent?: string | OpenAIMessageItem[];
  content: string | OpenAIMessageItem[] | "";
  dragHandleProps?: Record<string, unknown>;
}

interface PromptComponentProps {
  prompt: PromptType;
}

interface OutputFieldProps {
  promptId: string;
  running: boolean;
  runResponse: AgenticPromptRunResponse | null;
  responseFormat: string | undefined;
}

interface SavePromptDialogProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  prompt: PromptType;
  initialName?: string;
  onSaveSuccess?: () => void;
  onSaveError?: (error: string) => void;
}

interface VersionSubmenuProps {
  open: boolean;
  promptName: string;
  taskId: string;
  apiClient: Api<unknown>;
  onVersionSelect: (version: number) => void;
  onClose: () => void;
  anchorEl: HTMLElement | null;
}

const MESSAGE_ROLE_OPTIONS: MessageRole[] = ["system", "user", "assistant", "tool"];

export {
  MESSAGE_ROLE_OPTIONS,
  MessageComponentProps,
  MessageType,
  ModelParametersType,
  PromptType,
  PromptComponentProps,
  PromptPlaygroundState,
  PromptAction,
  promptClassificationEnum,
  OutputFieldProps,
  SavePromptDialogProps,
  FrontendTool,
  VersionSubmenuProps,
};
