import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CloseIcon from "@mui/icons-material/Close";
import {
  Box,
  IconButton,
  Typography,
  Chip,
  Modal,
} from "@mui/material";
import React from "react";

import { MessageDisplay, VariableTile } from "./PromptResultComponents";

import type { InputVariable, EvalExecution, PromptOutput } from "@/lib/api-client/api-client";

interface Message {
  role: "system" | "user" | "assistant";
  content: string;
}

interface PromptResultDetailModalProps {
  open: boolean;
  onClose: () => void;
  promptName: string;
  promptVersion: string | number;
  inputVariables: InputVariable[];
  renderedPrompt: string;
  output: PromptOutput | null | undefined;
  evals: EvalExecution[];
  currentIndex: number;
  totalCount: number;
  onPrevious?: () => void;
  onNext?: () => void;
}

export const PromptResultDetailModal: React.FC<PromptResultDetailModalProps> = ({
  open,
  onClose,
  promptName,
  promptVersion,
  inputVariables,
  renderedPrompt,
  output,
  evals,
  currentIndex,
  totalCount,
  onPrevious,
  onNext,
}) => {
  const getEvalChipSx = (isPass: boolean) => {
    const color = isPass ? "success.main" : "error.main";
    return {
      backgroundColor: "transparent",
      color: color,
      borderColor: color,
      borderWidth: 1,
      borderStyle: "solid",
    };
  };

  const getPendingChipSx = () => ({
    backgroundColor: "transparent",
    color: "text.secondary",
    borderColor: "text.secondary",
    borderWidth: 1,
    borderStyle: "solid",
  });

  // Add keyboard navigation
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!open) return;

      if (e.key === "ArrowLeft" && onPrevious) {
        e.preventDefault();
        onPrevious();
      } else if (e.key === "ArrowRight" && onNext) {
        e.preventDefault();
        onNext();
      } else if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onPrevious, onNext, onClose]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="prompt-result-detail-modal"
    >
      <Box
        className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[90vw] max-w-6xl max-h-[90vh] bg-white rounded-lg shadow-xl overflow-auto"
      >
        {/* Modal Header */}
        <Box className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center z-10">
          <Box className="flex items-center gap-3">
            {onPrevious && (
              <IconButton
                onClick={onPrevious}
                size="small"
                disabled={currentIndex <= 0}
                className="hover:bg-gray-100"
              >
                <ArrowBackIcon />
              </IconButton>
            )}
            <Typography variant="h6" className="font-semibold text-gray-900">
              Result {currentIndex + 1} of {totalCount} - {promptName} (v{promptVersion})
            </Typography>
            {onNext && (
              <IconButton
                onClick={onNext}
                size="small"
                disabled={currentIndex >= totalCount - 1}
                className="hover:bg-gray-100"
              >
                <ArrowForwardIcon />
              </IconButton>
            )}
          </Box>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Modal Content */}
        <Box className="p-6">
          {/* Input Variables Section */}
          <Box className="mb-6">
            <Typography
              variant="h6"
              className="font-bold mb-4 pb-2 border-b-2 border-gray-300 text-gray-900"
            >
              Input Variables
            </Typography>
            <Box className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {inputVariables.map((variable) => (
                <VariableTile
                  key={variable.variable_name}
                  variableName={variable.variable_name}
                  value={variable.value}
                />
              ))}
            </Box>
          </Box>

          {/* Messages: Rendered Prompt and Output */}
          <Box className="mb-6">
            <Typography
              variant="h6"
              className="font-bold mb-4 pb-2 border-b-2 border-gray-300 text-gray-900"
            >
              Messages
            </Typography>
            <Box className="grid grid-cols-2 gap-4">
              {/* Rendered Prompt Messages */}
              <Box>
                <Typography variant="subtitle2" className="font-medium text-gray-700 mb-2">
                  Input Messages:
                </Typography>
                <Box className="max-h-96 overflow-auto">
                  {(() => {
                    try {
                      const messages = JSON.parse(renderedPrompt) as Message[];
                      return messages.map((message, msgIndex) => (
                        <MessageDisplay key={msgIndex} message={message} />
                      ));
                    } catch {
                      // If not JSON, display as plain text
                      return (
                        <Box className="p-3 bg-gray-100 border border-gray-300 rounded">
                          <Typography variant="body2" className="whitespace-pre-wrap text-gray-900">
                            {renderedPrompt}
                          </Typography>
                        </Box>
                      );
                    }
                  })()}
                </Box>
              </Box>

              {/* Output */}
              <Box>
                <Typography variant="subtitle2" className="font-medium text-gray-700 mb-2">
                  Output Message:
                </Typography>
                <Box className="max-h-96 overflow-auto">
                  {output ? (
                    <>
                      {output.content && (
                        <MessageDisplay
                          message={{ role: "assistant", content: output.content }}
                        />
                      )}
                      {output.tool_calls && output.tool_calls.length > 0 && (
                        <Box className="mt-2 p-2 bg-purple-50 border border-purple-200 rounded">
                          <Typography variant="caption" className="font-medium text-purple-700">
                            Tool Calls: {output.tool_calls.length}
                          </Typography>
                        </Box>
                      )}
                    </>
                  ) : (
                    <Box className="p-3 bg-gray-100 border border-gray-300 rounded">
                      <Typography variant="body2" className="text-gray-500 italic">
                        No output available
                      </Typography>
                    </Box>
                  )}
                </Box>
              </Box>
            </Box>
          </Box>

          {/* Evals */}
          {evals.length > 0 && (
            <Box>
              <Typography
                variant="h6"
                className="font-bold mb-4 pb-2 border-b-2 border-gray-300 text-gray-900"
              >
                Evaluations
              </Typography>
              <Box className="space-y-2">
                {evals.map((evalItem, evalIndex) => (
                  <Box key={evalIndex} className="p-3 bg-blue-50 border border-blue-200 rounded">
                    <Box className="flex items-center gap-2 mb-2">
                      <Typography variant="body2" className="font-medium text-gray-900">
                        {evalItem.eval_name} v{evalItem.eval_version}
                      </Typography>
                      {evalItem.eval_results ? (
                        <>
                          <Chip
                            label={evalItem.eval_results.score === 1 ? "Pass" : "Fail"}
                            size="small"
                            sx={getEvalChipSx(evalItem.eval_results.score === 1)}
                          />
                          <Chip
                            label={`Cost: $${evalItem.eval_results.cost}`}
                            size="small"
                            variant="outlined"
                          />
                        </>
                      ) : (
                        <Chip
                          label="Pending"
                          size="small"
                          sx={getPendingChipSx()}
                        />
                      )}
                    </Box>
                    {evalItem.eval_results?.explanation && (
                      <Typography variant="body2" className="text-gray-700 mt-1">
                        {evalItem.eval_results.explanation}
                      </Typography>
                    )}
                  </Box>
                ))}
              </Box>
            </Box>
          )}
        </Box>
      </Box>
    </Modal>
  );
};
