import { PromptType } from "../types";

import { ToolChoice, ToolChoiceEnum } from "@/lib/api-client/api-client";

/**
 * Gets the display value for a toolChoice for UI purposes.
 * Returns the string value for ToolChoiceEnum or the tool ID for ToolChoice objects.
 * @param toolChoice - The toolChoice value
 * @param tools - Array of tools to lookup tool function names
 * @returns String value for UI display ("auto", "none", "required", or tool ID)
 */
export const getToolChoiceDisplayValue = (toolChoice: ToolChoiceEnum | ToolChoice | undefined, tools: PromptType["tools"]): string => {
  if (!toolChoice) {
    return "auto";
  }

  // If it's a ToolChoiceEnum string, return as-is
  if (typeof toolChoice === "string") {
    return toolChoice;
  }

  // If it's a ToolChoice object, find the tool by function name and return its ID
  if (typeof toolChoice === "object" && "function" in toolChoice && toolChoice.function?.name) {
    const tool = tools.find((t) => t.function.name === toolChoice.function?.name);
    if (tool) {
      return tool.id;
    }
    // If tool not found, return "auto" as fallback
    return "auto";
  }

  return "auto";
};

export default getToolChoiceDisplayValue;
