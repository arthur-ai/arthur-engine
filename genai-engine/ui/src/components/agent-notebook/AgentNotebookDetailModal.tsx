import CloseIcon from "@mui/icons-material/Close";
import EditIcon from "@mui/icons-material/Edit";
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
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useAgenticNotebook } from "./hooks/useAgenticNotebook";
import { useUpdateAgenticNotebook } from "./hooks/useUpdateAgenticNotebook";

import { getStatusChipSx } from "@/utils/statusChipStyles";

interface AgentNotebookDetailModalProps {
  open: boolean;
  notebookId: string | null;
  onClose: () => void;
}

const AgentNotebookDetailModal: React.FC<AgentNotebookDetailModalProps> = ({ open, notebookId, onClose }) => {
  const navigate = useNavigate();
  const { id: taskId } = useParams<{ id: string }>();
  const { data: notebook, isLoading } = useAgenticNotebook(notebookId ?? "");
  const updateMutation = useUpdateAgenticNotebook();

  const [isRenaming, setIsRenaming] = useState(false);
  const [newNotebookName, setNewNotebookName] = useState("");
  const isSavingRenameRef = useRef(false);

  useEffect(() => {
    if (notebook?.name) setNewNotebookName(notebook.name);
  }, [notebook?.name]);

  const handleStartRename = () => {
    setNewNotebookName(notebook?.name ?? "");
    setIsRenaming(true);
  };

  const handleCancelRename = () => {
    setIsRenaming(false);
    setNewNotebookName(notebook?.name ?? "");
  };

  const handleSaveRename = async () => {
    if (isSavingRenameRef.current) return;
    const trimmed = newNotebookName.trim();
    if (!trimmed || !notebookId || trimmed === notebook?.name) {
      handleCancelRename();
      return;
    }
    isSavingRenameRef.current = true;
    setIsRenaming(false);
    try {
      await updateMutation.mutateAsync({ notebookId, request: { name: trimmed, description: notebook?.description } });
    } finally {
      isSavingRenameRef.current = false;
    }
  };

  const handleLaunchNotebook = () => {
    if (taskId && notebookId) {
      navigate(`/tasks/${taskId}/agentic-notebooks/${notebookId}`);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {isRenaming ? (
            <TextField
              variant="filled"
              size="small"
              value={newNotebookName}
              onChange={(e) => setNewNotebookName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSaveRename();
                else if (e.key === "Escape") handleCancelRename();
              }}
              onBlur={handleSaveRename}
              autoFocus
              sx={{
                "& .MuiInputBase-root": { fontSize: "1.25rem", fontWeight: 600 },
              }}
            />
          ) : (
            <>
              <Typography variant="h6" component="span">
                {notebook?.name || "Notebook Details"}
              </Typography>
              {notebook && (
                <IconButton
                  size="small"
                  onClick={handleStartRename}
                  sx={{
                    padding: 0.5,
                    color: "text.secondary",
                    "&:hover": { color: "text.primary", backgroundColor: "action.hover" },
                  }}
                >
                  <EditIcon sx={{ fontSize: "1rem" }} />
                </IconButton>
              )}
            </>
          )}
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Button variant="contained" size="small" startIcon={<LaunchIcon />} onClick={handleLaunchNotebook} disabled={!notebookId}>
            Launch
          </Button>
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
        ) : !notebook ? (
          <Box sx={{ py: 4, textAlign: "center" }}>
            <Typography color="error">Failed to load notebook details</Typography>
          </Box>
        ) : (
          <Stack spacing={3}>
            {/* Metadata */}
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, color: "text.secondary" }}>
                METADATA
              </Typography>
              <Stack spacing={1.5}>
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
                    <Typography variant="body2">{new Date(notebook.created_at).toLocaleString()}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ color: "text.secondary" }}>
                      Updated
                    </Typography>
                    <Typography variant="body2">{new Date(notebook.updated_at).toLocaleString()}</Typography>
                  </Box>
                </Box>
              </Stack>
            </Box>

            <Divider />

            {/* Experiment History */}
            <Box>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, color: "text.secondary" }}>
                  EXPERIMENT HISTORY
                </Typography>
                {notebook.experiments.length > 0 && (
                  <Typography variant="caption" color="text.secondary">
                    {notebook.experiments.length} run{notebook.experiments.length !== 1 ? "s" : ""}
                  </Typography>
                )}
              </Box>
              {notebook.experiments.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ fontStyle: "italic", py: 2 }}>
                  No experiments run yet
                </Typography>
              ) : (
                <TableContainer sx={{ maxHeight: 300 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>Name</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Created</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {notebook.experiments.map((experiment) => (
                        <TableRow
                          key={experiment.id}
                          hover
                          sx={{ cursor: "pointer" }}
                          onClick={() => {
                            navigate(`/tasks/${taskId}/agent-experiments/${experiment.id}`);
                            onClose();
                          }}
                        >
                          <TableCell>
                            <Typography variant="body2">{experiment.name}</Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={experiment.status} size="small" sx={getStatusChipSx(experiment.status)} />
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
          </Stack>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default AgentNotebookDetailModal;
