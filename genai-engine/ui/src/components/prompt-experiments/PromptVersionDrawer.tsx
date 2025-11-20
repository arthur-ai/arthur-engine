import CloseIcon from "@mui/icons-material/Close";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import {
  Box,
  Drawer,
  IconButton,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Paper,
  LinearProgress,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Link,
} from "@mui/material";
import React, { useState, useEffect, useMemo } from "react";
import { Link as RouterLink } from "react-router-dom";

import { PromptResultDetailModal, EvalInputsDialog } from "./PromptResultDetailModal";

import NunjucksHighlightedTextField from "@/components/evaluators/MustacheHighlightedTextField";
import { usePrompt } from "@/components/prompts-management/hooks/usePrompt";
import { usePromptVersionResults } from "@/hooks/usePromptExperiments";
import { formatUTCTimestamp } from "@/utils/formatters";

interface EvalResult {
  eval_name: string;
  eval_version: string;
  pass_count: number;
  total_count: number;
}

interface PromptVersionDetails {
  prompt_key?: string | null; // Format: "saved:name:version" or "unsaved:auto_name"
  prompt_type?: string | null; // "saved" or "unsaved"
  prompt_name?: string | null; // For saved prompts or auto_name for unsaved
  prompt_version?: string | null; // For saved prompts only
  eval_results: EvalResult[];
}

interface PromptVersionDrawerProps {
  open: boolean;
  onClose: () => void;
  promptDetails: PromptVersionDetails | null;
  taskId: string;
  experimentId: string;
  experimentPromptConfigs?: Array<{
    type: "saved" | "unsaved";
    name?: string;
    version?: number;
    auto_name?: string;
    messages?: any[];
    model_name?: string;
    model_provider?: string;
    tools?: any[];
    config?: any;
    variables?: string[];
  }>;
}

export const PromptVersionDrawer: React.FC<PromptVersionDrawerProps> = ({
  open,
  onClose,
  promptDetails,
  taskId,
  experimentId,
  experimentPromptConfigs,
}) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedResultIndex, setSelectedResultIndex] = useState<number>(-1);
  const [pendingIndexAfterPageLoad, setPendingIndexAfterPageLoad] = useState<"first" | "last" | null>(null);
  const [evalInputsDialogOpen, setEvalInputsDialogOpen] = useState(false);
  const [selectedEvalExecution, setSelectedEvalExecution] = useState<any>(null);

  // Find unsaved prompt config if this is an unsaved prompt
  const unsavedPromptConfig = useMemo(() => {
    if (promptDetails?.prompt_type === "unsaved" && experimentPromptConfigs) {
      return experimentPromptConfigs.find(config =>
        config.type === "unsaved" &&
        (config.auto_name === promptDetails.prompt_name ||
         `unsaved:${config.auto_name}` === promptDetails.prompt_key)
      );
    }
    return null;
  }, [promptDetails, experimentPromptConfigs]);

  // Fetch prompt version details (only for saved prompts)
  const shouldFetchPrompt = promptDetails && (promptDetails.prompt_type === "saved" || !promptDetails.prompt_type) && !!promptDetails.prompt_name && !!promptDetails.prompt_version;
  const { prompt: fetchedPrompt, isLoading: isPromptLoading } = usePrompt(
    taskId,
    shouldFetchPrompt && promptDetails ? promptDetails.prompt_name : undefined,
    shouldFetchPrompt && promptDetails ? promptDetails.prompt_version : undefined
  );

  // Use either fetched prompt (for saved) or construct from config (for unsaved)
  const prompt = useMemo(() => {
    if (fetchedPrompt) {
      return fetchedPrompt;
    }
    if (unsavedPromptConfig) {
      // Construct a prompt object from the unsaved config
      return {
        messages: unsavedPromptConfig.messages || [],
        model_name: unsavedPromptConfig.model_name || "",
        model_provider: unsavedPromptConfig.model_provider || "",
        config: unsavedPromptConfig.config || {},
        tools: unsavedPromptConfig.tools,
        variables: unsavedPromptConfig.variables,
        created_at: null, // Unsaved prompts don't have timestamps
      };
    }
    return null;
  }, [fetchedPrompt, unsavedPromptConfig]);

  // Use prompt_key directly from prompt details, or construct it from old format
  const promptKey = promptDetails?.prompt_key ||
    (promptDetails && promptDetails.prompt_name && promptDetails.prompt_version
      ? `saved:${promptDetails.prompt_name}:${promptDetails.prompt_version}`
      : undefined);

  // Fetch prompt version results from the experiment
  const {
    results,
    totalCount,
    isLoading: isResultsLoading,
  } = usePromptVersionResults(
    experimentId,
    promptKey,
    page,
    rowsPerPage
  );

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Effect to handle index after page load
  useEffect(() => {
    if (pendingIndexAfterPageLoad && results.length > 0) {
      if (pendingIndexAfterPageLoad === "first") {
        setSelectedResultIndex(0);
      } else if (pendingIndexAfterPageLoad === "last") {
        setSelectedResultIndex(results.length - 1);
      }
      setPendingIndexAfterPageLoad(null);
    }
  }, [results, pendingIndexAfterPageLoad]);

  const handleRowClick = (index: number) => {
    setSelectedResultIndex(index);
    setDetailModalOpen(true);
  };

  const handleCloseDetailModal = () => {
    setDetailModalOpen(false);
    setSelectedResultIndex(-1);
  };

  const handleViewEvalInputs = (evalExecution: any) => {
    setSelectedEvalExecution(evalExecution);
    setEvalInputsDialogOpen(true);
  };

  const handleCloseEvalInputsDialog = () => {
    setEvalInputsDialogOpen(false);
    setSelectedEvalExecution(null);
  };

  const handlePrevious = () => {
    if (selectedResultIndex > 0) {
      // Navigate within current page
      setSelectedResultIndex(selectedResultIndex - 1);
    } else if (page > 0) {
      // Load previous page and go to last item
      setPendingIndexAfterPageLoad("last");
      setPage(page - 1);
    }
  };

  const handleNext = () => {
    if (selectedResultIndex < results.length - 1) {
      // Navigate within current page
      setSelectedResultIndex(selectedResultIndex + 1);
    } else if (page < Math.ceil(totalCount / rowsPerPage) - 1) {
      // Load next page and go to first item
      setPendingIndexAfterPageLoad("first");
      setPage(page + 1);
    }
  };

  // Calculate global index for display
  const globalIndex = page * rowsPerPage + selectedResultIndex;

  // Format messages as JSON for display in template modal
  const messagesJson = useMemo(() => {
    if (!prompt?.messages) {
      return "";
    }
    return JSON.stringify(prompt.messages, null, 2);
  }, [prompt?.messages]);

  if (!promptDetails) {
    return null;
  }

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: "95%",
        },
      }}
    >
      <Box className="h-full flex flex-col">
        {/* Header */}
        <Box className="p-6 border-b border-gray-200 bg-gray-50">
          <Box className="flex items-center justify-between mb-4">
            <Box className="flex-1">
              <Box className="flex items-center gap-2 mb-1">
                <Typography variant="h5" className="font-semibold text-gray-900">
                  {promptDetails && (promptDetails.prompt_type === "saved" || !promptDetails.prompt_type)
                    ? `${promptDetails.prompt_name || 'Unknown'} (v${promptDetails.prompt_version || '?'})`
                    : promptDetails?.prompt_name || "Unsaved Prompt"}
                </Typography>
                {promptDetails?.prompt_type === "unsaved" && (
                  <Chip label="Unsaved" size="small" sx={{ backgroundColor: "#fff3e0", color: "#f57c00", fontWeight: 600 }} />
                )}
                {promptDetails && (promptDetails.prompt_type === "saved" || !promptDetails.prompt_type) && promptDetails.prompt_name && promptDetails.prompt_version && (
                  <Link
                    component={RouterLink}
                    to={`/tasks/${taskId}/prompts/${promptDetails.prompt_name}/versions/${promptDetails.prompt_version}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm"
                    sx={{ textDecoration: "none" }}
                  >
                    <OpenInNewIcon sx={{ fontSize: 16 }} />
                    <Typography variant="caption" className="font-medium">
                      View in Prompt Management
                    </Typography>
                  </Link>
                )}
              </Box>
            </Box>
            <IconButton onClick={onClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>

          {isPromptLoading && !unsavedPromptConfig ? (
            <Box className="flex justify-center py-4">
              <CircularProgress size={24} />
            </Box>
          ) : prompt ? (
            <>
              {/* Prompt Version Details */}
              <Box className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
                <Box className="flex items-center justify-start">
                  <Button
                    variant="outlined"
                    startIcon={<OpenInFullIcon />}
                    onClick={() => setTemplateModalOpen(true)}
                    size="small"
                  >
                    View Template
                  </Button>
                </Box>
                <Box>
                  <Typography variant="caption" className="text-gray-500 font-medium">
                    Created At
                  </Typography>
                  <Typography variant="body2" className="text-gray-900">
                    {prompt.created_at ? formatUTCTimestamp(prompt.created_at) : "N/A"}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" className="text-gray-500 font-medium">
                    Model
                  </Typography>
                  <Typography variant="body2" className="text-gray-900 font-mono">
                    {prompt.model_name}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" className="text-gray-500 font-medium">
                    Provider
                  </Typography>
                  <Typography variant="body2" className="text-gray-900">
                    {prompt.model_provider}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" className="text-gray-500 font-medium">
                    Messages
                  </Typography>
                  <Typography variant="body2" className="text-gray-900">
                    {prompt.messages.length}
                  </Typography>
                </Box>
              </Box>
            </>
          ) : (
            <Typography variant="body2" className="text-gray-500">
              Prompt details not available
            </Typography>
          )}
        </Box>

        {/* Prompt Details Section */}
        <Box className="p-6 border-b border-gray-200 bg-white">
          <Typography variant="h6" className="font-semibold text-gray-900 mb-4">
            Evaluation Performance
          </Typography>
          <Box className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6 gap-4">
            {promptDetails.eval_results.map((evalResult) => {
              const percentage = (evalResult.pass_count / evalResult.total_count) * 100;

              return (
                <Box key={`${evalResult.eval_name}-${evalResult.eval_version}`} className="p-4 border border-gray-200 rounded">
                  <Box className="flex justify-between items-center mb-2">
                    <Link
                      component={RouterLink}
                      to={`/tasks/${taskId}/evaluators/${evalResult.eval_name}/versions/${evalResult.eval_version}`}
                      sx={{ textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
                    >
                      <Typography variant="subtitle2" className="font-medium text-gray-800">
                        {evalResult.eval_name} (v{evalResult.eval_version})
                      </Typography>
                    </Link>
                    <Typography variant="body2" className="font-semibold text-gray-700">
                      {percentage.toFixed(0)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={percentage}
                    className="h-2 rounded mb-2"
                    sx={{
                      backgroundColor: "#ef4444",
                      "& .MuiLinearProgress-bar": {
                        backgroundColor: "#10b981",
                      },
                    }}
                  />
                  <Typography variant="caption" className="text-gray-600">
                    {evalResult.pass_count} / {evalResult.total_count} test cases passed
                  </Typography>
                </Box>
              );
            })}
          </Box>
        </Box>

        {/* Test Cases Table */}
        <Box className="flex-1 flex flex-col overflow-hidden p-6">
          <Typography variant="h6" className="font-semibold text-gray-900 mb-4">
            Test Case Results
          </Typography>
          <Box className="flex-1 overflow-hidden">
            <TableContainer component={Paper} elevation={1} sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
              <Box sx={{ flexGrow: 1, overflow: "auto" }}>
                <Table stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell className="font-semibold">Input Variables</TableCell>
                      <TableCell className="font-semibold">Rendered Prompt</TableCell>
                      <TableCell className="font-semibold">Output</TableCell>
                      <TableCell className="font-semibold" align="center">
                        Evaluation Results
                      </TableCell>
                      <TableCell className="font-semibold" align="right">
                        Cost
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {isResultsLoading ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          <Box className="py-8">
                            <CircularProgress size={32} />
                            <Typography variant="body2" className="mt-2 text-gray-600">
                              Loading results...
                            </Typography>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ) : results.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          <Typography variant="body2" className="py-8 text-gray-600 italic">
                            No test case results available yet
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      results.map((result, idx) => {
                        // Sort evals by name for consistent ordering across rows
                        const sortedEvals = [...result.evals].sort((a, b) =>
                          a.eval_name.localeCompare(b.eval_name)
                        );
                        const passedCount = sortedEvals.filter((e) => e.eval_results && e.eval_results.score >= 0.5).length;
                        const totalCount = sortedEvals.length;

                        return (
                          <TableRow
                            key={`${result.dataset_row_id}-${idx}`}
                            hover
                            onClick={() => handleRowClick(idx)}
                            sx={{ cursor: "pointer" }}
                          >
                            <TableCell>
                              <Typography
                                variant="body2"
                                className="text-gray-700 text-xs"
                                sx={{
                                  overflow: "hidden",
                                  display: "-webkit-box",
                                  WebkitLineClamp: 4,
                                  WebkitBoxOrient: "vertical",
                                  maxWidth: "250px",
                                }}
                              >
                                {result.prompt_input_variables
                                  .map((v) => `${v.variable_name}: ${v.value}`)
                                  .join("\n")}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Typography
                                variant="body2"
                                className="text-gray-700 text-xs"
                                sx={{
                                  overflow: "hidden",
                                  display: "-webkit-box",
                                  WebkitLineClamp: 4,
                                  WebkitBoxOrient: "vertical",
                                  maxWidth: "300px",
                                }}
                              >
                                {result.rendered_prompt || "No prompt"}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Typography
                                variant="body2"
                                className="text-gray-700 text-xs"
                                sx={{
                                  overflow: "hidden",
                                  display: "-webkit-box",
                                  WebkitLineClamp: 4,
                                  WebkitBoxOrient: "vertical",
                                  maxWidth: "300px",
                                }}
                              >
                                {result.output?.content || (result.output?.tool_calls && result.output.tool_calls.length > 0 ? `${result.output.tool_calls.length} tool call(s)` : "No output yet")}
                              </Typography>
                            </TableCell>
                            <TableCell align="center">
                              <Box className="flex flex-col gap-1 items-center">
                                <Typography variant="caption" className="font-medium">
                                  {passedCount} / {totalCount} passed
                                </Typography>
                                <Box className="flex gap-1 flex-wrap justify-center">
                                  {sortedEvals.map((evalExec, eidx) => {
                                    const passed = evalExec.eval_results && evalExec.eval_results.score >= 0.5;
                                    return (
                                      <Chip
                                        key={eidx}
                                        label={`${evalExec.eval_name} (v${evalExec.eval_version})`}
                                        size="small"
                                        color={passed ? "success" : "error"}
                                        sx={{ fontSize: "0.65rem", height: "20px" }}
                                      />
                                    );
                                  })}
                                </Box>
                              </Box>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2" className="font-mono text-xs">
                                ${result.total_cost || "0.00"}
                              </Typography>
                            </TableCell>
                          </TableRow>
                        );
                      })
                    )}
                  </TableBody>
                </Table>
              </Box>
              <TablePagination
                rowsPerPageOptions={[5, 10, 25, 50]}
                component="div"
                count={totalCount}
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={handleChangePage}
                onRowsPerPageChange={handleChangeRowsPerPage}
                sx={{ borderTop: 1, borderColor: "divider", flexShrink: 0 }}
              />
            </TableContainer>
          </Box>
        </Box>
      </Box>

      {/* Prompt Template Modal */}
      <Dialog open={templateModalOpen} onClose={() => setTemplateModalOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box className="flex items-center justify-between">
            <Typography variant="h6" className="font-semibold">
              Prompt Template - {promptDetails && (promptDetails.prompt_type === "saved" || !promptDetails.prompt_type)
                ? `${promptDetails.prompt_name || 'Unknown'} (v${promptDetails.prompt_version || '?'})`
                : promptDetails?.prompt_name || "Unsaved Prompt"}
            </Typography>
            <IconButton onClick={() => setTemplateModalOpen(false)} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent dividers>
          {isPromptLoading && !unsavedPromptConfig ? (
            <Box className="flex justify-center py-8">
              <CircularProgress />
            </Box>
          ) : prompt ? (
            <>
              {/* Model Configuration */}
              <Box className="mb-6">
                <Typography variant="subtitle1" className="font-semibold text-gray-900 mb-3">
                  Model Configuration
                </Typography>
                <Box className="grid grid-cols-2 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded">
                  <Box>
                    <Typography variant="caption" className="text-gray-500 font-medium">
                      Model
                    </Typography>
                    <Typography variant="body2" className="text-gray-900 font-mono">
                      {prompt.model_name}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" className="text-gray-500 font-medium">
                      Provider
                    </Typography>
                    <Typography variant="body2" className="text-gray-900 font-mono">
                      {prompt.model_provider}
                    </Typography>
                  </Box>
                  {prompt.config?.temperature !== undefined && (
                    <Box>
                      <Typography variant="caption" className="text-gray-500 font-medium">
                        Temperature
                      </Typography>
                      <Typography variant="body2" className="text-gray-900 font-mono">
                        {prompt.config.temperature}
                      </Typography>
                    </Box>
                  )}
                  {prompt.config?.max_tokens !== undefined && (
                    <Box>
                      <Typography variant="caption" className="text-gray-500 font-medium">
                        Max Tokens
                      </Typography>
                      <Typography variant="body2" className="text-gray-900 font-mono">
                        {prompt.config.max_tokens}
                      </Typography>
                    </Box>
                  )}
                </Box>
              </Box>

              {/* Messages */}
              <Box>
                <Typography variant="subtitle1" className="font-semibold text-gray-900 mb-3">
                  Messages
                </Typography>
                <Box>
                  <NunjucksHighlightedTextField
                    value={messagesJson}
                    onChange={() => {}} // Read-only, no-op
                    disabled
                    multiline
                    minRows={4}
                    maxRows={30}
                    size="small"
                  />
                </Box>
              </Box>
            </>
          ) : (
            <Typography variant="body2" className="text-gray-500 text-center py-8">
              Prompt template not available
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTemplateModalOpen(false)} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Prompt Result Detail Modal */}
      {selectedResultIndex >= 0 && selectedResultIndex < results.length && promptDetails && (
        <PromptResultDetailModal
          open={detailModalOpen}
          onClose={handleCloseDetailModal}
          promptName={promptDetails.prompt_name || undefined}
          promptVersion={promptDetails.prompt_version || undefined}
          inputVariables={results[selectedResultIndex].prompt_input_variables}
          renderedPrompt={results[selectedResultIndex].rendered_prompt}
          output={results[selectedResultIndex].output}
          evals={results[selectedResultIndex].evals}
          currentIndex={globalIndex}
          totalCount={totalCount}
          onPrevious={handlePrevious}
          onNext={handleNext}
          onViewEvalInputs={handleViewEvalInputs}
        />
      )}

      {/* Eval Inputs Dialog - rendered as sibling to avoid nesting in Modal */}
      <EvalInputsDialog
        open={evalInputsDialogOpen}
        onClose={handleCloseEvalInputsDialog}
        evalExecution={selectedEvalExecution}
      />
    </Drawer>
  );
};
