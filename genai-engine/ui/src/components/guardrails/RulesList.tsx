import AddIcon from "@mui/icons-material/Add";
import { Alert, Box, Button, CircularProgress, Stack, Typography } from "@mui/material";
import React from "react";

import { RuleCard } from "./RuleCard";

import type { RuleResponse } from "@/lib/api-client/api-client";

interface RulesListProps {
  rules: RuleResponse[];
  isLoading: boolean;
  error: Error | null;
  onAddRule: () => void;
  onToggleRule: (rule: RuleResponse, enabled: boolean) => void;
  onDeleteRule: (rule: RuleResponse) => void;
  pendingRuleId: string | null;
}

export const RulesList: React.FC<RulesListProps> = ({ rules, isLoading, error, onAddRule, onToggleRule, onDeleteRule, pendingRuleId }) => {
  return (
    <Stack spacing={2} sx={{ height: "100%" }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between">
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Rules
        </Typography>
        <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={onAddRule}>
          Add rule
        </Button>
      </Stack>

      {isLoading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress size={28} />
        </Box>
      )}

      {error && !isLoading && <Alert severity="error">Failed to load rules: {error.message}</Alert>}

      {!isLoading && !error && rules.length === 0 && (
        <Box
          sx={{
            border: "1px dashed",
            borderColor: "divider",
            borderRadius: 1,
            p: 4,
            textAlign: "center",
          }}
        >
          <Typography variant="body2" color="text.secondary">
            No rules attached to this task. Click <strong>Add rule</strong> to create one.
          </Typography>
        </Box>
      )}

      <Stack spacing={1.5} sx={{ overflowY: "auto", flex: 1, minHeight: 0 }}>
        {rules.map((rule) => (
          <RuleCard key={rule.id} rule={rule} onToggle={onToggleRule} onDelete={onDeleteRule} isUpdating={pendingRuleId === rule.id} />
        ))}
      </Stack>
    </Stack>
  );
};
