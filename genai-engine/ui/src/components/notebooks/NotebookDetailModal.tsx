import CloseIcon from "@mui/icons-material/Close";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import React from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useNotebook, useNotebookHistory } from "@/hooks/useNotebooks";

interface NotebookDetailModalProps {
  open: boolean;
  notebookId: string | null;
  onClose: () => void;
}

const NotebookDetailModal: React.FC<NotebookDetailModalProps> = ({
  open,
  notebookId,
  onClose,
}) => {
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { notebook, isLoading, error } = useNotebook(notebookId || undefined);
  const { experiments, isLoading: isLoadingHistory } = useNotebookHistory(
    notebookId || undefined,
    0,
    10
  );

  const getStatusChipSx = (status: string) => {
    const colorMap: Record<string, any> = {
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

  const handleExperimentClick = (experimentId: string) => {
    navigate(`/tasks/${taskId}/prompt-experiments/${experimentId}`);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Notebook Details
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent dividers>
        {isLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        ) : error || !notebook ? (
          <Box sx={{ py: 4, textAlign: "center" }}>
            <Typography color="error">Failed to load notebook details</Typography>
          </Box>
        ) : (
          <Stack spacing={3}>
            {/* Metadata Section */}
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, color: "text.secondary" }}>
                METADATA
              </Typography>
              <Stack spacing={1.5}>
                <Box>
                  <Typography variant="caption" sx={{ color: "text.secondary" }}>
                    Name
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {notebook.name}
                  </Typography>
                </Box>
                {notebook.description && (
                  <Box>
                    <Typography variant="caption" sx={{ color: "text.secondary" }}>
                      Description
                    </Typography>
                    <Typography variant="body2">{notebook.description}</Typography>
                  </Box>
                )}
                <Box sx={{ display: "flex", gap: 3 }}>
                  <Box>
                    <Typography variant="caption" sx={{ color: "text.secondary" }}>
                      Created
                    </Typography>
                    <Typography variant="body2">
                      {new Date(notebook.created_at).toLocaleString()}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ color: "text.secondary" }}>
                      Updated
                    </Typography>
                    <Typography variant="body2">
                      {new Date(notebook.updated_at).toLocaleString()}
                    </Typography>
                  </Box>
                </Box>
              </Stack>
            </Box>

            <Divider />

            {/* Configuration Section */}
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, color: "text.secondary" }}>
                CONFIGURATION
              </Typography>
              
              {!notebook.state?.prompt_configs && !notebook.state?.dataset_ref && !notebook.state?.eval_list ? (
                <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic" }}>
                  No configuration set
                </Typography>
              ) : (
                <Stack spacing={2}>
                  {/* Prompts */}
                  {notebook.state?.prompt_configs && notebook.state.prompt_configs.length > 0 && (
                    <Box>
                      <Typography variant="caption" sx={{ color: "text.secondary", mb: 0.5, display: "block" }}>
                        Prompts ({notebook.state.prompt_configs.length})
                      </Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                        {notebook.state.prompt_configs.map((config: any, idx: number) => (
                          <Chip
                            key={idx}
                            label={
                              config.type === "saved"
                                ? `${config.name} (v${config.version})`
                                : config.auto_name || "Unsaved Prompt"
                            }
                            size="small"
                            sx={{
                              backgroundColor: config.type === "saved" ? "#e3f2fd" : "#fff3e0",
                              borderColor: config.type === "saved" ? "#2196f3" : "#ff9800",
                            }}
                            onClick={
                              config.type === "saved"
                                ? () => {
                                    navigate(`/tasks/${taskId}/prompts/${config.name}/versions/${config.version}`);
                                    onClose();
                                  }
                                : undefined
                            }
                            onDelete={
                              config.type === "saved"
                                ? () => {
                                    navigate(`/tasks/${taskId}/prompts/${config.name}/versions/${config.version}`);
                                    onClose();
                                  }
                                : undefined
                            }
                            deleteIcon={config.type === "saved" ? <OpenInNewIcon fontSize="small" /> : undefined}
                          />
                        ))}
                      </Stack>
                    </Box>
                  )}

                  {/* Dataset */}
                  {notebook.state?.dataset_ref && (
                    <Box>
                      <Typography variant="caption" sx={{ color: "text.secondary", mb: 0.5, display: "block" }}>
                        Dataset
                      </Typography>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {notebook.state.dataset_ref.name || notebook.state.dataset_ref.id}
                        </Typography>
                        {notebook.state.dataset_ref.version && (
                          <Chip label={`v${notebook.state.dataset_ref.version}`} size="small" />
                        )}
                        {notebook.state.dataset_ref.id && (
                          <IconButton
                            size="small"
                            onClick={() => {
                              navigate(`/tasks/${taskId}/datasets/${notebook.state!.dataset_ref!.id}`);
                              onClose();
                            }}
                            sx={{ padding: 0.5 }}
                          >
                            <OpenInNewIcon fontSize="small" />
                          </IconButton>
                        )}
                      </Box>
                    </Box>
                  )}

                  {/* Evaluators */}
                  {notebook.state?.eval_list && notebook.state.eval_list.length > 0 && (
                    <Box>
                      <Typography variant="caption" sx={{ color: "text.secondary", mb: 0.5, display: "block" }}>
                        Evaluators ({notebook.state.eval_list.length})
                      </Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                        {notebook.state.eval_list.map((evalRef: any, idx: number) => (
                          <Chip
                            key={idx}
                            label={`${evalRef.name} (v${evalRef.version})`}
                            size="small"
                            sx={{
                              backgroundColor: "#e8f5e9",
                              borderColor: "#4caf50",
                            }}
                            onClick={() => {
                              navigate(`/tasks/${taskId}/evaluators/${evalRef.name}/versions/${evalRef.version}`);
                              onClose();
                            }}
                            onDelete={() => {
                              navigate(`/tasks/${taskId}/evaluators/${evalRef.name}/versions/${evalRef.version}`);
                              onClose();
                            }}
                            deleteIcon={<OpenInNewIcon fontSize="small" />}
                          />
                        ))}
                      </Stack>
                    </Box>
                  )}

                  {/* Variable Mappings */}
                  {notebook.state?.prompt_variable_mapping && notebook.state.prompt_variable_mapping.length > 0 && (
                    <Box>
                      <Typography variant="caption" sx={{ color: "text.secondary", mb: 0.5, display: "block" }}>
                        Variable Mappings ({notebook.state.prompt_variable_mapping.length})
                      </Typography>
                      <Stack spacing={0.5}>
                        {notebook.state.prompt_variable_mapping.map((mapping: any, idx: number) => (
                          <Typography key={idx} variant="body2" sx={{ fontSize: "0.813rem" }}>
                            <Box component="span" sx={{ fontWeight: 600, fontFamily: "monospace" }}>
                              {mapping.variable_name}
                            </Box>
                            {" → "}
                            <Box component="span" sx={{ color: "text.secondary" }}>
                              {mapping.source?.dataset_column?.name || "Unknown"}
                            </Box>
                          </Typography>
                        ))}
                      </Stack>
                    </Box>
                  )}
                </Stack>
              )}
            </Box>

            <Divider />

            {/* Experiment History Section */}
            <Box>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, color: "text.secondary" }}>
                  EXPERIMENT HISTORY (Recent 10)
                </Typography>
                {experiments.length > 0 && (
                  <Typography variant="caption" color="text.secondary">
                    {experiments.length} experiment{experiments.length !== 1 ? "s" : ""}
                  </Typography>
                )}
              </Box>

              {isLoadingHistory ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : experiments.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic", py: 2 }}>
                  No experiments run yet
                </Typography>
              ) : (
                <TableContainer sx={{ maxHeight: 400 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>Created</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Rows</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Cost</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600 }}>
                          Actions
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {experiments.map((experiment: any) => (
                        <TableRow
                          key={experiment.id}
                          hover
                          sx={{ cursor: "pointer" }}
                          onClick={() => handleExperimentClick(experiment.id)}
                        >
                          <TableCell>
                            <Typography variant="body2">
                              {new Date(experiment.created_at).toLocaleString()}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={experiment.status}
                              size="small"
                              sx={getStatusChipSx(experiment.status)}
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {experiment.completed_rows}/{experiment.total_rows}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {experiment.total_cost ? `$${experiment.total_cost}` : "—"}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleExperimentClick(experiment.id);
                              }}
                            >
                              <OpenInNewIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          </Stack>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default NotebookDetailModal;

