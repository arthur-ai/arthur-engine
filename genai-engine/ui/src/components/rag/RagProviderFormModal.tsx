import { Alert, Box, Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, TextField } from "@mui/material";
import React, { useState } from "react";

import { useProviderForm } from "@/hooks/rag/useProviderForm";
import { useRagProviderMutations } from "@/hooks/rag/useRagProviderMutations";
import type {
  RagProviderConfigurationRequest,
  RagProviderConfigurationResponse,
  RagProviderConfigurationUpdateRequest,
} from "@/lib/api-client/api-client";

interface RagProviderFormModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  taskId: string;
  mode: "create" | "edit";
  initialData?: RagProviderConfigurationResponse;
}

export const RagProviderFormModal: React.FC<RagProviderFormModalProps> = ({ open, onClose, onSuccess, taskId, mode, initialData }) => {
  const { createProvider, updateProvider, testConnection } = useRagProviderMutations();
  const { form, values, fieldValidators, isFormValid, validateForm, resetForm, normalizeHostUrl } = useProviderForm(mode, initialData);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  const [connectionTested, setConnectionTested] = useState(mode === "edit" && !!initialData);

  const isTesting = testConnection.isPending;
  const isSaving = createProvider.isPending || updateProvider.isPending;

  const handleModalEnter = () => {
    resetForm();
    setConnectionTested(mode === "edit" && !!initialData);
    setTestResult(null);
  };

  const handleTestConnection = async () => {
    const isValid = await validateForm();
    if (!isValid) {
      return;
    }

    setTestResult(null);

    const normalizedUrl = normalizeHostUrl(values.host_url);

    const testData = {
      authentication_config: {
        authentication_method: "api_key" as const,
        host_url: normalizedUrl,
        api_key: values.api_key,
        rag_provider: "weaviate" as const,
      },
    };

    testConnection.mutate(
      { taskId, data: testData },
      {
        onSuccess: (result) => {
          if (result.connection_check_outcome === "passed") {
            setTestResult({
              success: true,
              message: "Connection successful! You can now save the provider.",
            });
            setConnectionTested(true);
          } else {
            setTestResult({
              success: false,
              message: result.failure_reason || "Connection test failed. Please check your credentials.",
            });
            setConnectionTested(false);
          }
        },
        onError: (err) => {
          setTestResult({
            success: false,
            message: err instanceof Error ? err.message : "Failed to test connection",
          });
          setConnectionTested(false);
        },
      }
    );
  };

  const handleSave = async () => {
    const isValid = await validateForm();
    if (!isValid) {
      return;
    }

    if (mode === "create" && !connectionTested) {
      setTestResult({
        success: false,
        message: "Please test the connection before saving",
      });
      return;
    }

    if (mode === "edit" && values.api_key.trim() && !connectionTested) {
      setTestResult({
        success: false,
        message: "Please test the connection before saving",
      });
      return;
    }

    const normalizedUrl = normalizeHostUrl(values.host_url);

    if (mode === "create") {
      const createData: RagProviderConfigurationRequest = {
        name: values.name,
        description: values.description || undefined,
        authentication_config: {
          authentication_method: "api_key" as const,
          host_url: normalizedUrl,
          api_key: values.api_key,
          rag_provider: "weaviate" as const,
        },
      };

      createProvider.mutate(
        { taskId, data: createData },
        {
          onSuccess: () => {
            onSuccess();
            onClose();
          },
          onError: (err) => {
            setTestResult({
              success: false,
              message: err instanceof Error ? err.message : "Failed to save provider",
            });
          },
        }
      );
    } else if (initialData) {
      const updateData: RagProviderConfigurationUpdateRequest = {
        name: values.name,
        description: values.description || null,
      };

      if (values.api_key.trim() || normalizedUrl !== initialData.authentication_config.host_url) {
        updateData.authentication_config = {
          host_url: normalizedUrl,
          rag_provider: "weaviate",
        };

        if (values.api_key.trim()) {
          updateData.authentication_config.api_key = values.api_key;
        }
      }

      updateProvider.mutate(
        { providerId: initialData.id, data: updateData },
        {
          onSuccess: () => {
            onSuccess();
            onClose();
          },
          onError: (err) => {
            setTestResult({
              success: false,
              message: err instanceof Error ? err.message : "Failed to save provider",
            });
          },
        }
      );
    }
  };

  const canSave = mode === "edit" ? isFormValid && (connectionTested || !values.api_key.trim()) : isFormValid && connectionTested;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth TransitionProps={{ onEnter: handleModalEnter }}>
      <DialogTitle>{mode === "create" ? "Create RAG Provider" : "Edit RAG Provider"}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <form.Field name="name" validators={fieldValidators.name}>
            {(field) => (
              <TextField
                label="Name"
                value={field.state.value}
                onChange={(event) => field.handleChange(event.target.value)}
                onBlur={field.handleBlur}
                required
                fullWidth
                error={field.state.meta.errors.length > 0}
                helperText={field.state.meta.errors[0]}
                placeholder="My RAG Provider"
              />
            )}
          </form.Field>

          <form.Field name="description" validators={fieldValidators.description}>
            {(field) => (
              <TextField
                label="Description"
                value={field.state.value}
                onChange={(event) => field.handleChange(event.target.value)}
                onBlur={field.handleBlur}
                fullWidth
                multiline
                rows={3}
                error={field.state.meta.errors.length > 0}
                helperText={field.state.meta.errors[0]}
                placeholder="Optional description for this provider"
              />
            )}
          </form.Field>

          <form.Field name="host_url" validators={fieldValidators.host_url}>
            {(field) => (
              <TextField
                label="Host URL"
                value={field.state.value}
                onChange={(event) => {
                  field.handleChange(event.target.value);
                  setConnectionTested(false);
                  setTestResult(null);
                }}
                onBlur={field.handleBlur}
                required
                fullWidth
                error={field.state.meta.errors.length > 0}
                helperText={field.state.meta.errors[0] || "Enter with or without https://"}
                placeholder="your-cluster.example.com"
              />
            )}
          </form.Field>

          <form.Field name="api_key" validators={fieldValidators.api_key}>
            {(field) => (
              <TextField
                label="API Key"
                value={field.state.value}
                onChange={(event) => {
                  field.handleChange(event.target.value);
                  setConnectionTested(false);
                  setTestResult(null);
                }}
                onBlur={field.handleBlur}
                required={mode === "create"}
                fullWidth
                type="password"
                error={field.state.meta.errors.length > 0}
                helperText={mode === "edit" ? field.state.meta.errors[0] || "Leave blank to keep existing API key" : field.state.meta.errors[0]}
                placeholder={mode === "edit" ? "(unchanged)" : ""}
              />
            )}
          </form.Field>

          <TextField label="Provider Type" value="Weaviate" disabled fullWidth helperText="Currently only Weaviate is supported" />

          <Button
            variant="outlined"
            onClick={handleTestConnection}
            disabled={!isFormValid || isTesting}
            startIcon={isTesting ? <CircularProgress size={20} /> : null}
            fullWidth
          >
            {isTesting ? "Testing Connection..." : "Test Connection"}
          </Button>

          {testResult && <Alert severity={testResult.success ? "success" : "error"}>{testResult.message}</Alert>}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isSaving}>
          Cancel
        </Button>
        <Button onClick={handleSave} variant="contained" disabled={!canSave || isSaving} startIcon={isSaving ? <CircularProgress size={20} /> : null}>
          {isSaving ? "Saving..." : "Save"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
