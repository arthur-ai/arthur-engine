import CloseIcon from "@mui/icons-material/Close";
import LaunchIcon from "@mui/icons-material/Launch";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import React from "react";
import { useNavigate, useParams } from "react-router-dom";

import { EditableTitle } from "@/components/common";
import { useRagNotebook, useRagNotebookHistoryWithPolling, useUpdateRagNotebookMutation } from "@/hooks/useRagNotebooks";
import { getStatusChipSx } from "@/utils/statusChipStyles";

interface RagNotebookDetailModalProps {
  open: boolean;
  notebookId: string | null;
  onClose: () => void;
}

const RagNotebookDetailModal: React.FC<RagNotebookDetailModalProps> = ({ open, notebookId, onClose }) => {
  const navigate = useNavigate();
  const { id: taskId } = useParams<{ id: string }>();
  const { notebook, isLoading: isLoadingNotebook } = useRagNotebook(notebookId ?? undefined);
  const { experiments, isLoading: isLoadingHistory } = useRagNotebookHistoryWithPolling(notebookId ?? undefined);
  const updateMutation = useUpdateRagNotebookMutation();

  const handleLaunchNotebook = () => {
    if (taskId && notebookId) {
      navigate(`/tasks/${taskId}/rag-notebooks/${notebookId}`);
      onClose();
    }
  };

  const isLoading = isLoadingNotebook || isLoadingHistory;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth aria-labelledby="rag-notebook-detail-dialog-title">
      <DialogTitle id="rag-notebook-detail-dialog-title" sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <EditableTitle
          value={notebook?.name ?? ""}
          onSave={async (newName) => {
            if (notebookId) {
              await updateMutation.mutateAsync({ notebookId, request: { name: newName, description: notebook?.description } });
            }
          }}
          isPending={updateMutation.isPending}
          fallbackText="RAG Notebook Details"
          showEditButton={!!notebook}
        />
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Button variant="contained" size="small" startIcon={<LaunchIcon />} onClick={handleLaunchNotebook} disabled={!notebookId}>
            Launch
          </Button>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        {isLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {notebook?.description || "No description"}
              </Typography>
              <Box sx={{ display: "flex", gap: 3, mt: 2 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Created
                  </Typography>
                  <Typography variant="body2">{notebook?.created_at ? new Date(notebook.created_at).toLocaleString() : "—"}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Last Updated
                  </Typography>
                  <Typography variant="body2">{notebook?.updated_at ? new Date(notebook.updated_at).toLocaleString() : "—"}</Typography>
                </Box>
              </Box>
            </Box>

            <Divider sx={{ my: 2 }} />

            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                Experiment History
              </Typography>
              {experiments.length === 0 ? (
                <Box sx={{ py: 3, textAlign: "center" }}>
                  <Typography variant="body2" color="text.secondary">
                    No experiments have been run from this notebook yet.
                  </Typography>
                </Box>
              ) : (
                <TableContainer sx={{ maxHeight: 300 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>
                          <Typography variant="caption" sx={{ fontWeight: 600 }}>
                            Name
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption" sx={{ fontWeight: 600 }}>
                            Status
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption" sx={{ fontWeight: 600 }}>
                            Configs
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption" sx={{ fontWeight: 600 }}>
                            Created
                          </Typography>
                        </TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {experiments.map((experiment) => (
                        <TableRow key={experiment.id} hover>
                          <TableCell>
                            <Typography variant="body2">{experiment.name}</Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={experiment.status} size="small" sx={getStatusChipSx(experiment.status)} />
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">{experiment.rag_configs?.length || 0}</Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary">
                              {new Date(experiment.created_at).toLocaleString()}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default RagNotebookDetailModal;
