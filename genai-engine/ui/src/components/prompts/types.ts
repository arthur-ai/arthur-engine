const messageTypeEnum = {
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

// The id is used in the FE, but may not need to be stored in BE.
type MessageType = {
  id: string;
  type: string; // messageTypeEnum
  content: string;
};

interface MessageComponentProps {
  id: string;
  type?: string;
  defaultContent?: string;
  onTypeChange: (id: string, type: string) => void;
  onContentChange: (id: string, content: string) => void;
  onDuplicate: (id: string) => void;
  onDelete: (id: string) => void;
}

export { messageTypeEnum, MessageComponentProps, MessageType, providerEnum };
