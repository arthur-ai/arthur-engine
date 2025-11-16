import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import TablePagination from "@mui/material/TablePagination";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import EvalFormModal from "./EvalFormModal";
import EvaluatorsHeader from "./EvaluatorsHeader";
import EvalFullScreenView from "./fullscreen/EvalFullScreenView";
import { useCreateEvalMutation } from "./hooks/useCreateEvalMutation";
import { useDeleteEvalMutation } from "./hooks/useDeleteEvalMutation";
import { useEvals } from "./hooks/useEvals";
import EvalsTable from "./table/EvalsTable";

import { getContentHeight } from "@/constants/layout";
import { useTask } from "@/hooks/useTask";
import { CreateEvalRequest } from "@/lib/api-client/api-client";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const Evaluators: React.FC = () => {
  const { task } = useTask();
  const { id: taskId, evaluatorName: urlEvaluatorName, version: urlVersion } = useParams<{ id: string; evaluatorName?: string; version?: string }>();
  const navigate = useNavigate();
  const [fullScreenEval, setFullScreenEval] = useState<string | null>(null);
  const [sortColumn, setSortColumn] = useState<string | null>("latest_version_created_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Initialize fullScreenEval from URL parameter
  useEffect(() => {
    if (urlEvaluatorName && !fullScreenEval) {
      setFullScreenEval(urlEvaluatorName);
    }
  }, [urlEvaluatorName, fullScreenEval]);

  const filters = useMemo(
    () => ({
      page,
      pageSize,
      sort: sortDirection,
    }),
    [page, pageSize, sortDirection]
  );

  const { evals, count, error, isLoading, refetch } = useEvals(task?.id, filters);

  const createMutation = useCreateEvalMutation(task?.id, () => {
    setIsCreateModalOpen(false);
    refetch();
  });

  const deleteMutation = useDeleteEvalMutation(task?.id, () => {
    refetch();
  });

  const handleCreateEval = useCallback(
    async (evalName: string, data: CreateEvalRequest) => {
      await createMutation.mutateAsync({ evalName, data });
    },
    [createMutation]
  );

  const handleExpandToFullScreen = useCallback((evalName: string) => {
    setFullScreenEval(evalName);
    // Update URL to reflect the selected evaluator
    navigate(`/tasks/${taskId}/evaluators/${evalName}`);
  }, [taskId, navigate]);

  const handleCloseFullScreen = useCallback(() => {
    setFullScreenEval(null);
    // Update URL to go back to the main evaluators view
    navigate(`/tasks/${taskId}/evaluators`);
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

  if (fullScreenEval) {
    const initialVersion = urlVersion ? parseInt(urlVersion, 10) : null;
    return (
      <Box sx={{ height: getContentHeight(), overflow: "hidden" }}>
        <EvalFullScreenView evalName={fullScreenEval} initialVersion={initialVersion} onClose={handleCloseFullScreen} />
      </Box>
    );
  }

  if (isLoading && evals.length === 0) {
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

  if (error && evals.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" onClose={() => refetch()}>
          {error.message || "Failed to load evals"}
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
      <EvaluatorsHeader onCreateEval={() => setIsCreateModalOpen(true)} />

      {error && evals.length > 0 && (
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
        {!isLoading && evals.length === 0 ? (
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
                No evals found
              </Box>
              <Box sx={{ color: "text.secondary", mb: 2 }}>Create your first eval to get started.</Box>
              <Button variant="contained" onClick={() => setIsCreateModalOpen(true)} sx={{ mt: 1 }}>
                Create Evaluator
              </Button>
            </Box>
          </Box>
        ) : (
          <EvalsTable
            evals={evals}
            sortColumn={sortColumn}
            sortDirection={sortDirection}
            onSort={handleSort}
            onExpandToFullScreen={handleExpandToFullScreen}
            onDelete={deleteMutation.mutateAsync}
          />
        )}
      </Box>

      {evals.length > 0 && (
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

      <EvalFormModal
        open={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateEval}
        isLoading={createMutation.isPending}
      />
    </Box>
  );
};

export default Evaluators;
