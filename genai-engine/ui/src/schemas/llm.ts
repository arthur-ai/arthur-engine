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

export const ToolCall = z.object({
  tool_call: z.object({
    id: z.string().optional(),
    function: z.object({
      name: z.string(),
      arguments: z.string().optional(),
    }),
  }),
});

export const Message = z.discriminatedUnion("role", [
  z.object({
    role: z.literal("system"),
    content: z.string(),
  }),
  z.object({
    role: z.literal("user"),
    content: z.string(),
  }),
  z.object({
    role: z.literal("assistant"),
    content: z.string().optional(),
    tool_calls: z.array(ToolCall).optional(),
  }),
  z.object({
    role: z.literal("tool"),
    content: z.string().optional(),
    tool_call_id: z.string().optional(),
  }),
]);

export const Tool = z
  .object({
    name: z.string(),
    description: z.string(),
    input_schema: z.record(z.string(), z.any()),
  })
  .brand("Tool");

export const LiteLLMTool = z
  .object({
    type: z.literal("function"),
    function: z.object({
      name: z.string(),
      description: z.string(),
      parameters: z.record(z.string(), z.any()),
    }),
  })
  .brand("LiteLLMTool");

export const LLMToolsField = z.array(
  z.object({
    tool: z.object({
      json_schema: z
        .string()
        .transform((val, ctx) => {
          try {
            return JSON.parse(val);
          } catch {
            ctx.addIssue({
              code: "custom",
              message: "Invalid JSON schema",
            });
            return z.NEVER;
          }
        })
        .pipe(z.union([Tool, LiteLLMTool])),
    }),
  })
);

export type Message = z.infer<typeof Message>;
export type ToolCall = z.infer<typeof ToolCall>;

export type TextContent = z.infer<typeof TextContent>;
export type ToolCallContent = z.infer<typeof ToolCallContent>;
export type ToolResultContent = z.infer<typeof ToolResultContent>;

export type LLMOutputMessage = z.infer<typeof LLMOutputMessage>;

export type Tool = z.infer<typeof Tool>;
export type LiteLLMTool = z.infer<typeof LiteLLMTool>;
export type LLMToolsField = z.infer<typeof LLMToolsField>;
