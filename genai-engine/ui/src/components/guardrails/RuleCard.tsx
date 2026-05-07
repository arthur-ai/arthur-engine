import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { Box, Card, CardContent, Chip, IconButton, Stack, Switch, Tooltip, Typography } from "@mui/material";
import React from "react";

import { RULE_TYPE_META } from "./ruleTypeConfig";

import type { RuleResponse } from "@/lib/api-client/api-client";

interface RuleCardProps {
  rule: RuleResponse;
  onToggle: (rule: RuleResponse, enabled: boolean) => void;
  onDelete: (rule: RuleResponse) => void;
  isUpdating?: boolean;
}

export const RuleCard: React.FC<RuleCardProps> = ({ rule, onToggle, onDelete, isUpdating }) => {
  const meta = RULE_TYPE_META[rule.type];
  const isDefault = rule.scope === "default";
  const enabled = rule.enabled ?? true;

  return (
    <Card variant="outlined" sx={{ opacity: enabled ? 1 : 0.65 }}>
      <CardContent sx={{ pb: "16px !important", py: 1.5 }}>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, color: "text.primary" }} noWrap>
                {rule.name}
              </Typography>
              <Chip
                label={isDefault ? "Default" : "Task"}
                size="small"
                color={isDefault ? "default" : "primary"}
                variant={isDefault ? "outlined" : "filled"}
                sx={{ height: 20, fontSize: 11 }}
              />
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
          </Box>

          <Tooltip title={isDefault ? "Default rules cannot be toggled per task here" : enabled ? "Disable rule" : "Enable rule"}>
            <span>
              <Switch size="small" checked={enabled} disabled={isDefault || isUpdating} onChange={(e) => onToggle(rule, e.target.checked)} />
            </span>
          </Tooltip>

          {!isDefault && (
            <Tooltip title="Delete rule">
              <span>
                <IconButton size="small" onClick={() => onDelete(rule)} disabled={isUpdating}>
                  <DeleteOutlineIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};
