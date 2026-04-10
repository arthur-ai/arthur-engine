import SearchIcon from "@mui/icons-material/Search";
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
import { alpha } from "@mui/material/styles";
import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { CreateExperimentModal } from "./create-experiment-modal";
import { PromptExperimentsEmptyState } from "./PromptExperimentsEmptyState";
import { PromptExperimentsTable, PromptExperiment, PromptConfig } from "./PromptExperimentsTable";
import { PromptExperimentsViewHeader } from "./PromptExperimentsViewHeader";

import { getContentHeight } from "@/constants/layout";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { usePromptExperiments } from "@/hooks/usePromptExperiments";
import { formatCurrency } from "@/utils/formatters";
import { getStatusChipSx } from "@/utils/statusChipStyles";

interface PromptExperimentsViewProps {
  onRegisterCreate?: (fn: () => void) => void;
  onRegisterCreateFromExisting?: (fn: () => void) => void;
}

export const PromptExperimentsView: React.FC<PromptExperimentsViewProps> = ({ onRegisterCreate, onRegisterCreateFromExisting }) => {
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { defaultCurrency } = useDisplaySettings();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSelectExistingModalOpen, setIsSelectExistingModalOpen] = useState(false);
  const [selectedExperimentId, setSelectedExperimentId] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [searchText, setSearchText] = useState("");
  const debouncedSearchText = useDebouncedValue(searchText, 300);
  const [modalSearchText, setModalSearchText] = useState("");

  const {
    experiments,
    totalCount = 0,
    isLoading,
    error,
    refetch,
  } = usePromptExperiments(taskId, page, rowsPerPage, debouncedSearchText || undefined);
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
    const hasRunningExperiments = experiments.some((exp) => exp.status === "running" || exp.status === "queued");

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

  const onRegisterCreateRef = useRef(onRegisterCreate);
  const onRegisterCreateFromExistingRef = useRef(onRegisterCreateFromExisting);
  useEffect(() => {
    onRegisterCreateRef.current?.(handleCreateExperiment);
    onRegisterCreateFromExistingRef.current?.(handleCreateFromExisting);
  }, []);

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

  return (
    <>
      <Box className="w-full grid overflow-hidden" style={{ height: getContentHeight(), gridTemplateRows: "auto 1fr" }}>
        {onRegisterCreate ? (
          <Box
            sx={{
              px: 3,
              py: 2,
              borderBottom: 1,
              borderColor: "divider",
              backgroundColor: "background.paper",
            }}
          >
            <TextField
              placeholder="Search experiments by name, description, prompt, or dataset..."
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
            <PromptExperimentsViewHeader
              onCreateExperiment={handleCreateExperiment}
              onCreateFromExisting={handleCreateFromExisting}
              searchValue={searchText}
              onSearchChange={handleSearchChange}
            />
          </Box>
        )}

        <Box className="overflow-auto min-h-0">
          {isLoading ? (
            <Box className="flex items-center justify-center h-full">
              <Typography variant="body2" color="text.secondary">
                Loading experiments...
              </Typography>
            </Box>
          ) : error ? (
            <Box className="flex items-center justify-center h-full">
              <Typography variant="body2" color="error.main">
                {error.message}
              </Typography>
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
      <Dialog open={isSelectExistingModalOpen} onClose={handleCloseSelectExistingModal} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box>
            <Typography variant="h6" className="font-semibold mb-1">
              Select an Existing Experiment
            </Typography>
            <Typography variant="body2" color="text.secondary">
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
              variant="filled"
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
              const promptMatches = exp.prompt_configs?.some((config: PromptConfig) => {
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
                  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>
                    {experiments.length === 0 ? "No experiments available to clone." : "No experiments match your search."}
                  </Typography>
                </Box>
              );
            }

            return (
              <List sx={{ py: 0, border: 1, borderColor: "divider", borderRadius: 1 }}>
                {filteredExperiments.map((experiment, index) => (
                  <React.Fragment key={experiment.id}>
                    {index > 0 && <Divider />}
                    <ListItem disablePadding>
                      <ListItemButton
                        onClick={() => handleSelectExistingExperiment(experiment)}
                        sx={{
                          py: 2,
                          px: 2,
                          "&:hover": {
                            backgroundColor: "action.hover",
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
                              <Chip label={experiment.status} size="small" sx={getStatusChipSx(experiment.status)} />
                            </Box>
                          }
                          secondary={
                            <Box>
                              {experiment.description && (
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                  {experiment.description}
                                </Typography>
                              )}
                              <Box className="flex flex-col gap-2">
                                <Box className="flex flex-wrap gap-1">
                                  <Typography variant="caption" color="text.secondary" className="mr-2">
                                    <strong>Prompts:</strong>
                                  </Typography>
                                  {experiment.prompt_configs?.map((config: PromptConfig, idx: number) => (
                                    <Chip
                                      key={idx}
                                      label={config.type === "saved" ? `${config.name} (v${config.version})` : config.auto_name || "Unsaved Prompt"}
                                      size="small"
                                      sx={{
                                        height: "20px",
                                        fontSize: "0.688rem",
                                        backgroundColor: (theme) =>
                                          config.type === "saved" ? alpha(theme.palette.info.main, 0.12) : alpha(theme.palette.warning.main, 0.12),
                                        borderColor: config.type === "saved" ? "primary.main" : "warning.main",
                                      }}
                                    />
                                  ))}
                                </Box>
                                <Box className="flex gap-4 text-sm">
                                  <Typography variant="caption" color="text.secondary">
                                    <strong>Rows:</strong> {experiment.total_rows}
                                  </Typography>
                                  {experiment.total_cost && (
                                    <Typography variant="caption" color="text.secondary">
                                      <strong>Cost:</strong> {formatCurrency(parseFloat(experiment.total_cost), defaultCurrency)}
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

      <CreateExperimentModal templateId={selectedExperimentId ?? undefined} open={isModalOpen} onClose={handleCloseModal} />
    </>
  );
};
