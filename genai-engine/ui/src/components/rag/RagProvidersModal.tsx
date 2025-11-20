import { Delete, Edit, Add, Close } from "@mui/icons-material";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Paper,
} from "@mui/material";
import React, { useState } from "react";

import { RagProviderFormModal } from "@/components/rag/RagProviderFormModal";
import { RagProvidersEmptyState } from "@/components/rag/RagProvidersEmptyState";
import { RagProvidersErrorState } from "@/components/rag/RagProvidersErrorState";
import { RagProvidersLoadingState } from "@/components/rag/RagProvidersLoadingState";
import { useRagProviderMutations } from "@/hooks/rag/useRagProviderMutations";
import { useRagProviders } from "@/hooks/rag/useRagProviders";
import type { RagProviderConfigurationResponse } from "@/lib/api-client/api-client";

interface RagProvidersModalProps {
  open: boolean;
  onClose: () => void;
  taskId: string;
}

export const RagProvidersModal: React.FC<RagProvidersModalProps> = ({ open, onClose, taskId }) => {
  const { providers, isLoading, error, refetch } = useRagProviders(taskId);
  const { deleteProvider } = useRagProviderMutations();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<RagProviderConfigurationResponse | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deletingProvider, setDeletingProvider] = useState<RagProviderConfigurationResponse | null>(null);

  const isDeleting = deleteProvider.isPending;

  const handleOpenCreateModal = () => {
    setCreateModalOpen(true);
  };

  const handleCloseCreateModal = () => {
    setCreateModalOpen(false);
  };

  const handleOpenEditModal = (provider: RagProviderConfigurationResponse) => {
    setEditingProvider(provider);
  };

  const handleCloseEditModal = () => {
    setEditingProvider(null);
  };

  const handleOpenDeleteModal = (provider: RagProviderConfigurationResponse) => {
    setDeletingProvider(provider);
    setDeleteModalOpen(true);
  };

  const handleCloseDeleteModal = () => {
    setDeleteModalOpen(false);
    setDeletingProvider(null);
  };

  const handleConfirmDelete = () => {
    if (!deletingProvider) return;

    deleteProvider.mutate(
      { providerId: deletingProvider.id },
      {
        onSuccess: () => {
          handleCloseDeleteModal();
        },
      }
    );
  };

  const handleSuccess = () => {
    refetch();
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Box>
              <Typography variant="h6">Manage RAG Providers</Typography>
              <Typography variant="caption" color="text.secondary">
                Configure vector database connections for retrieval-augmented generation
              </Typography>
            </Box>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              {!isLoading && !error && (
                <Button variant="contained" startIcon={<Add />} onClick={handleOpenCreateModal} size="small">
                  Create Provider
                </Button>
              )}
              <IconButton onClick={onClose} size="small">
                <Close />
              </IconButton>
            </Box>
          </Box>
        </DialogTitle>
        <DialogContent>
          {isLoading && providers.length === 0 ? (
            <RagProvidersLoadingState />
          ) : error && providers.length === 0 ? (
            <RagProvidersErrorState error={error} onRetry={refetch} />
          ) : providers.length === 0 ? (
            <RagProvidersEmptyState />
          ) : (
            <TableContainer component={Paper} sx={{ boxShadow: 0, border: 1, borderColor: "divider" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Host URL</TableCell>
                    <TableCell>Provider</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {providers.map((provider) => (
                    <TableRow key={provider.id} sx={{ "&:last-child td, &:last-child th": { border: 0 } }}>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {provider.name}
                        </Typography>
                        {provider.description && (
                          <Typography variant="caption" color="text.secondary">
                            {provider.description}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          sx={{
                            fontFamily: "monospace",
                            fontSize: "0.75rem",
                          }}
                        >
                          {provider.authentication_config.host_url}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{provider.authentication_config.rag_provider}</Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {formatDate(provider.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <IconButton size="small" onClick={() => handleOpenEditModal(provider)} title="Edit provider">
                          <Edit fontSize="small" />
                        </IconButton>
                        <IconButton size="small" onClick={() => handleOpenDeleteModal(provider)} title="Delete provider" color="error">
                          <Delete fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>

      <RagProviderFormModal open={createModalOpen} onClose={handleCloseCreateModal} onSuccess={handleSuccess} taskId={taskId} mode="create" />

      {editingProvider && (
        <RagProviderFormModal
          open={!!editingProvider}
          onClose={handleCloseEditModal}
          onSuccess={handleSuccess}
          taskId={taskId}
          mode="edit"
          initialData={editingProvider}
        />
      )}

      <Dialog open={deleteModalOpen} onClose={handleCloseDeleteModal}>
        <DialogTitle>Delete RAG Provider</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the provider "{deletingProvider?.name}"? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDeleteModal} disabled={isDeleting}>
            Cancel
          </Button>
          <Button onClick={handleConfirmDelete} color="error" variant="contained" disabled={isDeleting}>
            {isDeleting ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
