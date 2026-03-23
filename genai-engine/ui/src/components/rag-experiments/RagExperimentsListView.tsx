import SearchIcon from "@mui/icons-material/Search";
import { Box, InputAdornment, TextField } from "@mui/material";
import React, { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { RagExperimentsEmptyState } from "./RagExperimentsEmptyState";
import { RagExperimentsTable } from "./RagExperimentsTable";
import { RagExperimentsViewHeader } from "./RagExperimentsViewHeader";

import { CreateRagExperimentModal } from "@/components/retrievals/rag-experiment-modal";
import { getContentHeight } from "@/constants/layout";
import { useApi } from "@/hooks/useApi";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useRagExperimentsWithPolling } from "@/hooks/useRagExperiments";
import type { CreateRagExperimentRequest, RagExperimentSummary } from "@/lib/api-client/api-client";

interface RagExperimentsListViewProps {
  onRegisterCreate?: (fn: () => void) => void;
}

export const RagExperimentsListView: React.FC<RagExperimentsListViewProps> = ({ onRegisterCreate }) => {
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const api = useApi();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [searchText, setSearchText] = useState("");
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const debouncedSearchText = useDebouncedValue(searchText, 300);

  const {
    experiments,
    totalCount = 0,
    isLoading,
    error,
    refetch,
  } = useRagExperimentsWithPolling(taskId, page, rowsPerPage, debouncedSearchText || undefined);

  const handleCreateExperiment = useCallback(() => {
    setCreateModalOpen(true);
  }, []);

  const onRegisterCreateRef = useRef(onRegisterCreate);
  useEffect(() => {
    onRegisterCreateRef.current?.(handleCreateExperiment);
  }, [handleCreateExperiment]);

  const handleCreateExperimentSubmit = useCallback(
    async (request: CreateRagExperimentRequest): Promise<{ id: string }> => {
      if (!api || !taskId) {
        throw new Error("API client or task ID not available");
      }
      const response = await api.api.createRagExperimentApiV1TasksTaskIdRagExperimentsPost(taskId, request);
      refetch();
      return { id: response.data.id };
    },
    [api, taskId, refetch]
  );

  const handleRowClick = (experiment: RagExperimentSummary) => {
    navigate(`/tasks/${taskId}/rag-experiments/${experiment.id}`);
  };

  const handlePageChange = (_event: React.MouseEvent<HTMLButtonElement> | null, newPage: number) => {
    setPage(newPage);
  };

  const handleRowsPerPageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleSearchChange = (value: string) => {
    setSearchText(value);
    setPage(0);
  };

  const showLoading = isLoading;
  const showError = !isLoading && error;
  const showEmptyState = !isLoading && !error && experiments.length === 0;
  const showExperiments = !isLoading && !error && experiments.length > 0;

  return (
    <>
      <Box className="w-full grid overflow-hidden" style={{ height: getContentHeight(), gridTemplateRows: "auto 1fr" }}>
        {onRegisterCreate ? (
          <Box sx={{ px: 3, pt: 2, pb: 2, borderBottom: 1, borderColor: "divider", backgroundColor: "background.paper" }}>
            <TextField
              placeholder="Search experiments by name, description, or dataset..."
              value={searchText}
              onChange={(e) => handleSearchChange(e.target.value)}
              fullWidth
              size="small"
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                },
              }}
            />
          </Box>
        ) : (
          <Box className="px-6 pt-6 pb-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
            <RagExperimentsViewHeader onCreateExperiment={handleCreateExperiment} searchValue={searchText} onSearchChange={handleSearchChange} />
          </Box>
        )}

        <Box className="overflow-auto min-h-0">
          {showLoading && (
            <Box className="flex items-center justify-center h-full">
              <p className="text-gray-600">Loading experiments...</p>
            </Box>
          )}
          {showError && (
            <Box className="flex items-center justify-center h-full">
              <p className="text-red-600">{error.message}</p>
            </Box>
          )}
          {showEmptyState && <RagExperimentsEmptyState onCreateExperiment={handleCreateExperiment} />}
          {showExperiments && (
            <RagExperimentsTable
              experiments={experiments}
              onRowClick={handleRowClick}
              page={page}
              rowsPerPage={rowsPerPage}
              totalCount={totalCount}
              onPageChange={handlePageChange}
              onRowsPerPageChange={handleRowsPerPageChange}
              loading={isLoading}
            />
          )}
        </Box>
      </Box>

      <CreateRagExperimentModal open={createModalOpen} onClose={() => setCreateModalOpen(false)} onSubmit={handleCreateExperimentSubmit} />
    </>
  );
};
