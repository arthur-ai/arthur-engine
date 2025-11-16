import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import TablePagination from "@mui/material/TablePagination";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import PromptFullScreenView from "./fullscreen/PromptFullScreenView";
import { useDeletePromptMutation } from "./hooks/useDeletePromptMutation";
import { usePrompts } from "./hooks/usePrompts";
import PromptsManagementHeader from "./PromptsManagementHeader";
import PromptsTable from "./table/PromptsTable";

import { getContentHeight } from "@/constants/layout";
import { useTask } from "@/hooks/useTask";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const PromptsManagement: React.FC = () => {
  const { task } = useTask();
  const { id: taskId, promptName: urlPromptName, version: urlVersion } = useParams<{ id: string; promptName?: string; version?: string }>();
  const navigate = useNavigate();
  const [fullScreenPrompt, setFullScreenPrompt] = useState<string | null>(null);
  const [sortColumn, setSortColumn] = useState<string | null>("latest_version_created_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  // Initialize fullScreenPrompt from URL parameter
  useEffect(() => {
    if (urlPromptName && !fullScreenPrompt) {
      setFullScreenPrompt(urlPromptName);
    }
  }, [urlPromptName, fullScreenPrompt]);

  const filters = useMemo(
    () => ({
      page,
      pageSize,
      sort: sortDirection,
    }),
    [page, pageSize, sortDirection]
  );

  const { prompts, count, error, isLoading, refetch } = usePrompts(task?.id, filters);

  const deleteMutation = useDeletePromptMutation(task?.id, () => {
    refetch();
  });

  const handleCreatePrompt = useCallback(() => {
    // Navigate to prompts playground
    window.location.href = `/tasks/${task?.id}/playgrounds/prompts`;
  }, [task?.id]);

  const handleExpandToFullScreen = useCallback((promptName: string) => {
    setFullScreenPrompt(promptName);
    // Update URL to reflect the selected prompt
    navigate(`/tasks/${taskId}/prompts/${promptName}`);
  }, [taskId, navigate]);

  const handleCloseFullScreen = useCallback(() => {
    setFullScreenPrompt(null);
    // Update URL to go back to the main prompts management view
    navigate(`/tasks/${taskId}/prompts-management`);
  }, [taskId, navigate]);

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

  if (fullScreenPrompt) {
    const initialVersion = urlVersion ? parseInt(urlVersion, 10) : null;
    return (
      <Box sx={{ height: getContentHeight(), overflow: "hidden" }}>
        <PromptFullScreenView promptName={fullScreenPrompt} initialVersion={initialVersion} onClose={handleCloseFullScreen} />
      </Box>
    );
  }

  if (isLoading && prompts.length === 0) {
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

  if (error && prompts.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" onClose={() => refetch()}>
          {error.message || "Failed to load prompts"}
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
      <PromptsManagementHeader onCreatePrompt={handleCreatePrompt} />

      {error && prompts.length > 0 && (
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
        {!isLoading && prompts.length === 0 ? (
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
                No prompts found
              </Box>
              <Box sx={{ color: "text.secondary", mb: 2 }}>Create your first prompt to get started.</Box>
              <Button variant="contained" onClick={handleCreatePrompt} sx={{ mt: 1 }}>
                Create Prompt
              </Button>
            </Box>
          </Box>
        ) : (
          <PromptsTable
            prompts={prompts}
            sortColumn={sortColumn}
            sortDirection={sortDirection}
            onSort={handleSort}
            onExpandToFullScreen={handleExpandToFullScreen}
            onDelete={deleteMutation.mutateAsync}
          />
        )}
      </Box>

      {prompts.length > 0 && (
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
    </Box>
  );
};

export default PromptsManagement;
