import { openai } from "@ai-sdk/openai";
import { Agent } from "@mastra/core/agent";
import { websearchTool, githubSearchTool } from "@/mastra/tools";
import { z } from "zod";

export const AgentState = z.object({
  supportHistory: z.array(z.string()).default([]),
});

// Main orchestrator agent - not directly called but can be used for single-turn interactions
export const customerSupportAgent = new Agent({
  name: "customerSupportAgent",
  tools: { websearchTool, githubSearchTool },
  model: openai("gpt-4o"),
  instructions:
    "You are a helpful customer support agent for Arthur AI. Help users by searching documentation and code repositories to answer their questions about Arthur AI products and services.",
});

// Step 1: Plan Agent - Analyzes the question and creates a structured plan
export const planAgent = new Agent({
  name: "planAgent",
  model: openai("gpt-4o"),
  instructions: "", // Will be populated from Arthur Engine prompt
});

// Step 2: Websearch Agent - Searches Arthur AI documentation
export const websearchAgent = new Agent({
  name: "websearchAgent",
  tools: { websearchTool },
  model: openai("gpt-4o"),
  instructions: "", // Will be populated from Arthur Engine prompt
});

// Step 3: GitHub Agent - Searches Arthur Engine repository
export const githubAgent = new Agent({
  name: "githubAgent",
  tools: { githubSearchTool },
  model: openai("gpt-4o"),
  instructions: "", // Will be populated from Arthur Engine prompt
});

// Step 4: Draft Agent - Creates initial response from search results
export const draftAgent = new Agent({
  name: "draftAgent",
  model: openai("gpt-4o"),
  instructions: "", // Will be populated from Arthur Engine prompt
});

// Step 5: Review Agent - Reviews and finalizes the response
export const reviewAgent = new Agent({
  name: "reviewAgent",
  model: openai("gpt-4o"),
  instructions: "", // Will be populated from Arthur Engine prompt
});
