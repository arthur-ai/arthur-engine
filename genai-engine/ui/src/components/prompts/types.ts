const promptClassificationEnum = {
  EVAL: "eval",
  DEFAULT: "default",
};

const messageRoleEnum = {
  SYSTEM: "system",
  USER: "user",
  AI: "ai",
  TOOL: "tool",
};

const providerEnum = {
  OPENAI: "openai",
  GOOGLE: "google",
  AZURE: "azure",
};

type PromptTool = {
  id: string;
  type: "function";
  function: {
    name: string;
    description: string;
    parameters: {
      type: "object";
      properties: Record<string, {
        type: string;
        description?: string;
      }>;
      required: string[];
    };
  };
};

const reasoningEffortEnum = {
  NONE: "none",
  MINIMAL: "minimal",
  LOW: "low",
  MEDIUM: "medium",
  HIGH: "high",
  DEFAULT: "default",
};

type PromptAction =
  | { type: "addPrompt" }
  | { type: "deletePrompt"; payload: { id: string } }
  | { type: "duplicatePrompt"; payload: { id: string } }
  | { type: "hydratePrompt"; payload: { promptData: Partial<PromptType> } }
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
      type: "updateModelParameters";
      payload: { promptId: string; modelParameters: ModelParametersType };
    }
  | { type: "addTool"; 
      payload: { parentId: string } 
    }
  | { type: "deleteTool"; 
      payload: { parentId: string; toolId: string } 
    }
  | {
      type: "updateTool";
      payload: { parentId: string; toolId: string; tool: Partial<PromptTool> };
    }
  | { type: "expandTools"; 
      payload: { parentId: string } 
    }
  | {
      type: "updateToolChoice";
      payload: { promptId: string; toolChoice: string };
    };

// The id is used in the FE, but may not need to be stored in BE.
type MessageType = {
  id: string;
  role: string; // messageRoleEnum
  content: string;
  disabled: boolean;
};

type ModelParametersType = {
  temperature?: number | null; // 0 < temperature <= 1 (or 2?)
  top_p?: number | null; // 0 < top_p <= 1
  timeout?: number | null; // In milliseconds
  stream?: boolean; // Whether to stream the response, defautl false
  stream_options?: object | null; // Stream options TODO
  max_tokens?: number | null; // Length limit of generated response > 0
  max_completion_tokens?: number | null; // ??
  frequency_penalty?: number; // -2 < frequency_penalty <= 2
  presence_penalty?: number; // -2 < presence_penalty <= 2, default 0
  stop?: string | null; // Stop sequence
  seed?: number | null; // Random seed
  reasoning_effort?: typeof reasoningEffortEnum | "";
  // The following do not appear in the UI
  logprobs?: boolean | null; //Whether to return log probabilities of the output tokens or not. If true, returns the log probabilities of each output token returned in the content of message.
  top_logprobs?: number | null; //An integer between 0 and 5 specifying the number of most likely tokens to return at each token position, each with an associated log probability. logprobs must be set to true if this parameter is used.
  logit_bias?: object | null; //Logit bias TODO
  thinking?: object | null; //Thinking TODO AnthropicThinkingParam
};

type PromptType = {
  id: string; // name + timestamp, probably
  classification: string;
  name: string;
  modelName: string;
  provider: string;
  messages: MessageType[];
  modelParameters: ModelParametersType;
  outputField: string;
  tools: PromptTool[];
  toolChoice: string; // "auto", "none", "required", or tool ID
  // responseFormat: ?; // TODO
  // tags: Array<string>; // TODO
};

interface PromptPlaygroundState {
  keywords: Map<string, string>;
  keywordTracker: Map<string, Array<string>>;
  prompts: PromptType[];
}

interface MessageComponentProps {
  id: string;
  parentId: string;
  role?: string;
  defaultContent?: string;
  content: string | "";
  dispatch: (action: PromptAction) => void;
}

interface PromptComponentProps {
  prompt: PromptType;
  dispatch: (action: PromptAction) => void;
}

export {
  messageRoleEnum,
  MessageComponentProps,
  MessageType,
  ModelParametersType,
  providerEnum,
  PromptType,
  PromptComponentProps,
  PromptPlaygroundState,
  PromptAction,
  promptClassificationEnum,
  reasoningEffortEnum,
  PromptTool,
};
