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

  const { experiments, isLoading, error } = usePromptExperiments(taskId);
  const createExperiment = useCreateExperiment(taskId);

  const handleCreateExperiment = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleSubmitExperiment = async (data: ExperimentFormData) => {
    // Validate that datasetVersion is a number
    if (typeof data.datasetVersion !== 'number') {
      throw new Error('Dataset version must be selected');
    }

    try {
      await createExperiment.mutateAsync({
        name: data.name,
        description: data.description,
        dataset_ref: {
          id: data.datasetId,
          version: data.datasetVersion,
        },
        prompt_ref: {
          name: data.promptVersions[0].promptName,
          version_list: data.promptVersions.map(pv => pv.version),
          variable_mapping: [],
        },
        eval_list: data.evaluators.map(evaluator => ({
          name: evaluator.name,
          version: evaluator.version,
          variable_mapping: [],
        })),
      });
      handleCloseModal();
    } catch (err) {
      console.error("Failed to create experiment:", err);
      throw err;
    }
  };

  const handleRowClick = (experiment: PromptExperiment) => {
    navigate(`/tasks/${taskId}/prompt-experiments/${experiment.id}`);
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
