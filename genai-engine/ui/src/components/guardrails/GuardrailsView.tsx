import { Box, Paper, Stack, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import React, { useState } from "react";

import { CreateRuleDialog } from "./CreateRuleDialog";
import { RulesList } from "./RulesList";
import { TestPromptPanel } from "./TestPromptPanel";

import { getContentHeight } from "@/constants/layout";
import { useArchiveRule, useCreateRule, useTaskRules, useToggleRule, useValidatePrompt } from "@/hooks/useGuardrails";
import { useTask } from "@/hooks/useTask";
import type { NewRuleRequest, RuleResponse } from "@/lib/api-client/api-client";

const errorMessage = (e: unknown): string => {
  if (e instanceof Error) return e.message;
  if (typeof e === "string") return e;
  return "Unexpected error";
};

export const GuardrailsView: React.FC = () => {
  const { task } = useTask();
  const taskId = task?.id ?? "";
  const { enqueueSnackbar } = useSnackbar();

  const { data: rules = [], isLoading, error } = useTaskRules(taskId);
  const createMutation = useCreateRule(taskId);
  const archiveMutation = useArchiveRule(taskId);
  const toggleMutation = useToggleRule(taskId);
  const validateMutation = useValidatePrompt(taskId);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogNonce, setDialogNonce] = useState(0);
  const [createError, setCreateError] = useState<string | null>(null);
  const [pendingRuleId, setPendingRuleId] = useState<string | null>(null);
  const [validateError, setValidateError] = useState<string | null>(null);

  const handleOpenDialog = () => {
    setDialogNonce((n) => n + 1);
    setCreateError(null);
    setDialogOpen(true);
  };

  const handleCreate = async (rule: NewRuleRequest) => {
    setCreateError(null);
    try {
      await createMutation.mutateAsync(rule);
      setDialogOpen(false);
      enqueueSnackbar(`Rule "${rule.name}" created`, { variant: "success" });
    } catch (e) {
      setCreateError(errorMessage(e));
    }
  };

  const handleToggle = async (rule: RuleResponse, enabled: boolean) => {
    setPendingRuleId(rule.id);
    try {
      await toggleMutation.mutateAsync({ ruleId: rule.id, enabled });
    } catch (e) {
      enqueueSnackbar(`Failed to update rule: ${errorMessage(e)}`, { variant: "error" });
    } finally {
      setPendingRuleId(null);
    }
  };

  const handleDelete = async (rule: RuleResponse) => {
    setPendingRuleId(rule.id);
    try {
      await archiveMutation.mutateAsync(rule.id);
      enqueueSnackbar(`Rule "${rule.name}" deleted`, { variant: "success" });
    } catch (e) {
      enqueueSnackbar(`Failed to delete rule: ${errorMessage(e)}`, { variant: "error" });
    } finally {
      setPendingRuleId(null);
    }
  };

  const handleValidate = async (prompt: string) => {
    setValidateError(null);
    try {
      return await validateMutation.mutateAsync({ prompt });
    } catch (e) {
      setValidateError(errorMessage(e));
      throw e;
    }
  };

  return (
    <Box sx={{ p: 3, height: getContentHeight() }}>
      <Stack spacing={2} sx={{ height: "100%" }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            Guardrails
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure deterministic rules that validate prompts and responses for this task, and test them live.
          </Typography>
        </Box>

        <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ flex: 1, minHeight: 0 }}>
          <Paper variant="outlined" sx={{ p: 2.5, flex: { xs: "none", md: "0 0 45%" }, minHeight: 0, overflow: "hidden" }}>
            <RulesList
              rules={rules}
              isLoading={isLoading}
              error={error as Error | null}
              onAddRule={handleOpenDialog}
              onToggleRule={handleToggle}
              onDeleteRule={handleDelete}
              pendingRuleId={pendingRuleId}
            />
          </Paper>

          <Paper variant="outlined" sx={{ p: 2.5, flex: 1, minHeight: 0, overflow: "hidden" }}>
            <TestPromptPanel
              onValidate={handleValidate}
              validating={validateMutation.isPending}
              result={validateMutation.data ?? null}
              error={validateError}
            />
          </Paper>
        </Stack>
      </Stack>

      <CreateRuleDialog
        key={dialogNonce}
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleCreate}
        submitting={createMutation.isPending}
        error={createError}
      />
    </Box>
  );
};
