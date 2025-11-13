import { Alert, Box, Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, TextField } from "@mui/material";
import React, { useState } from "react";

import { useProviderForm } from "@/hooks/rag/useProviderForm";
import { useRagProviderMutations } from "@/hooks/rag/useRagProviderMutations";
import type { RagProviderConfigurationRequest, RagProviderConfigurationResponse, RagProviderConfigurationUpdateRequest } from "@/lib/api-client/api-client";

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
  const { formData, errors, isFormValid, updateField, validateForm, resetForm, normalizeHostUrl } = useProviderForm(mode, initialData);
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

  const handleChange = (field: "name" | "description" | "host_url" | "api_key") => (event: React.ChangeEvent<HTMLInputElement>) => {
    updateField(field, event.target.value);
    if (field === "host_url" || field === "api_key") {
      setConnectionTested(false);
      setTestResult(null);
    }
  };

  const handleTestConnection = async () => {
    if (!validateForm()) {
      return;
    }

    setTestResult(null);

    const normalizedUrl = normalizeHostUrl(formData.host_url);

    const testData = {
      authentication_config: {
        authentication_method: "api_key" as const,
        host_url: normalizedUrl,
        api_key: formData.api_key,
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
    if (!validateForm()) {
      return;
    }

    if (mode === "create" && !connectionTested) {
      setTestResult({
        success: false,
        message: "Please test the connection before saving",
      });
      return;
    }

    if (mode === "edit" && formData.api_key.trim() && !connectionTested) {
      setTestResult({
        success: false,
        message: "Please test the connection before saving",
      });
      return;
    }

    const normalizedUrl = normalizeHostUrl(formData.host_url);

    if (mode === "create") {
      const createData: RagProviderConfigurationRequest = {
        name: formData.name,
        description: formData.description || undefined,
        authentication_config: {
          authentication_method: "api_key" as const,
          host_url: normalizedUrl,
          api_key: formData.api_key,
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
        name: formData.name,
        description: formData.description || null,
      };

      if (formData.api_key.trim() || normalizedUrl !== initialData.authentication_config.host_url) {
        updateData.authentication_config = {
          host_url: normalizedUrl,
          rag_provider: "weaviate",
        };

        if (formData.api_key.trim()) {
          updateData.authentication_config.api_key = formData.api_key;
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

  const canSave = mode === "edit" ? isFormValid && (connectionTested || !formData.api_key.trim()) : isFormValid && connectionTested;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth TransitionProps={{ onEnter: handleModalEnter }}>
      <DialogTitle>{mode === "create" ? "Create RAG Provider" : "Edit RAG Provider"}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            label="Name"
            value={formData.name}
            onChange={handleChange("name")}
            required
            fullWidth
            error={!!errors.name}
            helperText={errors.name}
            placeholder="My RAG Provider"
          />

          <TextField
            label="Description"
            value={formData.description}
            onChange={handleChange("description")}
            fullWidth
            multiline
            rows={3}
            error={!!errors.description}
            helperText={errors.description}
            placeholder="Optional description for this provider"
          />

          <TextField
            label="Host URL"
            value={formData.host_url}
            onChange={handleChange("host_url")}
            required
            fullWidth
            error={!!errors.host_url}
            helperText={errors.host_url || "Enter with or without https://"}
            placeholder="your-cluster.example.com"
          />

          <TextField
            label="API Key"
            value={formData.api_key}
            onChange={handleChange("api_key")}
            required={mode === "create"}
            fullWidth
            type="password"
            error={!!errors.api_key}
            helperText={mode === "edit" ? errors.api_key || "Leave blank to keep existing API key" : errors.api_key}
            placeholder={mode === "edit" ? "(unchanged)" : ""}
          />

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
