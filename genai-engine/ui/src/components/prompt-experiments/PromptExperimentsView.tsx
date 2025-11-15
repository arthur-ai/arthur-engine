import { Box } from "@mui/material";
import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { PromptExperimentsEmptyState } from "./PromptExperimentsEmptyState";
import { PromptExperimentsTable, PromptExperiment } from "./PromptExperimentsTable";
import { PromptExperimentsViewHeader } from "./PromptExperimentsViewHeader";
import { CreateExperimentModal, ExperimentFormData } from "./CreateExperimentModal";

import { getContentHeight } from "@/constants/layout";

// Mock data for development - replace with API call later
const MOCK_EXPERIMENTS: PromptExperiment[] = [
  {
    id: "exp-1",
    name: "Customer Support Tone Variations",
    description: "Testing different tones for customer support responses",
    status: "completed",
    created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    finished_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    prompt_name: "customer_support_v2",
    total_rows: 150,
  },
  {
    id: "exp-2",
    name: "Product Description Generator",
    description: "Comparing prompt templates for product descriptions",
    status: "running",
    created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    finished_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
    prompt_name: "product_desc_template",
    total_rows: 500,
  },
  {
    id: "exp-3",
    name: "Code Review Assistant",
    description: "Testing different prompt structures for code review",
    status: "queued",
    created_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    finished_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    prompt_name: "code_reviewer_v1",
    total_rows: 75,
  },
  {
    id: "exp-4",
    name: "Summarization Length Experiment",
    description: "Comparing different length constraints in summarization prompts",
    status: "completed",
    created_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
    finished_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    prompt_name: "summarizer_base",
    total_rows: 200,
  },
  {
    id: "exp-5",
    name: "Sentiment Analysis Variations",
    description: "Testing prompt variations for sentiment classification",
    status: "failed",
    created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    finished_at: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
    prompt_name: "sentiment_classifier",
    total_rows: 1000,
  },
  {
    id: "exp-6",
    name: "Translation Quality Assessment",
    description: "Evaluating translation accuracy across different prompts",
    status: "evaluating",
    created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    finished_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    prompt_name: "translator_v3",
    total_rows: 350,
  },
];

export const PromptExperimentsView: React.FC = () => {
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Using mock data for now - will be replaced with API call
  const [experiments] = useState<PromptExperiment[]>(MOCK_EXPERIMENTS);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleCreateExperiment = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleSubmitExperiment = async (data: ExperimentFormData) => {
    console.log("Creating experiment with data:", data);
    // TODO: Call API to create experiment
    // For now, just log the data
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
          {experiments.length === 0 ? (
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
