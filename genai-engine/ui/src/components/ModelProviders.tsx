import { Edit, Delete, Warning } from "@mui/icons-material";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
} from "@mui/material";
import React, { useState, useEffect } from "react";

import { useApi } from "@/hooks/useApi";
import { ModelProviderResponse } from "@/lib/api-client/api-client";

export const ModelProviders: React.FC = () => {
  const api = useApi();
  const [providers, setProviders] = useState<ModelProviderResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteModal, setDeleteModal] = useState<{
    isOpen: boolean;
    provider: ModelProviderResponse | null;
  }>({ isOpen: false, provider: null });
  const [isDeleting, setIsDeleting] = useState(false);
  const [editModal, setEditModal] = useState<{
    isOpen: boolean;
    provider: ModelProviderResponse | null;
  }>({ isOpen: false, provider: null });
  const [apiKey, setApiKey] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const fetchModelProviders = async () => {
      try {
        setIsLoading(true);
        setError(null);

        if (!api) {
          throw new Error("API client not available");
        }

        const response =
          await api.api.getModelProvidersApiV1ModelProvidersGet();
        setProviders(response.data.providers || []);
      } catch (err) {
        console.error("Failed to fetch model providers:", err);
        setError(
          "Failed to load model providers. Please check your authentication."
        );
      } finally {
        setIsLoading(false);
      }
    };

    if (api) {
      fetchModelProviders();
    }
  }, [api]);

  const getProviderDisplayName = (provider: string): string => {
    const displayNames: Record<string, string> = {
      anthropic: "Anthropic",
      openai: "OpenAI",
      gemini: "Google Gemini",
    };
    return (
      displayNames[provider] ||
      provider.charAt(0).toUpperCase() + provider.slice(1)
    );
  };

  const getStatusBadge = (enabled: boolean) => {
    if (enabled) {
      return (
        <Chip label="Enabled" color="success" size="small" variant="filled" />
      );
    } else {
      return (
        <Chip label="Disabled" color="error" size="small" variant="filled" />
      );
    }
  };

  const handleDeleteClick = (provider: ModelProviderResponse) => {
    setDeleteModal({ isOpen: true, provider });
  };

  const handleDeleteConfirm = async () => {
    if (!deleteModal.provider || !api) return;

    try {
      setIsDeleting(true);
      await api.api.setModelProviderApiV1ModelProvidersProviderDelete(
        deleteModal.provider.provider
      );

      // Refresh the providers list
      const response = await api.api.getModelProvidersApiV1ModelProvidersGet();
      setProviders(response.data.providers || []);

      // Close modal
      setDeleteModal({ isOpen: false, provider: null });
    } catch (err) {
      console.error("Failed to delete model provider:", err);
      setError("Failed to delete model provider. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteModal({ isOpen: false, provider: null });
  };

  const handleEditClick = (provider: ModelProviderResponse) => {
    setEditModal({ isOpen: true, provider });
    setApiKey(""); // Clear the API key field when opening
  };

  const handleEditSave = async () => {
    if (!editModal.provider || !api || !apiKey.trim()) return;

    try {
      setIsSaving(true);
      await api.api.setModelProviderApiV1ModelProvidersProviderPut(
        editModal.provider.provider,
        { api_key: apiKey.trim() }
      );

      // Refresh the providers list
      const response = await api.api.getModelProvidersApiV1ModelProvidersGet();
      setProviders(response.data.providers || []);

      // Close modal and clear form
      setEditModal({ isOpen: false, provider: null });
      setApiKey("");
    } catch (err) {
      console.error("Failed to save model provider:", err);
      setError(
        "Failed to save model provider configuration. Please try again."
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleEditCancel = () => {
    setEditModal({ isOpen: false, provider: null });
    setApiKey("");
  };

  if (isLoading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: 256,
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        <Typography variant="h6">Error loading model providers</Typography>
        <Typography>{error}</Typography>
      </Alert>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 3 }}>
        <Typography
          variant="h5"
          component="h2"
          gutterBottom
          color="text.primary"
          fontWeight="bold"
        >
          Model Providers Configuration
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage and configure model providers to use LLM features.
        </Typography>
      </Box>

      <Card>
        <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
          <TableContainer
            sx={{ maxHeight: "calc(100vh - 200px)", overflow: "auto" }}
          >
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  <TableCell
                    sx={{ fontWeight: "bold", backgroundColor: "grey.100" }}
                  >
                    Provider
                  </TableCell>
                  <TableCell
                    sx={{ fontWeight: "bold", backgroundColor: "grey.100" }}
                  >
                    Status
                  </TableCell>
                  <TableCell
                    sx={{ fontWeight: "bold", backgroundColor: "grey.100" }}
                  >
                    Actions
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {providers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={3} align="center">
                      <Typography variant="body2" color="text.secondary">
                        No model providers found
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  providers.map((provider) => (
                    <TableRow key={provider.provider} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {getProviderDisplayName(provider.provider)}
                        </Typography>
                      </TableCell>
                      <TableCell>{getStatusBadge(provider.enabled)}</TableCell>
                      <TableCell>
                        <Box sx={{ display: "flex", gap: 1 }}>
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleEditClick(provider)}
                            title="Configure provider"
                          >
                            <Edit />
                          </IconButton>
                          {provider.enabled && (
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDeleteClick(provider)}
                              title="Delete provider"
                            >
                              <Delete />
                            </IconButton>
                          )}
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Delete Confirmation Modal */}
      <Dialog
        open={deleteModal.isOpen}
        onClose={handleDeleteCancel}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ textAlign: "center", pb: 1 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              mb: 2,
            }}
          >
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: "50%",
                bgcolor: "error.light",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Warning sx={{ color: "error.main", fontSize: 24 }} />
            </Box>
          </Box>
          Delete Model Provider
        </DialogTitle>
        <DialogContent sx={{ textAlign: "center" }}>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Are you sure you want to delete{" "}
            <Typography component="span" fontWeight="bold">
              {getProviderDisplayName(deleteModal.provider?.provider || "")}
            </Typography>
            ?
          </Typography>
          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography variant="body2">
              Any agents or evals currently using this provider will no longer
              work.
            </Typography>
          </Alert>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button
            onClick={handleDeleteCancel}
            disabled={isDeleting}
            variant="outlined"
          >
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            disabled={isDeleting}
            color="error"
            variant="contained"
            startIcon={isDeleting ? <CircularProgress size={16} /> : null}
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit/Configure Modal */}
      <Dialog
        open={editModal.isOpen}
        onClose={handleEditCancel}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ textAlign: "center", pb: 1 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              mb: 2,
            }}
          >
            <Box
              sx={{
                width: 48,
                height: 48,
                borderRadius: "50%",
                bgcolor: "primary.light",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Edit sx={{ color: "primary.main", fontSize: 24 }} />
            </Box>
          </Box>
          Configure {getProviderDisplayName(editModal.provider?.provider || "")}
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            id="apiKey"
            label="API Key"
            type="password"
            fullWidth
            variant="outlined"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Enter your API key..."
            disabled={isSaving}
            helperText={`Your API key will be securely stored and used to authenticate with ${getProviderDisplayName(
              editModal.provider?.provider || ""
            )}.`}
          />
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button
            onClick={handleEditCancel}
            disabled={isSaving}
            variant="outlined"
          >
            Cancel
          </Button>
          <Button
            onClick={handleEditSave}
            disabled={isSaving || !apiKey.trim()}
            variant="contained"
            startIcon={isSaving ? <CircularProgress size={16} /> : null}
          >
            {isSaving ? "Saving..." : "Save"}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};
