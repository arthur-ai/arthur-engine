import { Box, Paper, Stack, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import React, { useMemo, useState } from "react";

import { CreateRuleDialog } from "./CreateRuleDialog";
import { RulesList } from "./RulesList";
import { TestPromptPanel } from "./TestPromptPanel";

import { ConfirmationModal } from "@/components/common/ConfirmationModal";
import { getContentHeight } from "@/constants/layout";
import { useArchiveRule, useCreateRule, useTaskRules, useToggleRule, useValidate } from "@/hooks/useGuardrails";
import { useTask } from "@/hooks/useTask";
import type { BuiltinValidationRequest, NewRuleRequest, RuleResponse, RuleType } from "@/lib/api-client/api-client";
import { getApiErrorMessage } from "@/utils/errorUtils";

export const GuardrailsView: React.FC = () => {
  const { task } = useTask();
  const taskId = task?.id ?? "";
  const { enqueueSnackbar } = useSnackbar();

  const { data: rules = [], isLoading, error } = useTaskRules(taskId);
  const createMutation = useCreateRule(taskId);
  const archiveMutation = useArchiveRule(taskId);
  const toggleMutation = useToggleRule(taskId);
  const validateMutation = useValidate();

  const enabledChecks = useMemo<NewRuleRequest[]>(
    () =>
      rules
        .filter((r) => r.enabled !== false)
        .map((r) => ({
          name: r.name,
          type: r.type,
          apply_to_prompt: r.apply_to_prompt,
          apply_to_response: r.apply_to_response,
          config: r.config ?? null,
        })),
    [rules]
  );

  const enabledRuleTypes = useMemo<RuleType[]>(() => rules.filter((r) => r.enabled !== false).map((r) => r.type), [rules]);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogNonce, setDialogNonce] = useState(0);
  const [createError, setCreateError] = useState<string | null>(null);
  const [pendingRuleId, setPendingRuleId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<RuleResponse | null>(null);
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
      setCreateError(getApiErrorMessage(e));
    }
  };

  const handleToggle = async (rule: RuleResponse, enabled: boolean) => {
    setPendingRuleId(rule.id);
    try {
      await toggleMutation.mutateAsync({ ruleId: rule.id, enabled });
    } catch (e) {
      enqueueSnackbar(`Failed to update rule: ${getApiErrorMessage(e)}`, { variant: "error" });
    } finally {
      setPendingRuleId(null);
    }
  };

  const requestDelete = (rule: RuleResponse) => setPendingDelete(rule);

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    const rule = pendingDelete;
    setPendingRuleId(rule.id);
    try {
      await archiveMutation.mutateAsync(rule.id);
      enqueueSnackbar(`Rule "${rule.name}" deleted`, { variant: "success" });
    } catch (e) {
      enqueueSnackbar(`Failed to delete rule: ${getApiErrorMessage(e)}`, { variant: "error" });
    } finally {
      setPendingRuleId(null);
    }
  };

  const handleValidate = async (input: { prompt: string; response: string; context: string }) => {
    setValidateError(null);
    const request: BuiltinValidationRequest = {
      checks: enabledChecks,
      prompt: input.prompt.trim() || null,
      response: input.response.trim() || null,
      context: input.context.trim() || null,
    };
    try {
      return await validateMutation.mutateAsync(request);
    } catch (e) {
      setValidateError(getApiErrorMessage(e));
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
              onDeleteRule={requestDelete}
              pendingRuleId={pendingRuleId}
            />
          </Paper>

          <Paper variant="outlined" sx={{ p: 2.5, flex: 1, minHeight: 0, overflow: "hidden" }}>
            <TestPromptPanel
              onValidate={handleValidate}
              onResetResults={validateMutation.reset}
              validating={validateMutation.isPending}
              results={validateMutation.data?.results ?? null}
              error={validateError}
              hasEnabledRules={enabledChecks.length > 0}
              enabledRuleTypes={enabledRuleTypes}
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

      <ConfirmationModal
        open={pendingDelete !== null}
        onClose={() => setPendingDelete(null)}
        onConfirm={confirmDelete}
        title="Delete rule"
        message={pendingDelete ? `Delete rule "${pendingDelete.name}"? This cannot be undone.` : ""}
        confirmText="Delete"
      />
    </Box>
  );
};
