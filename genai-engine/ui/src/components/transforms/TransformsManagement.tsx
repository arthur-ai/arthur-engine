import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import TablePagination from "@mui/material/TablePagination";
import React, { useCallback, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import { useCreateTransformMutation } from "./hooks/useCreateTransformMutation";
import { useDeleteTransformMutation } from "./hooks/useDeleteTransformMutation";
import { useTransforms } from "./hooks/useTransforms";
import { useUpdateTransformMutation } from "./hooks/useUpdateTransformMutation";
import TransformsTable from "./table/TransformsTable";
import TransformDetailsModal from "./TransformDetailsModal";
import TransformFormModal from "./TransformFormModal";
import TransformsHeader from "./TransformsHeader";
import { TraceTransform } from "./types";

import { TransformDefinition } from "@/components/traces/components/add-to-dataset/form/shared";
import { getContentHeight } from "@/constants/layout";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const TransformsManagement: React.FC = () => {
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [sortColumn, setSortColumn] = useState<string | null>("updated_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingTransform, setEditingTransform] = useState<TraceTransform | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [viewingTransform, setViewingTransform] = useState<TraceTransform | null>(null);

  const { data: transforms, error, isLoading, refetch } = useTransforms(taskId);

  const createMutation = useCreateTransformMutation(taskId, () => {
    setIsCreateModalOpen(false);
    refetch();
  });

  const updateMutation = useUpdateTransformMutation(taskId, () => {
    setEditingTransform(null);
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

  const paginatedTransforms = useMemo(() => {
    const start = page * pageSize;
    return sortedTransforms.slice(start, start + pageSize);
  }, [sortedTransforms, page, pageSize]);

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
    },
    [editingTransform, updateMutation]
  );

  const handleView = useCallback((transform: TraceTransform) => {
    setViewingTransform(transform);
  }, []);

  const handleEdit = useCallback((transform: TraceTransform) => {
    setEditingTransform(transform);
  }, []);

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

  const handlePageChange = useCallback((_event: unknown, newPage: number) => {
    setPage(newPage);
  }, []);

  const handlePageSizeChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setPageSize(parseInt(event.target.value, 10));
    setPage(0);
  }, []);

  const handleBack = useCallback(() => {
    navigate(-1);
  }, [navigate]);

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
      <TransformsHeader onCreateTransform={() => setIsCreateModalOpen(true)} onBack={handleBack} />

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
              alignItems: "center",
              justifyContent: "center",
              flex: 1,
              p: 3,
              minHeight: 400,
            }}
          >
            <Box sx={{ textAlign: "center" }}>
              <Box
                sx={{
                  fontWeight: 600,
                  fontSize: "1.25rem",
                  color: "text.primary",
                  mb: 1,
                }}
              >
                No transforms found
              </Box>
              <Box sx={{ color: "text.secondary", mb: 2 }}>
                Create your first transform to extract data from traces.
              </Box>
              <Button variant="contained" onClick={() => setIsCreateModalOpen(true)} sx={{ mt: 1 }}>
                Create Transform
              </Button>
            </Box>
          </Box>
        ) : (
          <TransformsTable
            transforms={paginatedTransforms}
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
            page={page}
            onPageChange={handlePageChange}
            rowsPerPage={pageSize}
            onRowsPerPageChange={handlePageSizeChange}
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

      <TransformDetailsModal
        open={!!viewingTransform}
        onClose={() => setViewingTransform(null)}
        transform={viewingTransform}
      />

      <Dialog open={!!deleteConfirmId} onClose={() => setDeleteConfirmId(null)}>
        <DialogTitle>Delete Transform</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete this transform? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmId(null)}>Cancel</Button>
          <Button onClick={handleConfirmDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TransformsManagement;
