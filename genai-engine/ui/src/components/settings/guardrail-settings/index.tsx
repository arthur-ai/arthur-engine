import { Alert, Autocomplete, Box, Button, Card, CardContent, CircularProgress, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { useState } from "react";

import {
  useGuardrailCatalog,
  useGuardrailConfiguration,
  useGuardrailPermissions,
  useSaveGuardrailConfiguration,
} from "@/components/model-providers/hooks/useGuardrailConfiguration";
import { useProviders } from "@/components/model-providers/hooks/useProviders";
import type { GuardrailLLMConfiguration } from "@/lib/api-client/api-client";

type Draft = Pick<GuardrailLLMConfiguration, "model" | "base_model"> & {
  provider: GuardrailLLMConfiguration["provider"] | "";
};

export const GuardrailSettings = () => {
  const { canRead } = useGuardrailPermissions();
  if (!canRead) return <Alert severity="info">You do not have permission to view guardrail settings.</Alert>;
  return <GuardrailSettingsEditor />;
};

const GuardrailSettingsEditor = () => {
  const { canWrite } = useGuardrailPermissions();
  const configuration = useGuardrailConfiguration();
  const providers = useProviders();
  const mutation = useSaveGuardrailConfiguration();
  const { enqueueSnackbar } = useSnackbar();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const selection: Draft = draft ?? configuration.data?.guardrail_llm ?? { provider: "", model: "", base_model: null };
  const selectedProvider = providers.data?.find((provider) => provider.provider === selection.provider);
  const enabledProviders = providers.data?.filter((provider) => provider.enabled) ?? [];
  const catalog = useGuardrailCatalog(selection.provider, !!selectedProvider?.enabled);
  const models = catalog.data?.catalog ?? [];
  const aliasesAllowed = selectedProvider?.supports_custom_models ?? false;
  const readOnly = !canWrite || mutation.isPending;
  const complete =
    !!selection.provider &&
    !!selection.model.trim() &&
    !!selectedProvider?.enabled &&
    (aliasesAllowed || models.includes(selection.model)) &&
    (!selection.base_model || models.includes(selection.base_model));

  const save = async () => {
    if (!complete || !selection.provider) return;
    setSaveError(null);
    try {
      await mutation.mutateAsync({
        provider: selection.provider,
        model: selection.model,
        base_model: selection.base_model || null,
      });
      const refreshed = await configuration.refetch();
      if (refreshed.isError) {
        setSaveError("Settings were saved, but could not be refreshed. Retry loading the page.");
        return;
      }
      setDraft(null);
      enqueueSnackbar("Guardrail settings saved", { variant: "success" });
    } catch {
      setSaveError("Guardrail settings could not be saved. Check the provider and model, then try again.");
    }
  };

  if (configuration.isLoading || providers.isLoading) return <CircularProgress aria-label="Loading guardrail settings" />;
  if (configuration.isError || providers.isError) {
    return (
      <Alert
        severity="error"
        action={
          <Button
            onClick={() => {
              void configuration.refetch();
              void providers.refetch();
            }}
          >
            Retry
          </Button>
        }
      >
        Guardrail settings could not be loaded.
      </Alert>
    );
  }

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={3} sx={{ maxWidth: 760 }}>
          <Box>
            <Typography variant="h5" fontWeight={600}>
              Guardrail Settings
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 1 }}>
              Applies to hallucination and sensitive-data validation checks for all organizations. Judge calls consume the calling resource&apos;s
              organization credits. Model-picker restrictions do not limit this service model.
            </Typography>
          </Box>
          {configuration.data?.guardrail_llm_status === "needs_configuration" && (
            <Alert severity="warning">A model provider and model must be configured for guardrails.</Alert>
          )}
          {configuration.data?.guardrail_llm_status === "invalid" && (
            <Alert severity="error">The saved guardrail configuration is invalid. Select a provider and model to replace it.</Alert>
          )}
          {!canWrite && <Alert severity="info">Only an organization administrator can change these settings.</Alert>}
          {enabledProviders.length === 0 && (
            <Alert severity="info">No model providers are enabled. Configure credentials in Model Providers first.</Alert>
          )}
          <TextField
            select
            variant="filled"
            label="Model provider"
            value={selection.provider}
            disabled={readOnly || enabledProviders.length === 0}
            onChange={(event) => {
              const provider = enabledProviders.find((item) => item.provider === event.target.value);
              if (provider) {
                setDraft({ provider: provider.provider, model: "", base_model: null });
                setSaveError(null);
              }
            }}
          >
            {selectedProvider && !selectedProvider.enabled && (
              <MenuItem value={selectedProvider.provider} disabled>
                {selectedProvider.provider} (not configured)
              </MenuItem>
            )}
            {enabledProviders.map((provider) => (
              <MenuItem key={provider.provider} value={provider.provider}>
                {provider.provider}
              </MenuItem>
            ))}
          </TextField>
          {catalog.isError && (
            <Alert severity="error" action={<Button onClick={() => void catalog.refetch()}>Retry</Button>}>
              The model catalog could not be loaded.{aliasesAllowed ? " You can still enter an exact routing name." : ""}
            </Alert>
          )}
          {!!selection.provider && !catalog.isLoading && !catalog.isError && models.length === 0 && (
            <Alert severity="info">No catalog models are available for this provider.</Alert>
          )}
          <Autocomplete
            freeSolo={aliasesAllowed}
            options={models}
            value={selection.model || null}
            inputValue={aliasesAllowed ? selection.model : undefined}
            loading={catalog.isLoading}
            disabled={readOnly || !selectedProvider?.enabled}
            onChange={(_, model) => setDraft({ ...selection, model: model ?? "" })}
            onInputChange={(_, model, reason) => {
              if (reason === "input" && aliasesAllowed) setDraft({ ...selection, model });
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                variant="filled"
                label={aliasesAllowed ? "Model or exact routing name" : "Model"}
                helperText="The full catalog can include models your provider account cannot access. Saving does not test a paid connection."
              />
            )}
          />
          {aliasesAllowed && (
            <Autocomplete
              options={models}
              value={selection.base_model ?? null}
              disabled={readOnly || !selectedProvider?.enabled || catalog.isError}
              onChange={(_, base_model) => setDraft({ ...selection, base_model })}
              renderInput={(params) => (
                <TextField
                  {...params}
                  variant="filled"
                  label="Catalog base model (optional)"
                  helperText="Supplies capabilities and token limits only. The routing name above is sent to the provider unchanged."
                />
              )}
            />
          )}
          {saveError && <Alert severity="error">{saveError}</Alert>}
          {canWrite && (
            <Button
              variant="contained"
              sx={{ alignSelf: "flex-start" }}
              disabled={!complete || mutation.isPending || catalog.isLoading || configuration.isFetching || providers.isFetching}
              onClick={() => void save()}
            >
              {mutation.isPending ? "Saving..." : "Save"}
            </Button>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};
