import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import TablePagination from "@mui/material/TablePagination";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import NotebookDetailModal from "./NotebookDetailModal";
import NotebooksHeader from "./NotebooksHeader";
import NotebooksTable from "./NotebooksTable";

import { getContentHeight } from "@/constants/layout";
import { useTask } from "@/hooks/useTask";
import { useNotebooks, useDeleteNotebookMutation } from "@/hooks/useNotebooks";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const Notebooks: React.FC = () => {
  const { task } = useTask();
  const { id: taskId } = useParams<{ id: string }>();
  const [sortColumn, setSortColumn] = useState<string | null>("updated_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [selectedNotebookId, setSelectedNotebookId] = useState<string | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

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

  const handleCreateNotebook = useCallback(() => {
    console.log("Create notebook - not implemented yet");
    // TODO: Phase 2 - Open CreateNotebookModal
  }, []);

  const handleLaunchNotebook = useCallback(
    (notebookId: string) => {
      console.log("Launch notebook:", notebookId);
      // TODO: Phase 2 - Navigate to /tasks/{taskId}/playgrounds/prompts?notebookId={notebookId}
    },
    []
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
      <NotebooksHeader onCreateNotebook={handleCreateNotebook} />

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
              alignItems: "center",
              justifyContent: "center",
              flex: 1,
              p: 3,
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
                No notebooks found
              </Box>
              <Box sx={{ color: "text.secondary", mb: 2 }}>
                Create your first notebook to start experimenting with prompts.
              </Box>
              <Button variant="contained" onClick={handleCreateNotebook} sx={{ mt: 1 }}>
                Create Notebook
              </Button>
            </Box>
          </Box>
        ) : (
          <NotebooksTable
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

      <NotebookDetailModal
        open={isDetailModalOpen}
        notebookId={selectedNotebookId}
        onClose={handleCloseDetailModal}
      />
    </Box>
  );
};

export default Notebooks;

