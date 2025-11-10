import { PromptType } from "../types";

import { ToolChoice } from "@/lib/api-client/api-client";
import { ToolChoiceEnum } from "@/lib/api-client/api-client";

/**
 * Converts a toolChoice value from frontend format to backend format.
 * Handles conversion of tool ID strings to ToolChoice objects.
 * @param toolChoice - The toolChoice value from prompt (can be ToolChoiceEnum, ToolChoice, tool ID string, or undefined)
 * @param tools - Array of tools to lookup tool IDs from
 * @returns ToolChoiceEnum, ToolChoice object, or null for backend API
 */
const convertToolChoiceForBackend = (
  toolChoice: ToolChoiceEnum | ToolChoice | string | undefined,
  tools: PromptType["tools"]
): ToolChoiceEnum | ToolChoice | null => {
  if (!toolChoice) {
    return null;
  }

  // If it's already a ToolChoiceEnum ("auto", "none", "required"), return as-is
  if (toolChoice === "auto" || toolChoice === "none" || toolChoice === "required") {
    return toolChoice as ToolChoiceEnum;
  }

  // If it's already a ToolChoice object, return as-is
  if (typeof toolChoice === "object" && "function" in toolChoice) {
    return toolChoice as ToolChoice;
  }

  // If it's a string (likely a tool ID), find the tool and convert to ToolChoice object
  if (typeof toolChoice === "string") {
    const tool = tools.find((t) => t.id === toolChoice);
    if (tool) {
      return {
        function: {
          name: tool.function.name,
        },
        type: "function",
      } as ToolChoice;
    }
    // If tool not found, return null
    return null;
  }

  return null;
};

export default convertToolChoiceForBackend;
