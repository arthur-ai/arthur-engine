import AddIcon from "@mui/icons-material/Add";
import StorageOutlinedIcon from "@mui/icons-material/StorageOutlined";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import TablePagination from "@mui/material/TablePagination";
import Typography from "@mui/material/Typography";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import DeleteTransformDialog from "./DeleteTransformDialog";
import TransformFullScreenView from "./fullscreen/TransformFullScreenView";
import { useCreateTransformMutation } from "./hooks/useCreateTransformMutation";
import { useDeleteTransformMutation } from "./hooks/useDeleteTransformMutation";
import { useImpactedTransformContinuousEvals } from "./hooks/useImpactedTransformContinuousEvals";
import { useUpdateTransformMutation } from "./hooks/useUpdateTransformMutation";
import TransformsTable from "./table/TransformsTable";
import TransformFormModal from "./TransformFormModal";
import TransformImpactedCEsDialog from "./TransformImpactedCEsDialog";
import TransformsHeader from "./TransformsHeader";
import { TraceTransform } from "./types";

import { TransformDefinition } from "@/components/traces/components/add-to-dataset/form/shared";
import { getContentHeight } from "@/constants/layout";
import { useTransforms } from "@/hooks/transforms/useTransforms";
import { usePagination } from "@/hooks/usePagination";
import type { ContinuousEvalResponse } from "@/lib/api-client/api-client";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const TransformsManagement: React.FC = () => {
  const pagination = usePagination();
  const { id: taskId, transformId: urlTransformId, versionId: urlVersionId } = useParams<{ id: string; transformId?: string; versionId?: string }>();
  const navigate = useNavigate();
  const [sortColumn, setSortColumn] = useState<string | null>("updated_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingTransform, setEditingTransform] = useState<TraceTransform | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [fullScreenTransformId, setFullScreenTransformId] = useState<string | null>(urlTransformId ?? null);
  const [editKey, setEditKey] = useState(0);
  const [impactedCEs, setImpactedCEs] = useState<ContinuousEvalResponse[]>([]);
  const [impactedTransformName, setImpactedTransformName] = useState("");
  const [isImpactedDialogOpen, setIsImpactedDialogOpen] = useState(false);

  // Sync fullScreenTransformId with URL parameter
  useEffect(() => {
    if (urlTransformId) {
      setFullScreenTransformId(urlTransformId);
    } else if (!urlTransformId && fullScreenTransformId) {
      setFullScreenTransformId(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlTransformId]);

  const { data, error, isLoading, refetch } = useTransforms({ page: pagination.page, page_size: pagination.rowsPerPage });

  const transforms = useMemo(() => data?.transforms ?? [], [data]);

  const { fetchImpactedCEs } = useImpactedTransformContinuousEvals(taskId);

  const createMutation = useCreateTransformMutation(taskId, () => {
    setIsCreateModalOpen(false);
    refetch();
  });

  const updateMutation = useUpdateTransformMutation(taskId, () => {
    setEditingTransform(null);
    setEditKey((prev) => prev + 1);
    refetch();
  });

  const deleteMutation = useDeleteTransformMutation(taskId, () => {
    setDeleteConfirmId(null);
    refetch();
  });

  const sortedTransforms = useMemo(() => {
    if (!transforms) return [];

    const sorted = [...transforms];
    if (sortColumn) {
      sorted.sort((a, b) => {
        const aVal = a[sortColumn as keyof TraceTransform];
        const bVal = b[sortColumn as keyof TraceTransform];

        let aCompare: string | number = aVal as string | number;
        let bCompare: string | number = bVal as string | number;

        if (sortColumn === "name") {
          aCompare = String(aVal || "").toLowerCase();
          bCompare = String(bVal || "").toLowerCase();
        }

        if (aCompare < bCompare) return sortDirection === "asc" ? -1 : 1;
        if (aCompare > bCompare) return sortDirection === "asc" ? 1 : -1;
        return 0;
      });
    }
    return sorted;
  }, [transforms, sortColumn, sortDirection]);

  const handleCreateTransform = useCallback(
    async (name: string, description: string, definition: TransformDefinition) => {
      await createMutation.mutateAsync({ name, description, definition });
    },
    [createMutation]
  );

  const handleUpdateTransform = useCallback(
    async (name: string, description: string, definition: TransformDefinition) => {
      if (!editingTransform) return;
      await updateMutation.mutateAsync({
        transformId: editingTransform.id,
        name,
        description,
        definition,
      });

      try {
        const affected = await fetchImpactedCEs(editingTransform.id);
        if (affected.length > 0) {
          setImpactedCEs(affected);
          setImpactedTransformName(name);
          setIsImpactedDialogOpen(true);
        }
      } catch {
        // Non-critical — don't block the save flow if the check fails
      }
    },
    [editingTransform, updateMutation, fetchImpactedCEs]
  );

  const handleView = useCallback(
    (transform: TraceTransform) => {
      navigate(`/tasks/${taskId}/transforms/${transform.id}`);
    },
    [taskId, navigate]
  );

  const handleEdit = useCallback((transform: TraceTransform) => {
    setEditingTransform(transform);
  }, []);

  const handleCloseFullScreen = useCallback(() => {
    setFullScreenTransformId(null);
    navigate(`/tasks/${taskId}/transforms`);
  }, [taskId, navigate]);

  const handleDelete = useCallback((transformId: string) => {
    setDeleteConfirmId(transformId);
  }, []);

  const handleConfirmDelete = useCallback(async () => {
    if (deleteConfirmId) {
      await deleteMutation.mutateAsync(deleteConfirmId);
    }
  }, [deleteConfirmId, deleteMutation]);

  const handleSort = useCallback(
    (column: string) => {
      if (sortColumn === column) {
        setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
      } else {
        setSortColumn(column);
        setSortDirection("desc");
      }
    },
    [sortColumn]
  );

  if (fullScreenTransformId) {
    return (
      <Box sx={{ height: getContentHeight(), overflow: "hidden" }}>
        <TransformFullScreenView
          transformId={fullScreenTransformId}
          initialVersionId={urlVersionId ?? null}
          editKey={editKey}
          onClose={handleCloseFullScreen}
          onEdit={handleEdit}
        />
        <TransformFormModal
          open={!!editingTransform}
          onClose={() => setEditingTransform(null)}
          onSubmit={handleUpdateTransform}
          isLoading={updateMutation.isPending}
          taskId={taskId}
          initialTransform={editingTransform || undefined}
        />
        <TransformImpactedCEsDialog
          open={isImpactedDialogOpen}
          onClose={() => setIsImpactedDialogOpen(false)}
          impactedCEs={impactedCEs}
          transformName={impactedTransformName}
        />
      </Box>
    );
  }

  if (isLoading && !transforms) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: getContentHeight(),
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error && !transforms) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" onClose={() => refetch()}>
          {error.message || "Failed to load transforms"}
        </Alert>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        width: "100%",
        height: getContentHeight(),
        display: "grid",
        gridTemplateRows: "auto auto 1fr auto",
        overflow: "hidden",
      }}
    >
      <TransformsHeader onCreateTransform={() => setIsCreateModalOpen(true)} />

      {error && transforms && transforms.length > 0 && (
        <Box sx={{ px: 3, pt: 2 }}>
          <Alert severity="error">{error?.message || "An error occurred"}</Alert>
        </Box>
      )}

      <Box
        sx={{
          overflow: "auto",
          minHeight: 0,
        }}
      >
        {!isLoading && (!transforms || transforms.length === 0) ? (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              textAlign: "center",
              py: 8,
            }}
          >
            <StorageOutlinedIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
            <Typography variant="h5" gutterBottom sx={{ fontWeight: 500, color: "text.primary" }}>
              No transforms yet
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Get started by creating your first transform
            </Typography>
            <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setIsCreateModalOpen(true)} size="large">
              Transform
            </Button>
          </Box>
        ) : (
          <TransformsTable
            transforms={sortedTransforms}
            sortColumn={sortColumn}
            sortDirection={sortDirection}
            onSort={handleSort}
            onView={handleView}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        )}
      </Box>

      {transforms && transforms.length > 0 && (
        <Box
          sx={{
            borderTop: 1,
            borderColor: "divider",
            backgroundColor: "background.paper",
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <TablePagination
            component="div"
            count={sortedTransforms.length}
            page={pagination.page}
            onPageChange={pagination.handlePageChange}
            rowsPerPage={pagination.rowsPerPage}
            onRowsPerPageChange={pagination.handleRowsPerPageChange}
            rowsPerPageOptions={PAGE_SIZE_OPTIONS}
          />
        </Box>
      )}

      <TransformFormModal
        open={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateTransform}
        isLoading={createMutation.isPending}
        taskId={taskId}
      />

      <TransformFormModal
        open={!!editingTransform}
        onClose={() => setEditingTransform(null)}
        onSubmit={handleUpdateTransform}
        isLoading={updateMutation.isPending}
        taskId={taskId}
        initialTransform={editingTransform || undefined}
      />

      <DeleteTransformDialog
        transformId={deleteConfirmId}
        onClose={() => setDeleteConfirmId(null)}
        onConfirm={handleConfirmDelete}
        isDeleting={deleteMutation.isPending}
      />

      <TransformImpactedCEsDialog
        open={isImpactedDialogOpen}
        onClose={() => setIsImpactedDialogOpen(false)}
        impactedCEs={impactedCEs}
        transformName={impactedTransformName}
      />
    </Box>
  );
};

export default TransformsManagement;
