import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { Alert, Box, Button, Chip, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import React, { useState } from "react";

import type { ExternalRuleResult, RuleResultEnum, ValidationResult } from "@/lib/api-client/api-client";

interface TestPromptPanelProps {
  onValidate: (prompt: string) => Promise<ValidationResult>;
  validating: boolean;
  result: ValidationResult | null;
  error: string | null;
}

const resultColor = (result: RuleResultEnum): "success" | "error" | "default" => {
  if (result === "Pass") return "success";
  if (result === "Fail") return "error";
  return "default";
};

const ResultIcon: React.FC<{ result: RuleResultEnum }> = ({ result }) => {
  if (result === "Pass") return <CheckCircleOutlineIcon fontSize="small" sx={{ color: "success.main" }} />;
  if (result === "Fail") return <CancelOutlinedIcon fontSize="small" sx={{ color: "error.main" }} />;
  return <HelpOutlineIcon fontSize="small" sx={{ color: "text.disabled" }} />;
};

const detailsMessage = (rr: ExternalRuleResult): string | null => {
  const d = rr.details;
  if (!d) return null;
  if ("message" in d && typeof d.message === "string" && d.message.length > 0) return d.message;
  return null;
};

const detailsExtras = (rr: ExternalRuleResult): string[] => {
  const d = rr.details;
  if (!d) return [];

  const out: string[] = [];

  if ("keyword_matches" in d && Array.isArray(d.keyword_matches) && d.keyword_matches.length > 0) {
    out.push(`Matched keywords: ${d.keyword_matches.map((m) => m.keyword).join(", ")}`);
  }
  if ("regex_matches" in d && Array.isArray(d.regex_matches) && d.regex_matches.length > 0) {
    const matches = d.regex_matches as Array<{ matching_text?: string }>;
    const texts = matches.map((m) => m.matching_text).filter((t): t is string => typeof t === "string");
    if (texts.length > 0) out.push(`Matched: ${texts.join(", ")}`);
  }
  if ("pii_entities" in d && Array.isArray(d.pii_entities) && d.pii_entities.length > 0) {
    out.push(`Detected: ${d.pii_entities.map((e) => e.entity).join(", ")}`);
  }
  if ("toxicity_score" in d && typeof d.toxicity_score === "number") {
    out.push(`Toxicity score: ${d.toxicity_score.toFixed(3)}`);
  }
  if ("claims" in d && Array.isArray(d.claims) && d.claims.length > 0) {
    const invalid = (d.claims as Array<{ valid?: boolean; claim?: string }>).filter((c) => c.valid === false);
    if (invalid.length > 0) {
      out.push(
        `Invalid claims: ${invalid
          .map((c) => c.claim ?? "")
          .filter(Boolean)
          .join(" | ")}`
      );
    }
  }

  return out;
};

export const TestPromptPanel: React.FC<TestPromptPanelProps> = ({ onValidate, validating, result, error }) => {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || validating) return;
    void onValidate(prompt);
  };

  const ruleResults = result?.rule_results ?? [];

  return (
    <Stack spacing={2} sx={{ height: "100%" }}>
      <Typography variant="h6" sx={{ fontWeight: 600 }}>
        Test prompt
      </Typography>

      <form onSubmit={handleSubmit}>
        <Stack spacing={1.5}>
          <TextField
            label="Prompt"
            placeholder="Type a prompt to validate against this task's rules..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            multiline
            minRows={5}
            fullWidth
            disabled={validating}
          />
          <Box>
            <Button type="submit" variant="contained" disabled={validating || !prompt.trim()} sx={{ minWidth: 140 }}>
              {validating ? <CircularProgress size={20} sx={{ color: "inherit" }} /> : "Validate"}
            </Button>
          </Box>
        </Stack>
      </form>

      {error && <Alert severity="error">{error}</Alert>}

      {result && (
        <Stack spacing={1.5} sx={{ overflowY: "auto", flex: 1, minHeight: 0 }}>
          <Typography variant="subtitle2" sx={{ color: "text.secondary" }}>
            Results ({ruleResults.length})
          </Typography>

          {ruleResults.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No rules ran for this prompt.
            </Typography>
          )}

          {ruleResults.map((rr) => {
            const message = detailsMessage(rr);
            const extras = detailsExtras(rr);
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
                <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: message || extras.length > 0 ? 0.75 : 0 }}>
                  <ResultIcon result={rr.result} />
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, flex: 1, minWidth: 0 }} noWrap>
                    {rr.name}
                  </Typography>
                  <Chip
                    label={rr.result}
                    size="small"
                    color={resultColor(rr.result)}
                    variant={rr.result === "Pass" ? "outlined" : "filled"}
                    sx={{ height: 20, fontSize: 11 }}
                  />
                  <Typography variant="caption" color="text.disabled">
                    {rr.latency_ms}ms
                  </Typography>
                </Stack>
                {message && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", pl: 3 }}>
                    {message}
                  </Typography>
                )}
                {extras.map((line) => (
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
