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
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { ColumnDef, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import React, { useCallback, useMemo, useState } from "react";

import { RagProviderFormModal } from "@/components/rag/RagProviderFormModal";
import { RagProvidersEmptyState } from "@/components/rag/RagProvidersEmptyState";
import { RagProvidersErrorState } from "@/components/rag/RagProvidersErrorState";
import { RagProvidersLoadingState } from "@/components/rag/RagProvidersLoadingState";
import { useRagProviderMutations } from "@/hooks/rag/useRagProviderMutations";
import { useRagProviders } from "@/hooks/rag/useRagProviders";
import type { RagProviderConfigurationResponse } from "@/lib/api-client/api-client";
import { formatDate } from "@/utils/formatters";

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

  const handleOpenCreateModal = useCallback(() => {
    setCreateModalOpen(true);
  }, []);

  const handleCloseCreateModal = useCallback(() => {
    setCreateModalOpen(false);
  }, []);

  const handleOpenEditModal = useCallback((provider: RagProviderConfigurationResponse) => {
    setEditingProvider(provider);
  }, []);

  const handleCloseEditModal = useCallback(() => {
    setEditingProvider(null);
  }, []);

  const handleOpenDeleteModal = useCallback((provider: RagProviderConfigurationResponse) => {
    setDeletingProvider(provider);
    setDeleteModalOpen(true);
  }, []);

  const handleCloseDeleteModal = useCallback(() => {
    setDeleteModalOpen(false);
    setDeletingProvider(null);
  }, []);

  const handleConfirmDelete = useCallback(() => {
    if (!deletingProvider) return;

    deleteProvider.mutate(
      { providerId: deletingProvider.id },
      {
        onSuccess: () => {
          handleCloseDeleteModal();
        },
      }
    );
  }, [deleteProvider, deletingProvider, handleCloseDeleteModal]);

  const handleSuccess = useCallback(() => {
    refetch();
  }, [refetch]);

  const columns = useMemo<ColumnDef<RagProviderConfigurationResponse>[]>(() => {
    return [
      {
        header: "Name",
        accessorKey: "name",
        cell: ({ row }) => {
          const provider = row.original;
          return (
            <Box>
              <Typography variant="body2" fontWeight="medium">
                {provider.name}
              </Typography>
              {provider.description && (
                <Typography variant="caption" color="text.secondary">
                  {provider.description}
                </Typography>
              )}
            </Box>
          );
        },
      },
      {
        header: "Host URL",
        accessorFn: (provider) => provider.authentication_config.host_url,
        cell: ({ row }) => (
          <Typography
            variant="body2"
            sx={{
              fontFamily: "monospace",
              fontSize: "0.75rem",
            }}
          >
            {row.original.authentication_config.host_url}
          </Typography>
        ),
      },
      {
        header: "Provider",
        accessorFn: (provider) => provider.authentication_config.rag_provider,
        cell: ({ row }) => <Typography variant="body2">{row.original.authentication_config.rag_provider}</Typography>,
      },
      {
        header: "Created",
        accessorKey: "created_at",
        cell: ({ row }) => (
          <Typography variant="body2" color="text.secondary">
            {formatDate(new Date(row.original.created_at).toISOString())}
          </Typography>
        ),
      },
      {
        id: "actions",
        header: "Actions",
        meta: { align: "right" },
        cell: ({ row }) => (
          <>
            <IconButton size="small" onClick={() => handleOpenEditModal(row.original)} title="Edit provider">
              <Edit fontSize="small" />
            </IconButton>
            <IconButton size="small" onClick={() => handleOpenDeleteModal(row.original)} title="Delete provider" color="error">
              <Delete fontSize="small" />
            </IconButton>
          </>
        ),
      },
    ];
  }, [handleOpenDeleteModal, handleOpenEditModal]);

  const providerRows = providers ?? [];

  const table = useReactTable({
    data: providerRows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const tableAlign = (id: string) => {
    const column = table.getAllLeafColumns().find((col) => col.id === id);
    return (column?.columnDef.meta as { align?: "left" | "right" | "center" })?.align ?? "left";
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
          {isLoading && providerRows.length === 0 ? (
            <RagProvidersLoadingState />
          ) : error && providerRows.length === 0 ? (
            <RagProvidersErrorState error={error} onRetry={refetch} />
          ) : providerRows.length === 0 ? (
            <RagProvidersEmptyState />
          ) : (
            <TableContainer component={Paper} sx={{ boxShadow: 0, border: 1, borderColor: "divider" }}>
              <Table size="small">
                <TableHead>
                  {table.getHeaderGroups().map((headerGroup) => (
                    <TableRow key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <TableCell key={header.id} align={tableAlign(header.column.id)}>
                          {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableHead>
                <TableBody>
                  {table.getRowModel().rows.map((row) => (
                    <TableRow key={row.id}>
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id} align={tableAlign(cell.column.id)}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                      ))}
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
