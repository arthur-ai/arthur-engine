import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { Box, Card, CardContent, Chip, CircularProgress, IconButton, Stack, Switch, Tooltip, Typography } from "@mui/material";
import React from "react";

import { RULE_TYPE_META } from "./ruleTypeConfig";

import type { ExamplesConfig, KeywordsConfig, PIIConfig, RegexConfig, RuleResponse } from "@/lib/api-client/api-client";

interface RuleCardProps {
  rule: RuleResponse;
  onToggle: (rule: RuleResponse, enabled: boolean) => void;
  onDelete: (rule: RuleResponse) => void;
  isUpdating?: boolean;
  isModified?: boolean;
}

interface ConfigSummary {
  text: string;
  tooltip?: string;
}

const summarizeConfig = (rule: RuleResponse): ConfigSummary | null => {
  const meta = RULE_TYPE_META[rule.type];
  if (meta.configKind === "none" || !rule.config) return null;

  switch (meta.configKind) {
    case "keywords": {
      const c = rule.config as KeywordsConfig;
      const n = c.keywords?.length ?? 0;
      if (n === 0) return null;
      const preview = c.keywords.slice(0, 3).join(", ");
      const text = n <= 3 ? `${n} keyword${n === 1 ? "" : "s"}: ${preview}` : `${n} keywords: ${preview}, …`;
      return { text, tooltip: c.keywords.join(", ") };
    }
    case "regex": {
      const c = rule.config as RegexConfig;
      const n = c.regex_patterns?.length ?? 0;
      if (n === 0) return null;
      return { text: `${n} pattern${n === 1 ? "" : "s"}`, tooltip: c.regex_patterns.join("\n") };
    }
    case "pii": {
      const c = rule.config as PIIConfig;
      const disabled = c.disabled_pii_entities?.length ?? 0;
      const allowed = c.allow_list?.length ?? 0;
      const parts: string[] = [];
      if (disabled) parts.push(`${disabled} entity type${disabled === 1 ? "" : "s"} disabled`);
      if (allowed) parts.push(`${allowed} allow-listed`);
      if (parts.length === 0) return null;
      const tooltipParts: string[] = [];
      if (c.disabled_pii_entities?.length) tooltipParts.push(`Disabled: ${c.disabled_pii_entities.join(", ")}`);
      if (c.allow_list?.length) tooltipParts.push(`Allow list: ${c.allow_list.join(", ")}`);
      return { text: parts.join(" • "), tooltip: tooltipParts.join("\n") };
    }
    case "examples_json": {
      const c = rule.config as ExamplesConfig;
      const n = c.examples?.length ?? 0;
      if (n === 0) return null;
      const positives = c.examples.filter((e) => e.result).length;
      return { text: `${n} example${n === 1 ? "" : "s"} (${positives} sensitive)` };
    }
  }
  return null;
};

export const RuleCard: React.FC<RuleCardProps> = ({ rule, onToggle, onDelete, isUpdating, isModified }) => {
  const meta = RULE_TYPE_META[rule.type];
  const isDefault = rule.scope === "default";
  const enabled = rule.enabled ?? true;
  const summary = summarizeConfig(rule);

  return (
    <Card variant="outlined" sx={{ opacity: enabled ? 1 : 0.65 }}>
      <CardContent sx={{ pb: "16px !important", py: 1.5 }}>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
              <Tooltip title={rule.name}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, color: "text.primary", flex: 1, minWidth: 0 }} noWrap>
                  {rule.name}
                </Typography>
              </Tooltip>
              <Tooltip
                title={isDefault ? "Built-in guardrail available to every task. Cannot be deleted or disabled here." : "Custom rule for this task."}
              >
                <Chip
                  label={isDefault ? "Default" : "Task"}
                  size="small"
                  color={isDefault ? "default" : "primary"}
                  variant={isDefault ? "outlined" : "filled"}
                  sx={{ height: 20, fontSize: 11 }}
                />
              </Tooltip>
              {isModified && (
                <Tooltip title="Unsaved change">
                  <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: "warning.main", flexShrink: 0 }} />
                </Tooltip>
              )}
            </Stack>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                {meta?.label ?? rule.type}
              </Typography>
              <Typography variant="caption" sx={{ color: "text.disabled" }}>
                •
              </Typography>
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                {rule.apply_to_prompt && rule.apply_to_response
                  ? "prompt + response"
                  : rule.apply_to_prompt
                    ? "prompt"
                    : rule.apply_to_response
                      ? "response"
                      : "(neither)"}
              </Typography>
            </Stack>
            {summary &&
              (summary.tooltip ? (
                <Tooltip title={<Box sx={{ whiteSpace: "pre-wrap" }}>{summary.tooltip}</Box>}>
                  <Typography variant="caption" sx={{ color: "text.secondary", display: "block" }} noWrap>
                    {summary.text}
                  </Typography>
                </Tooltip>
              ) : (
                <Typography variant="caption" sx={{ color: "text.secondary", display: "block" }} noWrap>
                  {summary.text}
                </Typography>
              ))}
          </Box>

          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Tooltip title={isDefault ? "Default rules cannot be toggled per task here" : enabled ? "Disable rule" : "Enable rule"}>
              <span>
                <Switch size="small" checked={enabled} disabled={isDefault || isUpdating} onChange={(e) => onToggle(rule, e.target.checked)} />
              </span>
            </Tooltip>
          </Box>

          {!isDefault && (
            <Tooltip title="Delete rule">
              <span>
                <IconButton size="small" onClick={() => onDelete(rule)} disabled={isUpdating}>
                  {isUpdating ? <CircularProgress size={16} /> : <DeleteOutlineIcon fontSize="small" />}
                </IconButton>
              </span>
            </Tooltip>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};
