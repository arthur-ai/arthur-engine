import { Box, Paper, Stack, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import React, { useEffect, useMemo, useState } from "react";

import { CreateRuleDialog } from "./CreateRuleDialog";
import { RulesList } from "./RulesList";
import { TestPromptPanel } from "./TestPromptPanel";

import { ConfirmationModal } from "@/components/common/ConfirmationModal";
import { getContentHeight } from "@/constants/layout";
import { useGuardrailDraft } from "@/hooks/useGuardrailDraft";
import { useArchiveRule, useCreateRule, useSaveRuleStates, useTaskRules, useValidate } from "@/hooks/useGuardrails";
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
  const saveMutation = useSaveRuleStates(taskId);
  const validateMutation = useValidate();

  const { draftRules, setEnabled, discard, changes, hasUnsavedChanges } = useGuardrailDraft(rules);
  const modifiedRuleIds = useMemo(() => new Set(Object.keys(changes)), [changes]);

  // "Try it out" tests the staged (draft) configuration so changes can be previewed
  // before saving — the stateful production endpoint still uses only saved rules.
  const enabledChecks = useMemo<NewRuleRequest[]>(
    () =>
      draftRules
        .filter((r) => r.enabled !== false)
        .map((r) => ({
          name: r.name,
          type: r.type,
          apply_to_prompt: r.apply_to_prompt,
          apply_to_response: r.apply_to_response,
          config: r.config ?? null,
        })),
    [draftRules]
  );

  const enabledRuleTypes = useMemo<RuleType[]>(() => draftRules.filter((r) => r.enabled !== false).map((r) => r.type), [draftRules]);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogNonce, setDialogNonce] = useState(0);
  const [createError, setCreateError] = useState<string | null>(null);
  const [pendingRuleId, setPendingRuleId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<RuleResponse | null>(null);
  const [discardOpen, setDiscardOpen] = useState(false);
  const [validateError, setValidateError] = useState<string | null>(null);

  // Warn before the browser unloads (refresh/close/external nav) while there are
  // unsaved staged toggles. In-app navigation is signalled by the visible save bar —
  // useBlocker is unavailable here because the app uses BrowserRouter, not a data router.
  useEffect(() => {
    if (!hasUnsavedChanges) return;
    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [hasUnsavedChanges]);

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

  // Toggling only updates the local draft — nothing is persisted until Save.
  const handleToggle = (rule: RuleResponse, enabled: boolean) => setEnabled(rule, enabled);

  const handleSave = async () => {
    try {
      await saveMutation.mutateAsync(changes);
      enqueueSnackbar("Guardrail changes saved", { variant: "success" });
    } catch (e) {
      enqueueSnackbar(getApiErrorMessage(e), { variant: "error" });
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
              rules={draftRules}
              isLoading={isLoading}
              error={error as Error | null}
              onAddRule={handleOpenDialog}
              onToggleRule={handleToggle}
              onDeleteRule={requestDelete}
              pendingRuleId={pendingRuleId}
              modifiedRuleIds={modifiedRuleIds}
              hasUnsavedChanges={hasUnsavedChanges}
              isSaving={saveMutation.isPending}
              onSave={handleSave}
              onDiscard={() => setDiscardOpen(true)}
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

      <ConfirmationModal
        open={discardOpen}
        onClose={() => setDiscardOpen(false)}
        onConfirm={discard}
        title="Discard changes?"
        message="You have unsaved rule changes. Discarding will revert them to the last saved state."
        confirmText="Discard"
        cancelText="Keep editing"
      />
    </Box>
  );
};
