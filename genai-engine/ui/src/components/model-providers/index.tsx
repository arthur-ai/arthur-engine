import { Edit, Delete, Warning, SmartToy } from "@mui/icons-material";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
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
  Typography,
  Alert,
  Stack,
} from "@mui/material";
import React, { useState } from "react";

import { EditForm } from "./components/edit-form";
import { useProviders } from "./hooks/useProviders";
import { useRemoveProvider } from "./hooks/useRemoveProvider";
import { useSaveProvider } from "./hooks/useSaveProvider";

import { getContentHeight } from "@/constants/layout";
import { ModelProviderResponse, PutModelProviderCredentials } from "@/lib/api-client/api-client";
import { EVENT_NAMES, track } from "@/services/amplitude";

export const ModelProviders: React.FC = () => {
  const { data: providers, isLoading, error } = useProviders();
  const [deleteModal, setDeleteModal] = useState<{
    isOpen: boolean;
    provider: ModelProviderResponse | null;
  }>({ isOpen: false, provider: null });

  const [editModal, setEditModal] = useState<{
    isOpen: boolean;
    provider: ModelProviderResponse | null;
  }>({ isOpen: false, provider: null });

  const saveProviderMutation = useSaveProvider({
    onSuccess: async () => {
      setEditModal({ isOpen: false, provider: null });
    },
  });

  const deleteProviderMutation = useRemoveProvider({
    onSuccess: async () => {
      setDeleteModal({ isOpen: false, provider: null });
    },
  });

  const handleDeleteClick = (provider: ModelProviderResponse) => {
    track(EVENT_NAMES.MODEL_PROVIDER_DELETE_INTENT, { provider_name: provider.provider });
    setDeleteModal({ isOpen: true, provider });
  };

  const handleDeleteConfirm = async () => {
    if (!deleteModal.provider) return;

    deleteProviderMutation.mutate(deleteModal.provider.provider);
  };

  const handleDeleteCancel = () => {
    setDeleteModal({ isOpen: false, provider: null });
  };

  const handleEditClick = (provider: ModelProviderResponse) => {
    track(EVENT_NAMES.MODEL_PROVIDER_CONFIGURE_OPENED, { provider_name: provider.provider });
    setEditModal({ isOpen: true, provider });
  };

  const handleEditSave = async (data: PutModelProviderCredentials) => {
    if (!editModal.provider) return;

    await saveProviderMutation.mutateAsync({ provider: editModal.provider, data });
  };

  const handleEditCancel = () => {
    setEditModal({ isOpen: false, provider: null });
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

  const isDeleting = deleteProviderMutation.isPending;

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        <Typography variant="h6">Error loading model providers</Typography>
        <Typography>{error.message}</Typography>
      </Alert>
    );
  }

  return (
    <>
      <Stack sx={{ height: getContentHeight() }}>
        <Box
          sx={{
            px: 3,
            pt: 3,
            pb: 2,
            borderBottom: 1,
            borderColor: "divider",
            backgroundColor: "background.paper",
          }}
        >
          <Typography variant="h5" color="text.primary" fontWeight="bold">
            Model Providers Configuration
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage and configure model providers to use LLM features.
          </Typography>
        </Box>

        <Card>
          <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
            <TableContainer sx={{ maxHeight: "calc(100vh - 200px)", overflow: "auto" }}>
              <Table stickyHeader size="small" sx={{ width: "100%" }}>
                <TableHead>
                  <TableRow>
                    <TableCell
                      sx={{
                        fontWeight: "bold",
                        backgroundColor: (theme) => (theme.palette.mode === "dark" ? "background.paper" : "grey.100"),
                        width: "33.33%",
                      }}
                    >
                      Provider
                    </TableCell>
                    <TableCell
                      sx={{
                        fontWeight: "bold",
                        backgroundColor: (theme) => (theme.palette.mode === "dark" ? "background.paper" : "grey.100"),
                        width: "33.33%",
                      }}
                      align="center"
                    >
                      Status
                    </TableCell>
                    <TableCell
                      sx={{
                        fontWeight: "bold",
                        backgroundColor: (theme) => (theme.palette.mode === "dark" ? "background.paper" : "grey.100"),
                        width: "33.33%",
                      }}
                      align="right"
                    >
                      Actions
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {providers?.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3} align="center">
                        <Typography variant="body2" color="text.secondary">
                          No model providers found
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    providers?.map((provider) => (
                      <TableRow key={provider.provider} hover>
                        <TableCell>
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                            {getProviderIcon(provider.provider)}
                            <Typography variant="body2" fontWeight="medium">
                              {getProviderDisplayName(provider.provider)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell align="center">{getStatusBadge(provider.enabled)}</TableCell>
                        <TableCell align="right">
                          <Box
                            sx={{
                              display: "flex",
                              gap: 1,
                              justifyContent: "flex-end",
                            }}
                          >
                            <IconButton size="small" color="primary" onClick={() => handleEditClick(provider)} title="Configure provider">
                              <Edit />
                            </IconButton>
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDeleteClick(provider)}
                              disabled={!provider.enabled}
                              title={provider.enabled ? "Delete provider" : "Delete provider (disabled - provider not enabled)"}
                            >
                              <Delete />
                            </IconButton>
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
      </Stack>
      {/* Delete Confirmation Modal */}
      <Dialog open={deleteModal.isOpen} onClose={handleDeleteCancel} maxWidth="sm" fullWidth>
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
            <Typography variant="body2">Any agents or evals currently using this provider will no longer work.</Typography>
          </Alert>
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button onClick={handleDeleteCancel} disabled={isDeleting} variant="outlined">
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
      <Dialog open={editModal.isOpen} onClose={handleEditCancel} maxWidth="sm" fullWidth>
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
        {editModal.provider?.provider && <EditForm provider={editModal.provider.provider} onSubmit={handleEditSave} onClose={handleEditCancel} />}
      </Dialog>
    </>
  );
};

const getProviderDisplayName = (provider: string): string => {
  const displayNames: Record<string, string> = {
    anthropic: "Anthropic",
    openai: "OpenAI",
    gemini: "Google Gemini",
    vertex_ai: "Vertex AI",
    bedrock: "Amazon Bedrock",
    hosted_vllm: "vLLM",
  };
  return displayNames[provider] || provider.charAt(0).toUpperCase() + provider.slice(1);
};

const getProviderIcon = (provider: string) => {
  const iconMap: Record<string, React.ReactElement> = {
    anthropic: <img src="/logos/model_providers/anthropic-logo.svg" alt="Anthropic" style={{ width: 20, height: 20 }} />,
    openai: <img src="/logos/model_providers/openai-logo.svg" alt="OpenAI" style={{ width: 20, height: 20 }} />,
    gemini: <img src="/logos/model_providers/gemini-logo.svg" alt="Google Gemini" style={{ width: 20, height: 20 }} />,
    vertex_ai: <img src="/logos/model_providers/vertex-logo.svg" alt="Google Vertex AI" style={{ width: 20, height: 20 }} />,
    bedrock: <img src="/logos/model_providers/bedrock-logo.svg" alt="Amazon Bedrock" style={{ width: 20, height: 20 }} />,
    hosted_vllm: <img src="/logos/model_providers/vllm-logo.svg" alt="vLLM" style={{ width: 20, height: 20 }} />,
  };
  return iconMap[provider] || <SmartToy sx={{ color: "primary.main" }} />;
};

const getStatusBadge = (enabled: boolean) => {
  if (enabled) {
    return (
      <Chip
        label="Enabled"
        size="small"
        variant="filled"
        sx={{
          backgroundColor: "primary.main",
          color: "white",
          "& .MuiChip-label": { fontWeight: "medium" },
        }}
      />
    );
  } else {
    return (
      <Chip
        label="Disabled"
        size="small"
        variant="outlined"
        sx={{
          borderColor: "grey.400",
          color: "grey.600",
          "& .MuiChip-label": { fontWeight: "medium" },
        }}
      />
    );
  }
};
