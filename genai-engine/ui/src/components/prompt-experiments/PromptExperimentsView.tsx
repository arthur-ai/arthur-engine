import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Typography,
  Chip,
  Divider,
  TextField,
  InputAdornment,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { PromptExperimentsEmptyState } from "./PromptExperimentsEmptyState";
import { PromptExperimentsTable, PromptExperiment } from "./PromptExperimentsTable";
import { PromptExperimentsViewHeader } from "./PromptExperimentsViewHeader";
import { CreateExperimentModal, ExperimentFormData } from "./CreateExperimentModal";

import { getContentHeight } from "@/constants/layout";
import { usePromptExperiments, useCreateExperiment, usePromptExperiment } from "@/hooks/usePromptExperiments";
import type { PromptExperimentDetail } from "@/lib/api-client/api-client";

export const PromptExperimentsView: React.FC = () => {
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSelectExistingModalOpen, setIsSelectExistingModalOpen] = useState(false);
  const [selectedExperimentId, setSelectedExperimentId] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [searchText, setSearchText] = useState("");
  const [debouncedSearchText, setDebouncedSearchText] = useState("");
  const [modalSearchText, setModalSearchText] = useState("");

  // Debounce search text to avoid too many API calls
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchText(searchText);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchText]);

  const { experiments, totalCount = 0, isLoading, error, refetch } = usePromptExperiments(
    taskId,
    page,
    rowsPerPage,
    debouncedSearchText || undefined
  );
  const createExperiment = useCreateExperiment(taskId);

  // Fetch full experiment details when cloning
  const { experiment: experimentToClone, isLoading: isLoadingExperiment } = usePromptExperiment(selectedExperimentId || undefined);

  // Refetch data when window gains focus
  useEffect(() => {
    const handleFocus = () => {
      refetch();
    };

    window.addEventListener("focus", handleFocus);
    return () => {
      window.removeEventListener("focus", handleFocus);
    };
  }, [refetch]);

  // Auto-refresh when any experiment is running
  useEffect(() => {
    // Check if any experiment is in a running state (queued or running)
    const hasRunningExperiments = experiments.some(
      (exp) => exp.status === "running" || exp.status === "queued"
    );

    if (!hasRunningExperiments) {
      return;
    }

    // Set up interval to refresh every 1 second
    const intervalId = setInterval(() => {
      refetch();
    }, 1000);

    // Clean up interval when component unmounts or no experiments are running
    return () => {
      clearInterval(intervalId);
    };
  }, [experiments, refetch]);

  const handleCreateExperiment = () => {
    setSelectedExperimentId(null);
    setIsModalOpen(true);
  };

  const handleCreateFromExisting = () => {
    setIsSelectExistingModalOpen(true);
  };

  const handleSelectExistingExperiment = (experiment: PromptExperiment) => {
    setSelectedExperimentId(experiment.id);
    setIsSelectExistingModalOpen(false);
    // Open modal after experiment details are fetched
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedExperimentId(null);
  };

  const handleCloseSelectExistingModal = () => {
    setIsSelectExistingModalOpen(false);
    setModalSearchText("");
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

  const handleSearchChange = (value: string) => {
    setSearchText(value);
    setPage(0); // Reset to first page when searching
  };

  const getStatusChipSx = (status: PromptExperiment["status"]) => {
    const colorMap = {
      queued: { color: "text.secondary", borderColor: "text.secondary" },
      running: { color: "primary.main", borderColor: "primary.main" },
      evaluating: { color: "info.main", borderColor: "info.main" },
      completed: { color: "success.main", borderColor: "success.main" },
      failed: { color: "error.main", borderColor: "error.main" },
    };
    const colors = colorMap[status] || colorMap.queued;
    return {
      backgroundColor: "transparent",
      color: colors.color,
      borderColor: colors.borderColor,
      borderWidth: 1,
      borderStyle: "solid",
      textTransform: "capitalize",
    };
  };

  return (
    <>
      <Box
        className="w-full grid overflow-hidden"
        style={{ height: getContentHeight(), gridTemplateRows: "auto 1fr" }}
      >
        <Box className="px-6 pt-6 pb-4 border-b border-gray-200 bg-white">
          <PromptExperimentsViewHeader
            onCreateExperiment={handleCreateExperiment}
            onCreateFromExisting={handleCreateFromExisting}
            searchValue={searchText}
            onSearchChange={handleSearchChange}
          />
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

      {/* Select Existing Experiment Modal */}
      <Dialog
        open={isSelectExistingModalOpen}
        onClose={handleCloseSelectExistingModal}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box>
            <Typography variant="h6" className="font-semibold mb-1">
              Select an Existing Experiment
            </Typography>
            <Typography variant="body2" className="text-gray-600">
              Choose an experiment to use as a template. All settings will be copied to your new experiment.
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent dividers>
          <Box className="mb-4">
            <TextField
              placeholder="Search by name, description, or prompt..."
              value={modalSearchText}
              onChange={(e) => setModalSearchText(e.target.value)}
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
          {(() => {
            const filteredExperiments = experiments.filter((exp) => {
              if (!modalSearchText) return true;
              const searchLower = modalSearchText.toLowerCase();

              // Search in prompt configs
              const promptMatches = exp.prompt_configs?.some((config: any) => {
                if (config.type === "saved") {
                  return config.name.toLowerCase().includes(searchLower);
                } else if (config.type === "unsaved" && config.auto_name) {
                  return config.auto_name.toLowerCase().includes(searchLower);
                }
                return false;
              });

              return (
                exp.name.toLowerCase().includes(searchLower) ||
                (exp.description && exp.description.toLowerCase().includes(searchLower)) ||
                promptMatches
              );
            });

            if (filteredExperiments.length === 0) {
              return (
                <Box className="py-8 text-center">
                  <Typography variant="body2" className="text-gray-500 italic">
                    {experiments.length === 0
                      ? "No experiments available to clone."
                      : "No experiments match your search."}
                  </Typography>
                </Box>
              );
            }

            return (
              <List sx={{ py: 0, border: 1, borderColor: 'divider', borderRadius: 1 }}>
                {filteredExperiments.map((experiment, index) => (
                <React.Fragment key={experiment.id}>
                  {index > 0 && <Divider />}
                  <ListItem disablePadding>
                    <ListItemButton
                      onClick={() => handleSelectExistingExperiment(experiment)}
                      sx={{
                        py: 2,
                        px: 2,
                        '&:hover': {
                          backgroundColor: 'action.hover',
                        },
                      }}
                    >
                      <ListItemText
                        disableTypography
                        primary={
                          <Box className="flex items-center gap-2 mb-1">
                            <Typography variant="subtitle1" className="font-semibold">
                              {experiment.name}
                            </Typography>
                            <Chip
                              label={experiment.status}
                              size="small"
                              sx={getStatusChipSx(experiment.status)}
                            />
                          </Box>
                        }
                        secondary={
                          <Box>
                            {experiment.description && (
                              <Typography variant="body2" className="text-gray-700 mb-2">
                                {experiment.description}
                              </Typography>
                            )}
                            <Box className="flex flex-col gap-2">
                              <Box className="flex flex-wrap gap-1">
                                <Typography variant="caption" className="text-gray-600 mr-2">
                                  <strong>Prompts:</strong>
                                </Typography>
                                {experiment.prompt_configs?.map((config: any, idx: number) => (
                                  <Chip
                                    key={idx}
                                    label={
                                      config.type === "saved"
                                        ? `${config.name} (v${config.version})`
                                        : config.auto_name || "Unsaved Prompt"
                                    }
                                    size="small"
                                    sx={{
                                      height: "20px",
                                      fontSize: "0.688rem",
                                      backgroundColor: config.type === "saved" ? "#e3f2fd" : "#fff3e0",
                                      borderColor: config.type === "saved" ? "#2196f3" : "#ff9800",
                                    }}
                                  />
                                ))}
                              </Box>
                              <Box className="flex gap-4 text-sm">
                                <Typography variant="caption" className="text-gray-600">
                                  <strong>Rows:</strong> {experiment.total_rows}
                                </Typography>
                                {experiment.total_cost && (
                                  <Typography variant="caption" className="text-gray-600">
                                    <strong>Cost:</strong> ${parseFloat(experiment.total_cost).toFixed(4)}
                                  </Typography>
                                )}
                              </Box>
                            </Box>
                          </Box>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
            );
          })()}
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={handleCloseSelectExistingModal} variant="outlined">
            Cancel
          </Button>
        </DialogActions>
      </Dialog>

      <CreateExperimentModal
        open={isModalOpen}
        onClose={handleCloseModal}
        onSubmit={handleSubmitExperiment}
        initialData={experimentToClone || undefined}
        isLoadingInitialData={isLoadingExperiment}
      />
    </>
  );
};
