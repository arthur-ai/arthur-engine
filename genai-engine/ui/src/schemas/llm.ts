import { z } from "zod";

export const TextContent = z.object({
  type: z.literal("text"),
  text: z.string(),
});

export const ToolCallContent = z.object({
  type: z.literal("tool-call"),
  toolCallId: z.string(),
  toolName: z.string(),
  input: z.record(z.string(), z.any()),
});

export const ToolResultContent = z.object({
  type: z.literal("tool-result"),
  toolCallId: z.string(),
  toolName: z.string(),
  output: z.any(),
});

export const LLMOutputMessage = z.object({
  files: z.array(z.any()),
  text: z.string(),
  sources: z.array(z.any()),
  reasoning: z.array(z.any()),
  object: z.any(),
});

export const MessageContent = z
  .discriminatedUnion("type", [TextContent, ToolCallContent, ToolResultContent])
  .catch({ type: "text", text: "-" });

export const Message = z.discriminatedUnion("role", [
  z.object({
    role: z.literal("system"),
    content: z.array(MessageContent),
  }),
  z.object({
    role: z.literal("user"),
    content: z.array(MessageContent),
  }),
  z.object({
    role: z.literal("assistant"),
    content: z.array(MessageContent),
  }),
  z.object({
    role: z.literal("tool"),
    content: z.array(MessageContent),
  }),
]);

export type Message = z.infer<typeof Message>;

export type MessageContent = z.infer<typeof MessageContent>;

export type TextContent = z.infer<typeof TextContent>;
export type ToolCallContent = z.infer<typeof ToolCallContent>;
export type ToolResultContent = z.infer<typeof ToolResultContent>;

export type LLMOutputMessage = z.infer<typeof LLMOutputMessage>;
