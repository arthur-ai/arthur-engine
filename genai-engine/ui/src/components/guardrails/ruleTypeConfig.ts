import type { PIIEntityTypes, RuleType } from "@/lib/api-client/api-client";

export interface RuleTypeMeta {
  type: RuleType;
  label: string;
  description: string;
  // Whether the user can configure apply_to_prompt / apply_to_response. If forced,
  // the value is set and the corresponding switch is disabled.
  apply_to_prompt: { allowed: boolean; default: boolean };
  apply_to_response: { allowed: boolean; default: boolean };
  configKind: "none" | "keywords" | "regex" | "pii" | "examples_json";
}

export const RULE_TYPE_META: Record<RuleType, RuleTypeMeta> = {
  PromptInjectionRule: {
    type: "PromptInjectionRule",
    label: "Prompt Injection",
    description: "Detects prompt injection attempts using a DebertaV3 classifier. Prompt-only.",
    apply_to_prompt: { allowed: false, default: true },
    apply_to_response: { allowed: false, default: false },
    configKind: "none",
  },
  ModelHallucinationRuleV2: {
    type: "ModelHallucinationRuleV2",
    label: "Hallucination",
    description: "Claim-based LLM judge detects hallucinated claims in model output. Response-only.",
    apply_to_prompt: { allowed: false, default: false },
    apply_to_response: { allowed: false, default: true },
    configKind: "none",
  },
  ToxicityRule: {
    type: "ToxicityRule",
    label: "Toxicity",
    description: "RoBERTa-based toxicity classifier with default threshold (0.5).",
    apply_to_prompt: { allowed: true, default: true },
    apply_to_response: { allowed: true, default: true },
    configKind: "none",
  },
  KeywordRule: {
    type: "KeywordRule",
    label: "Keyword",
    description: "Fails if any of the listed keywords appear in the text.",
    apply_to_prompt: { allowed: true, default: true },
    apply_to_response: { allowed: true, default: true },
    configKind: "keywords",
  },
  RegexRule: {
    type: "RegexRule",
    label: "Regex",
    description: "Fails if any of the listed regex patterns match the text.",
    apply_to_prompt: { allowed: true, default: true },
    apply_to_response: { allowed: true, default: true },
    configKind: "regex",
  },
  PIIDataRule: {
    type: "PIIDataRule",
    label: "PII",
    description: "Detects PII via Presidio + GLiNER. Configure entity types to disable and an allow-list.",
    apply_to_prompt: { allowed: true, default: true },
    apply_to_response: { allowed: true, default: true },
    configKind: "pii",
  },
  ModelSensitiveDataRule: {
    type: "ModelSensitiveDataRule",
    label: "Sensitive Data",
    description: "Few-shot LLM judge for custom sensitive-data definitions. Provide examples as JSON.",
    apply_to_prompt: { allowed: true, default: true },
    apply_to_response: { allowed: true, default: true },
    configKind: "examples_json",
  },
};

export const RULE_TYPES_ORDERED: RuleType[] = [
  "PromptInjectionRule",
  "ModelHallucinationRuleV2",
  "ToxicityRule",
  "KeywordRule",
  "RegexRule",
  "PIIDataRule",
  "ModelSensitiveDataRule",
];

export const PII_ENTITY_VALUES: PIIEntityTypes[] = [
  "CREDIT_CARD",
  "CRYPTO",
  "DATE_TIME",
  "EMAIL_ADDRESS",
  "IBAN_CODE",
  "IP_ADDRESS",
  "NRP",
  "LOCATION",
  "PERSON",
  "PHONE_NUMBER",
  "MEDICAL_LICENSE",
  "URL",
  "US_BANK_NUMBER",
  "US_DRIVER_LICENSE",
  "US_ITIN",
  "US_PASSPORT",
  "US_SSN",
];
