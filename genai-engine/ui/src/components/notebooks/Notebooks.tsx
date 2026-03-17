import AddIcon from "@mui/icons-material/Add";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import TablePagination from "@mui/material/TablePagination";
import Typography from "@mui/material/Typography";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import { CreateNotebookModal } from "./CreateNotebookModal";
import NotebookDetailModal from "./NotebookDetailModal";
import NotebooksHeader from "./NotebooksHeader";
import NotebooksTable from "./NotebooksTable";

import { getContentHeight } from "@/constants/layout";
import { useNotebooks, useDeleteNotebookMutation, useCreateNotebookMutation } from "@/hooks/useNotebooks";
import { useTask } from "@/hooks/useTask";
import type { CreateNotebookRequest } from "@/lib/api-client/api-client";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

interface NotebooksProps {
  onRegisterCreate?: (fn: () => void) => void;
}

const Notebooks: React.FC<NotebooksProps> = ({ onRegisterCreate }) => {
  const { task } = useTask();
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [sortColumn, setSortColumn] = useState<string | null>("updated_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [selectedNotebookId, setSelectedNotebookId] = useState<string | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const filters = useMemo(
    () => ({
      page,
      pageSize,
      sort: sortDirection,
    }),
    [page, pageSize, sortDirection]
  );

  const { notebooks, count, error, isLoading, refetch } = useNotebooks(task?.id, filters);

  const deleteMutation = useDeleteNotebookMutation(task?.id, () => {
    refetch();
  });

  const createMutation = useCreateNotebookMutation(task?.id, (notebook) => {
    refetch();
    setIsCreateModalOpen(false);
    if (taskId) {
      navigate(`/tasks/${taskId}/playgrounds/prompts?notebookId=${notebook.id}`);
    }
  });

  const handleCreateNotebook = useCallback(() => {
    setIsCreateModalOpen(true);
  }, []);

  useEffect(() => {
    onRegisterCreate?.(() => setIsCreateModalOpen(true));
  }, [onRegisterCreate]);

  const handleCloseCreateModal = useCallback(() => {
    setIsCreateModalOpen(false);
  }, []);

  const handleSubmitCreateNotebook = useCallback(
    async (data: CreateNotebookRequest) => {
      await createMutation.mutateAsync(data);
    },
    [createMutation]
  );

  const handleLaunchNotebook = useCallback(
    (notebookId: string) => {
      if (taskId) {
        navigate(`/tasks/${taskId}/playgrounds/prompts?notebookId=${notebookId}`);
      }
    },
    [taskId, navigate]
  );

  const handleViewLastRun = useCallback(
    (experimentId: string) => {
      if (taskId) {
        navigate(`/tasks/${taskId}/prompt-experiments/${experimentId}`);
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
    setIsDetailModalOpen(true);
  }, []);

  const handleCloseDetailModal = useCallback(() => {
    setIsDetailModalOpen(false);
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
          {error.message || "Failed to load notebooks"}
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
      {!onRegisterCreate && <NotebooksHeader onCreateNotebook={handleCreateNotebook} />}

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
              No notebooks yet
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Get started by creating your first notebook
            </Typography>
            <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={handleCreateNotebook} size="large">
              Notebook
            </Button>
          </Box>
        ) : (
          <NotebooksTable
            notebooks={notebooks}
            sortColumn={sortColumn}
            sortDirection={sortDirection}
            onSort={handleSort}
            onRowClick={handleRowClick}
            onLaunchNotebook={handleLaunchNotebook}
            onViewLastRun={handleViewLastRun}
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

      <NotebookDetailModal open={isDetailModalOpen} notebookId={selectedNotebookId} onClose={handleCloseDetailModal} />

      <CreateNotebookModal
        open={isCreateModalOpen}
        onClose={handleCloseCreateModal}
        onSubmit={handleSubmitCreateNotebook}
        isLoading={createMutation.isPending}
      />
    </Box>
  );
};

export default Notebooks;
