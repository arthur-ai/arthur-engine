import AddIcon from "@mui/icons-material/Add";
import BalanceOutlinedIcon from "@mui/icons-material/BalanceOutlined";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import TablePagination from "@mui/material/TablePagination";
import Typography from "@mui/material/Typography";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import CreateEvalTypeModal from "./CreateEvalTypeModal";
import EvalFormModal from "./EvalFormModal";
import { EvaluatorAccordionList } from "./EvaluatorAccordionList";
import EvaluatorsHeader from "./EvaluatorsHeader";
import EvalFullScreenView from "./fullscreen/EvalFullScreenView";
import { useEvals } from "./hooks/useEvals";
import { useCreateEvalMutation } from "./hooks/useCreateEvalMutation";
import { useDeleteEvalMutation } from "./hooks/useDeleteEvalMutation";
import { useDeleteMLEvalMutation } from "./hooks/useDeleteMLEvalMutation";

import { SearchBar } from "@/components/common/SearchBar";
import { useCreateMlEvalMutation } from "@/components/ml-evaluators/hooks/useCreateMlEvalMutation";
import MLEvalFormModal from "@/components/ml-evaluators/MLEvalFormModal";
import { getContentHeight } from "@/constants/layout";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useTask } from "@/hooks/useTask";
import { CreateEvalRequest, CreateMLEvalRequest } from "@/lib/api-client/api-client";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

interface EvaluatorsProps {
  embedded?: boolean;
  isCreateModalOpen?: boolean;
  onCreateModalOpen?: () => void;
  onCreateModalClose?: () => void;
}

const Evaluators: React.FC<EvaluatorsProps> = ({ embedded = false, isCreateModalOpen: externalOpen, onCreateModalOpen, onCreateModalClose }) => {
  const { task } = useTask();
  const { id: taskId, evaluatorName: urlEvaluatorName, version: urlVersion } = useParams<{ id: string; evaluatorName?: string; version?: string }>();
  const navigate = useNavigate();
  const [fullScreenEval, setFullScreenEval] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [internalOpen, setInternalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearchQuery = useDebouncedValue(searchQuery, 300);

  // Type picker + per-type modal state
  const [isTypePickerOpen, setIsTypePickerOpen] = useState(false);
  const [isLLMModalOpen, setIsLLMModalOpen] = useState(false);
  const [isMLModalOpen, setIsMLModalOpen] = useState(false);

  const isCreateModalOpen = embedded ? (externalOpen ?? false) : internalOpen;
  const setIsCreateModalOpen = (value: boolean) => {
    if (embedded) {
      if (value) onCreateModalOpen?.();
      else onCreateModalClose?.();
    } else {
      setInternalOpen(value);
    }
  };

  // When the unified "create" trigger fires, open the type picker
  const prevExternalOpen = React.useRef(false);
  React.useEffect(() => {
    if (isCreateModalOpen && !prevExternalOpen.current) {
      setIsTypePickerOpen(true);
      // Immediately close the external open signal so the picker manages its own state
      setIsCreateModalOpen(false);
    }
    prevExternalOpen.current = isCreateModalOpen;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isCreateModalOpen]);

  // Reset to first page when search changes
  useEffect(() => {
    setPage(0);
  }, [debouncedSearchQuery]);

  // Sync fullScreenEval with URL parameter
  useEffect(() => {
    if (urlEvaluatorName) {
      setFullScreenEval(urlEvaluatorName);
    } else if (!urlEvaluatorName && fullScreenEval) {
      setFullScreenEval(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlEvaluatorName]);

  // When searching, fetch all evals (up to API max) so client-side filter spans the full dataset,
  // not just the current server page.
  const filters = useMemo(
    () => ({
      page: debouncedSearchQuery ? 0 : page,
      pageSize: debouncedSearchQuery ? 5000 : pageSize,
      sort: "desc" as const,
    }),
    [page, pageSize, debouncedSearchQuery]
  );

  const { evals, count, error, isLoading, refetch } = useEvals(task?.id, filters);

  const filteredEvals = useMemo(() => {
    if (!debouncedSearchQuery) return evals;
    const query = debouncedSearchQuery.toLowerCase();
    return evals.filter((e) => e.name.toLowerCase().includes(query));
  }, [evals, debouncedSearchQuery]);

  const createMutation = useCreateEvalMutation(task?.id, (evalData) => {
    setIsLLMModalOpen(false);
    refetch();
    // Navigate to the newly created eval's detail page
    navigate(`/tasks/${taskId}/evaluators/${encodeURIComponent(evalData.name)}/versions/${evalData.version}`);
  });

  const createMLMutation = useCreateMlEvalMutation(task?.id, () => {
    setIsMLModalOpen(false);
    refetch();
  });

  const deleteLLMMutation = useDeleteEvalMutation(task?.id, () => {
    refetch();
  });
  const deleteMLMutation = useDeleteMLEvalMutation(task?.id, () => {
    refetch();
  });

  const handleDelete = useCallback(
    async (evalName: string) => {
      const evalMeta = filteredEvals.find((e) => e.name === evalName);
      if (evalMeta?.eval_type !== "llm_as_a_judge") {
        await deleteMLMutation.mutateAsync(evalName);
      } else {
        await deleteLLMMutation.mutateAsync(evalName);
      }
    },
    [filteredEvals, deleteLLMMutation, deleteMLMutation]
  );

  const handleCreateEval = useCallback(
    async (evalName: string, data: CreateEvalRequest) => {
      await createMutation.mutateAsync({ evalName, data });
    },
    [createMutation]
  );

  const handleCreateMLEval = useCallback(
    async (evalName: string, data: CreateMLEvalRequest) => {
      await createMLMutation.mutateAsync({ evalName, data });
    },
    [createMLMutation]
  );

  const handleExpandToFullScreen = useCallback(
    (evalName: string) => {
      setFullScreenEval(evalName);
      // Update URL to reflect the selected evaluator
      navigate(`/tasks/${taskId}/evaluators/${encodeURIComponent(evalName)}`);
    },
    [taskId, navigate]
  );

  const handleCloseFullScreen = useCallback(() => {
    setFullScreenEval(null);
    // Navigate back to the combined Evaluate view
    navigate(`/tasks/${taskId}/evaluate`);
  }, [taskId, navigate]);

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

  // Standalone uses 4 explicit rows (header + search + error + table); embedded uses 3 (search + error + table)
  const gridTemplateRows = embedded ? "auto auto 1fr" : "auto auto auto 1fr";

  return (
    <Box
      sx={{
        width: "100%",
        height: getContentHeight(),
        display: "grid",
        gridTemplateRows,
        overflow: "hidden",
      }}
    >
      {!embedded && <EvaluatorsHeader onCreateEval={() => setIsCreateModalOpen(true)} />}

      <Box
        sx={{
          px: 3,
          py: 1.5,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <SearchBar value={searchQuery} onChange={setSearchQuery} onClear={() => setSearchQuery("")} placeholder="Search evaluators by name..." />
      </Box>

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
        {!isLoading && filteredEvals.length === 0 ? (
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
            <BalanceOutlinedIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
            {debouncedSearchQuery ? (
              <>
                <Typography variant="h5" gutterBottom sx={{ fontWeight: 500, color: "text.primary" }}>
                  No results found
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  No evaluators match &ldquo;{debouncedSearchQuery}&rdquo;
                </Typography>
              </>
            ) : (
              <>
                <Typography variant="h5" gutterBottom sx={{ fontWeight: 500, color: "text.primary" }}>
                  No evals yet
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                  Get started by creating your first eval
                </Typography>
                <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setIsTypePickerOpen(true)} size="large">
                  Evaluator
                </Button>
              </>
            )}
          </Box>
        ) : (
          <EvaluatorAccordionList evals={filteredEvals} taskId={taskId!} onExpandToFullScreen={handleExpandToFullScreen} onDelete={handleDelete} />
        )}
      </Box>

      {!debouncedSearchQuery && filteredEvals.length > 0 && (
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
            count={debouncedSearchQuery ? filteredEvals.length : count}
            page={page}
            onPageChange={handlePageChange}
            rowsPerPage={pageSize}
            onRowsPerPageChange={handlePageSizeChange}
            rowsPerPageOptions={PAGE_SIZE_OPTIONS}
          />
        </Box>
      )}

      <CreateEvalTypeModal
        open={isTypePickerOpen}
        onClose={() => setIsTypePickerOpen(false)}
        onSelectType={(type) => {
          setIsTypePickerOpen(false);
          if (type === "llm") setIsLLMModalOpen(true);
          else setIsMLModalOpen(true);
        }}
      />

      <EvalFormModal
        open={isLLMModalOpen}
        onClose={() => setIsLLMModalOpen(false)}
        onSubmit={handleCreateEval}
        isLoading={createMutation.isPending}
      />

      <MLEvalFormModal
        open={isMLModalOpen}
        onClose={() => setIsMLModalOpen(false)}
        onSubmit={handleCreateMLEval}
        isLoading={createMLMutation.isPending}
      />
    </Box>
  );
};

export default Evaluators;
