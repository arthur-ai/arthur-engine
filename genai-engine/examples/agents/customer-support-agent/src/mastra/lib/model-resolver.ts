/**
 * Model Resolver
 * 
 * Dynamically resolves AI models based on provider and model name
 * from Arthur prompt configurations.
 */

import { openai } from "@ai-sdk/openai";
import type { LanguageModelV1 } from "ai";

export interface ModelConfig {
  provider: string;
  modelName: string;
}

/**
 * Resolves a language model based on the provider and model name
 * returned from Arthur prompt configuration.
 * 
 * @param provider - The model provider (e.g., "openai", "anthropic")
 * @param modelName - The model name (e.g., "gpt-4", "gpt-4o", "claude-3-5-sonnet")
 * @returns The resolved language model
 * 
 * @example
 * ```typescript
 * const model = resolveModel("openai", "gpt-4o");
 * const result = await agent.generate(messages, { model });
 * ```
 */
export function resolveModel(
  provider: string,
  modelName: string
): LanguageModelV1 {
  const normalizedProvider = provider.toLowerCase();
  
  switch (normalizedProvider) {
    case "openai":
      return openai(modelName);
    
    // Add support for other providers as needed
    // case "anthropic":
    //   return anthropic(modelName);
    // case "google":
    //   return google(modelName);
    
    default:
      console.warn(
        `Unknown model provider: ${provider}. Falling back to OpenAI with model: ${modelName}`
      );
      return openai(modelName);
  }
}

/**
 * Resolves a model from Arthur prompt result
 * 
 * @param promptResult - The result from getTemplatedPrompt containing model info
 * @returns The resolved language model
 */
export function resolveModelFromPrompt(promptResult: {
  model_provider: string;
  model_name: string;
}): LanguageModelV1 {
  return resolveModel(promptResult.model_provider, promptResult.model_name);
}
