import { Box } from "@mui/material";
import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { PromptExperimentsEmptyState } from "./PromptExperimentsEmptyState";
import { PromptExperimentsTable, PromptExperiment } from "./PromptExperimentsTable";
import { PromptExperimentsViewHeader } from "./PromptExperimentsViewHeader";
import { CreateExperimentModal, ExperimentFormData } from "./CreateExperimentModal";

import { getContentHeight } from "@/constants/layout";
import { usePromptExperiments, useCreateExperiment } from "@/hooks/usePromptExperiments";

export const PromptExperimentsView: React.FC = () => {
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  const { experiments, totalCount = 0, isLoading, error } = usePromptExperiments(taskId, page, rowsPerPage);
  const createExperiment = useCreateExperiment(taskId);

  const handleCreateExperiment = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleSubmitExperiment = async (data: ExperimentFormData): Promise<{ id: string }> => {
    // Validate that datasetVersion is a number
    if (typeof data.datasetVersion !== 'number') {
      throw new Error('Dataset version must be selected');
    }

    try {
      // Transform prompt variable mappings to API format
      const promptVariableMapping = Object.entries(data.promptVariableMappings || {}).map(([varName, columnName]) => ({
        variable_name: varName,
        source: {
          type: "dataset_column" as const,
          dataset_column: {
            name: columnName,
          },
        },
      }));

      // Transform eval variable mappings to API format
      const evalList = data.evaluators.map(evaluator => {
        const evalMapping = data.evalVariableMappings?.find(
          m => m.evalName === evaluator.name && m.evalVersion === evaluator.version
        );

        const variableMapping = evalMapping
          ? Object.entries(evalMapping.mappings).map(([varName, mapping]) => {
              if (mapping.sourceType === "dataset_column") {
                return {
                  variable_name: varName,
                  source: {
                    type: "dataset_column" as const,
                    dataset_column: {
                      name: mapping.datasetColumn || "",
                    },
                  },
                };
              } else {
                return {
                  variable_name: varName,
                  source: {
                    type: "experiment_output" as const,
                    experiment_output: {
                      json_path: mapping.jsonPath || null,
                    },
                  },
                };
              }
            })
          : [];

        return {
          name: evaluator.name,
          version: evaluator.version,
          variable_mapping: variableMapping,
        };
      });

      const result = await createExperiment.mutateAsync({
        name: data.name,
        description: data.description,
        dataset_ref: {
          id: data.datasetId,
          version: data.datasetVersion,
        },
        prompt_ref: {
          name: data.promptVersions[0].promptName,
          version_list: data.promptVersions.map(pv => pv.version),
          variable_mapping: promptVariableMapping,
        },
        eval_list: evalList,
      });
      handleCloseModal();
      return { id: result.id };
    } catch (err) {
      console.error("Failed to create experiment:", err);
      throw err;
    }
  };

  const handleRowClick = (experiment: PromptExperiment) => {
    navigate(`/tasks/${taskId}/prompt-experiments/${experiment.id}`);
  };

  const handlePageChange = (_event: React.MouseEvent<HTMLButtonElement> | null, newPage: number) => {
    setPage(newPage);
  };

  const handleRowsPerPageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <>
      <Box
        className="w-full grid overflow-hidden"
        style={{ height: getContentHeight(), gridTemplateRows: "auto 1fr" }}
      >
        <Box className="px-6 pt-6 pb-4 border-b border-gray-200 bg-white">
          <PromptExperimentsViewHeader onCreateExperiment={handleCreateExperiment} />
        </Box>

        <Box className="overflow-auto min-h-0">
          {isLoading ? (
            <Box className="flex items-center justify-center h-full">
              <p className="text-gray-600">Loading experiments...</p>
            </Box>
          ) : error ? (
            <Box className="flex items-center justify-center h-full">
              <p className="text-red-600">{error.message}</p>
            </Box>
          ) : experiments.length === 0 ? (
            <PromptExperimentsEmptyState onCreateExperiment={handleCreateExperiment} />
          ) : (
            <PromptExperimentsTable
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

      <CreateExperimentModal
        open={isModalOpen}
        onClose={handleCloseModal}
        onSubmit={handleSubmitExperiment}
      />
    </>
  );
};
