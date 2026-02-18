import AddIcon from "@mui/icons-material/Add";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import TablePagination from "@mui/material/TablePagination";
import Typography from "@mui/material/Typography";
import React, { useCallback, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import { CreateRagNotebookModal } from "./CreateRagNotebookModal";
import RagNotebookDetailModal from "./RagNotebookDetailModal";
import RagNotebooksHeader from "./RagNotebooksHeader";
import RagNotebooksTable from "./RagNotebooksTable";

import { getContentHeight } from "@/constants/layout";
import { useRagNotebooks, useDeleteRagNotebookMutation, useCreateRagNotebookMutation } from "@/hooks/useRagNotebooks";
import { useTask } from "@/hooks/useTask";
import type { CreateRagNotebookRequest } from "@/lib/api-client/api-client";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const RagNotebooks: React.FC = () => {
  const { task } = useTask();
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [sortColumn, setSortColumn] = useState<string | null>("updated_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [selectedNotebookId, setSelectedNotebookId] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const isDetailModalOpen = selectedNotebookId !== null;

  const filters = useMemo(
    () => ({
      page,
      pageSize,
      sort: sortDirection,
    }),
    [page, pageSize, sortDirection]
  );

  const { notebooks, count, error, isLoading, refetch } = useRagNotebooks(task?.id, filters);

  const deleteMutation = useDeleteRagNotebookMutation(task?.id, () => {
    refetch();
  });

  const createMutation = useCreateRagNotebookMutation(task?.id, (notebook) => {
    refetch();
    setIsCreateModalOpen(false);
    if (taskId) {
      navigate(`/tasks/${taskId}/rag-notebooks/${notebook.id}`);
    }
  });

  const handleCreateNotebook = useCallback(() => {
    setIsCreateModalOpen(true);
  }, []);

  const handleCloseCreateModal = useCallback(() => {
    setIsCreateModalOpen(false);
  }, []);

  const handleSubmitCreateNotebook = useCallback(
    async (data: CreateRagNotebookRequest) => {
      await createMutation.mutateAsync(data);
    },
    [createMutation]
  );

  const handleLaunchNotebook = useCallback(
    (notebookId: string) => {
      if (taskId) {
        navigate(`/tasks/${taskId}/rag-notebooks/${notebookId}`);
      }
    },
    [taskId, navigate]
  );

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

  const handleRowClick = useCallback((notebookId: string) => {
    setSelectedNotebookId(notebookId);
  }, []);

  const handleCloseDetailModal = useCallback(() => {
    setSelectedNotebookId(null);
  }, []);

  if (isLoading && notebooks.length === 0) {
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

  if (error && notebooks.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" onClose={() => refetch()}>
          {error.message || "Failed to load RAG notebooks"}
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
        gridTemplateRows: "auto auto 1fr",
        overflow: "hidden",
      }}
    >
      <RagNotebooksHeader onCreateNotebook={handleCreateNotebook} />

      {error && notebooks.length > 0 && (
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
        {!isLoading && notebooks.length === 0 ? (
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
            <MenuBookOutlinedIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
            <Typography variant="h5" gutterBottom sx={{ fontWeight: 500, color: "text.primary" }}>
              No RAG notebooks yet
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Get started by creating your first RAG notebook
            </Typography>
            <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={handleCreateNotebook} size="large">
              Notebook
            </Button>
          </Box>
        ) : (
          <RagNotebooksTable
            notebooks={notebooks}
            sortColumn={sortColumn}
            sortDirection={sortDirection}
            onSort={handleSort}
            onRowClick={handleRowClick}
            onLaunchNotebook={handleLaunchNotebook}
            onDelete={deleteMutation.mutateAsync}
          />
        )}
      </Box>

      {notebooks.length > 0 && (
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
            count={count}
            page={page}
            onPageChange={handlePageChange}
            rowsPerPage={pageSize}
            onRowsPerPageChange={handlePageSizeChange}
            rowsPerPageOptions={PAGE_SIZE_OPTIONS}
          />
        </Box>
      )}

      <RagNotebookDetailModal open={isDetailModalOpen} notebookId={selectedNotebookId} onClose={handleCloseDetailModal} />

      <CreateRagNotebookModal
        open={isCreateModalOpen}
        onClose={handleCloseCreateModal}
        onSubmit={handleSubmitCreateNotebook}
        isLoading={createMutation.isPending}
      />
    </Box>
  );
};

export default RagNotebooks;
