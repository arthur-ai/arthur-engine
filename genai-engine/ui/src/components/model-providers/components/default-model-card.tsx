import { Alert, Autocomplete, Box, Button, Card, CardContent, CircularProgress, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { isAxiosError } from "axios";
import { useSnackbar } from "notistack";
import React, { useState } from "react";

import { useClearDefaultModelProvider, useDefaultModelProvider, useSetDefaultModelProvider } from "../hooks/useDefaultModelProvider";

import { useAvailableModels } from "@/hooks/useModelProviders";
import { ModelProvider } from "@/lib/api-client/api-client";

type Props = {
  enabledProviders: ModelProvider[];
  getProviderDisplayName: (provider: string) => string;
};

type Draft = { provider: ModelProvider | null; modelName: string | null };

export const DefaultModelCard: React.FC<Props> = ({ enabledProviders, getProviderDisplayName }) => {
  const { enqueueSnackbar } = useSnackbar();
  const { data: current, isLoading, isError, refetch } = useDefaultModelProvider();
  const { availableModels } = useAvailableModels(enabledProviders);
  const setDefault = useSetDefaultModelProvider();
  const clearDefault = useClearDefaultModelProvider();

  // Unsaved edits; null means "show what the server has"
  const [draft, setDraft] = useState<Draft | null>(null);

  const provider = draft ? draft.provider : (current?.provider ?? null);
  const modelName = draft ? draft.modelName : (current?.model_name ?? null);
  const models = provider ? (availableModels.get(provider) ?? []) : [];
  const isSet = !!current?.provider && !!current?.model_name;
  const isDirty = draft !== null && (draft.provider !== (current?.provider ?? null) || draft.modelName !== (current?.model_name ?? null));
  const isBusy = setDefault.isPending || clearDefault.isPending;

  const reportError = (err: unknown, fallback: string) => {
    const detail = isAxiosError(err) ? err.response?.data?.detail : undefined;
    enqueueSnackbar(typeof detail === "string" ? detail : fallback, { variant: "error" });
  };

  const handleSave = async () => {
    if (!provider || !modelName) return;
    try {
      await setDefault.mutateAsync({ provider, model_name: modelName });
      setDraft(null);
      enqueueSnackbar("Default model saved", { variant: "success" });
    } catch (err) {
      reportError(err, "Failed to save the default model");
    }
  };

  const handleClear = async () => {
    try {
      await clearDefault.mutateAsync();
      setDraft(null);
      enqueueSnackbar("Default model cleared", { variant: "success" });
    } catch (err) {
      reportError(err, "Failed to clear the default model");
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="h6" sx={{ color: "text.primary", fontWeight: 600 }}>
          Default model
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5, mb: 2 }}>
          Arthur&apos;s AI features run on this model: the AI Assistant always uses it, and synthetic data starts from it. Evals keep the model they
          were saved with.
        </Typography>

        {isLoading ? (
          <CircularProgress size={24} />
        ) : isError ? (
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={() => refetch()}>
                Retry
              </Button>
            }
          >
            Couldn&apos;t load the default model.
          </Alert>
        ) : (
          <Stack spacing={2}>
            {!isSet && <Alert severity="info">No default model is set. Features that use the default will report an error until you set one.</Alert>}
            {enabledProviders.length === 0 ? (
              <Alert severity="warning">Configure a model provider below before choosing a default model.</Alert>
            ) : (
              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                <TextField
                  select
                  variant="filled"
                  label="Provider"
                  value={provider ?? ""}
                  onChange={(e) => setDraft({ provider: e.target.value as ModelProvider, modelName: null })}
                  sx={{ minWidth: 220 }}
                  disabled={isBusy}
                >
                  {enabledProviders.map((p) => (
                    <MenuItem key={p} value={p}>
                      {getProviderDisplayName(p)}
                    </MenuItem>
                  ))}
                </TextField>
                <Autocomplete
                  options={models}
                  value={modelName}
                  onChange={(_, value) => setDraft({ provider, modelName: value })}
                  disabled={!provider || isBusy}
                  sx={{ minWidth: 320, flex: 1 }}
                  renderInput={(params) => <TextField {...params} variant="filled" label="Model" />}
                />
              </Box>
            )}
            <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
              {isSet && (
                <Button variant="text" color="error" onClick={handleClear} disabled={isBusy}>
                  Clear default
                </Button>
              )}
              {isDirty && (
                <Button variant="outlined" onClick={() => setDraft(null)} disabled={isBusy}>
                  Cancel
                </Button>
              )}
              <Button
                variant="contained"
                onClick={handleSave}
                disabled={!isDirty || !provider || !modelName || isBusy}
                startIcon={setDefault.isPending ? <CircularProgress size={16} /> : null}
              >
                Save
              </Button>
            </Box>
          </Stack>
        )}
      </CardContent>
    </Card>
  );
};
