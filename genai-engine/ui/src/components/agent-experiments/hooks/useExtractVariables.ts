import { HttpHeader } from "@/lib/api-client/api-client";

type FormEndpoint = {
  body: string;
  headers: HttpHeader[];
};

const MUSTACHE_REGEX = /\{\{\s*([^}\s]+)\s*\}\}/g;

export const extractVariablesFromText = (text: string): string[] => {
  return Array.from(text.matchAll(MUSTACHE_REGEX), (match) => match[1]);
};

export const useExtractVariables = (endpoint: FormEndpoint) => {
  const bodyVariables = extractVariablesFromText(endpoint.body);
  const headersVariables = endpoint.headers.flatMap((header) => [
    ...extractVariablesFromText(header.name),
    ...extractVariablesFromText(header.value),
  ]);
  return [...new Set([...bodyVariables, ...headersVariables])];
};
