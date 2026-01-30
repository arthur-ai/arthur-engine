import { formOptions } from "@tanstack/react-form";
import z from "zod";

import { ModelProvider } from "@/lib/api-client/api-client";

export const DEFAULT_VALUES = {
  anthropic: {
    api_key: "",
  },
  openai: {
    api_key: "",
  },
  gemini: {
    api_key: "",
  },
  vertex_ai: {
    project_id: "",
    region: "",
    gcp_service_account_credentials: null as File | null,
  },
  bedrock: {
    type: "api_key",
    api_key: "",
    aws_access_key_id: "",
    aws_secret_access_key: "",
    aws_bedrock_runtime_endpoint: "",
    aws_role_name: "",
    aws_session_name: "",
  } as (
    | {
        type: "api_key";
        api_key: string;
      }
    | {
        type: "access_key";
        aws_access_key_id: string;
        aws_secret_access_key: string;
      }
  ) & {
    aws_bedrock_runtime_endpoint: string;
    aws_role_name: string;
    aws_session_name: string;
  },
  hosted_vllm: {
    api_base: "",
    api_key: "",
  },
};

export const CredentialsSchema = z.object({
  type: z.string(),
  project_id: z.string(),
  private_key_id: z.string(),
  private_key: z.string(),
  client_email: z.string(),
  client_id: z.string(),
  auth_uri: z.string(),
  token_uri: z.string(),
  auth_provider_x509_cert_url: z.string(),
  client_x509_cert_url: z.string(),
  universe_domain: z.string(),
});

export const editFormOptions = (modelProvider: ModelProvider) =>
  formOptions({
    defaultValues: DEFAULT_VALUES[modelProvider],
  });

export type AnthropicFormValues = typeof DEFAULT_VALUES.anthropic;
export type OpenAIFormValues = typeof DEFAULT_VALUES.openai;
export type GeminiFormValues = typeof DEFAULT_VALUES.gemini;
export type VertexAIFormValues = typeof DEFAULT_VALUES.vertex_ai;
export type BedrockFormValues = typeof DEFAULT_VALUES.bedrock;
export type VllmFormValues = typeof DEFAULT_VALUES.hosted_vllm;
