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
    };

// The id is used in the FE, but may not need to be stored in BE.
type MessageType = {
  id: string;
  role: string; // messageRoleEnum
  content: string;
  disabled: boolean;
};

type PromptType = {
  id: string; // name + timestamp, probably
  classification: string;
  name: string;
  provider: string;
  messages: MessageType[];
  outputField: string;
};

interface PromptPlaygroundState {
  keywords: Set<string>;
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
  providerEnum,
  PromptType,
  PromptComponentProps,
  PromptPlaygroundState,
  PromptAction,
  promptClassificationEnum,
};
