import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import { Alert, Box, Button, Chip, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import React, { useState } from "react";

import type {
  BuiltinValidationResponse,
  ExternalRuleResult,
  HallucinationDetailsResponse,
  KeywordDetailsResponse,
  PIIDetailsResponse,
  RegexDetailsResponse,
  RuleResultEnum,
  RuleType,
  ToxicityDetailsResponse,
} from "@/lib/api-client/api-client";

interface TestPromptPanelProps {
  onValidate: (input: { prompt: string; response: string; context: string }) => Promise<BuiltinValidationResponse>;
  onResetResults: () => void;
  validating: boolean;
  results: ExternalRuleResult[] | null;
  error: string | null;
  hasEnabledRules: boolean;
  enabledRuleTypes: RuleType[];
}

type ResultClass = "pass" | "fail" | "skipped" | "unavailable";

const classifyResult = (r: RuleResultEnum): ResultClass => {
  if (r === "Pass") return "pass";
  if (r === "Fail") return "fail";
  if (r === "Skipped") return "skipped";
  return "unavailable";
};

interface ResultStyle {
  icon: React.ReactNode;
  chipColor: "success" | "error" | "info" | "warning";
  chipVariant: "filled" | "outlined";
  reasonColor: string;
  treatMessageAsReason: boolean;
}

const RESULT_STYLE: Record<ResultClass, ResultStyle> = {
  pass: {
    icon: <CheckCircleOutlineIcon fontSize="small" sx={{ color: "success.main" }} />,
    chipColor: "success",
    chipVariant: "outlined",
    reasonColor: "success.main",
    treatMessageAsReason: false,
  },
  fail: {
    icon: <CancelOutlinedIcon fontSize="small" sx={{ color: "error.main" }} />,
    chipColor: "error",
    chipVariant: "filled",
    reasonColor: "error.main",
    treatMessageAsReason: false,
  },
  skipped: {
    icon: <InfoOutlinedIcon fontSize="small" sx={{ color: "info.main" }} />,
    chipColor: "info",
    chipVariant: "outlined",
    reasonColor: "info.main",
    treatMessageAsReason: true,
  },
  unavailable: {
    icon: <WarningAmberOutlinedIcon fontSize="small" sx={{ color: "warning.main" }} />,
    chipColor: "warning",
    chipVariant: "outlined",
    reasonColor: "warning.main",
    treatMessageAsReason: true,
  },
};

const buildDetailLines = (rr: ExternalRuleResult): string[] => {
  const lines: string[] = [];
  const d = rr.details;
  if (!d) return lines;

  if ("message" in d && typeof d.message === "string" && d.message.length > 0) {
    lines.push(d.message);
  }

  switch (rr.rule_type) {
    case "KeywordRule": {
      const kd = d as KeywordDetailsResponse;
      if (kd.keyword_matches?.length) {
        lines.push(`Matched keywords: ${kd.keyword_matches.map((m) => m.keyword).join(", ")}`);
      }
      break;
    }
    case "RegexRule": {
      const rd = d as RegexDetailsResponse;
      const texts = rd.regex_matches?.map((m) => m.matching_text).filter((t): t is string => typeof t === "string");
      if (texts?.length) lines.push(`Matched: ${texts.join(", ")}`);
      break;
    }
    case "PIIDataRule": {
      const pd = d as PIIDetailsResponse;
      if (pd.pii_entities?.length) {
        lines.push(`Detected: ${pd.pii_entities.map((e) => e.entity).join(", ")}`);
      }
      break;
    }
    case "ToxicityRule": {
      const td = d as ToxicityDetailsResponse;
      if (typeof td.toxicity_score === "number") {
        lines.push(`Toxicity score: ${td.toxicity_score.toFixed(3)}`);
      }
      break;
    }
    case "ModelHallucinationRuleV2": {
      const hd = d as HallucinationDetailsResponse;
      const invalid = hd.claims?.filter((c) => c.valid === false) ?? [];
      if (invalid.length) {
        lines.push(
          `Invalid claims: ${invalid
            .map((c) => c.claim ?? "")
            .filter(Boolean)
            .join(" | ")}`
        );
      }
      break;
    }
    case "PromptInjectionRule":
    case "ModelSensitiveDataRule":
      break;
  }

  return lines;
};

export const TestPromptPanel: React.FC<TestPromptPanelProps> = ({
  onValidate,
  onResetResults,
  validating,
  results,
  error,
  hasEnabledRules,
  enabledRuleTypes,
}) => {
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [context, setContext] = useState("");

  const hasInput = prompt.trim().length > 0 || response.trim().length > 0;
  const canSubmit = !validating && hasEnabledRules && hasInput;

  const onFieldChange = (setter: (v: string) => void) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setter(e.target.value);
    if (results !== null) onResetResults();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    void onValidate({ prompt, response, context });
  };

  const needsContext = enabledRuleTypes.includes("ModelHallucinationRuleV2");
  const needsResponse = enabledRuleTypes.some((t) => t === "ModelHallucinationRuleV2" || t === "ModelSensitiveDataRule");
  const inputHint: string | null = (() => {
    if (needsContext && !context.trim()) return "Hallucination check needs context to run.";
    if (needsResponse && !response.trim()) return "Some enabled rules apply to the response — add a response to exercise them.";
    return null;
  })();

  const ruleResults = results ?? [];

  return (
    <Stack spacing={2} sx={{ height: "100%" }}>
      <Typography variant="h6" sx={{ fontWeight: 600 }}>
        Test prompt
      </Typography>

      <form onSubmit={handleSubmit}>
        <Stack spacing={1.5}>
          <TextField
            label="Prompt"
            placeholder="Optional — user prompt to validate."
            value={prompt}
            onChange={onFieldChange(setPrompt)}
            multiline
            minRows={4}
            fullWidth
            disabled={validating}
          />
          <TextField
            label="Response"
            placeholder="Optional — LLM response to validate."
            value={response}
            onChange={onFieldChange(setResponse)}
            multiline
            minRows={3}
            fullWidth
            disabled={validating}
          />
          <TextField
            label="Context"
            placeholder="Optional — grounding context (required for hallucination checks)."
            value={context}
            onChange={onFieldChange(setContext)}
            multiline
            minRows={2}
            fullWidth
            disabled={validating}
            helperText="Provide at least a prompt or a response."
          />
          {!hasEnabledRules && <Alert severity="info">No enabled rules on this task. Add or enable a rule to test.</Alert>}
          {hasEnabledRules && inputHint && (
            <Typography variant="caption" color="text.secondary">
              {inputHint}
            </Typography>
          )}
          <Box>
            <Button type="submit" variant="contained" disabled={!canSubmit} sx={{ minWidth: 140 }}>
              {validating ? <CircularProgress size={20} sx={{ color: "inherit" }} /> : "Validate"}
            </Button>
          </Box>
        </Stack>
      </form>

      {error && <Alert severity="error">{error}</Alert>}

      {results && (
        <Stack spacing={1.5} sx={{ overflowY: "auto", flex: 1, minHeight: 0 }}>
          <Typography variant="subtitle2" sx={{ color: "text.secondary" }}>
            Results ({ruleResults.length})
          </Typography>

          {ruleResults.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No rules ran for this input.
            </Typography>
          )}

          {ruleResults.map((rr) => {
            const lines = buildDetailLines(rr);
            const style = RESULT_STYLE[classifyResult(rr.result)];
            const showAsReason = style.treatMessageAsReason && lines.length > 0;
            return (
              <Box
                key={rr.id}
                sx={{
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 1,
                  p: 1.5,
                }}
              >
                <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: lines.length > 0 ? 0.75 : 0 }}>
                  {style.icon}
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, flex: 1, minWidth: 0 }} noWrap>
                    {rr.name}
                  </Typography>
                  <Chip label={rr.result} size="small" color={style.chipColor} variant={style.chipVariant} sx={{ height: 20, fontSize: 11 }} />
                  <Typography variant="caption" color="text.disabled">
                    {rr.latency_ms}ms
                  </Typography>
                </Stack>
                {showAsReason && (
                  <Typography variant="caption" sx={{ display: "block", pl: 3, color: style.reasonColor, fontWeight: 500 }}>
                    Reason: {lines[0]}
                  </Typography>
                )}
                {lines.slice(showAsReason ? 1 : 0).map((line) => (
                  <Typography key={line} variant="caption" color="text.secondary" sx={{ display: "block", pl: 3 }}>
                    {line}
                  </Typography>
                ))}
              </Box>
            );
          })}
        </Stack>
      )}
    </Stack>
  );
};
