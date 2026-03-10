import WarningIcon from "@mui/icons-material/Warning";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MuiLink from "@mui/material/Link";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import React from "react";
import { Link } from "react-router-dom";

import { useTransformDependents } from "./hooks/useTransformDependents";

import { useTask } from "@/hooks/useTask";
import { TransformDependentRef } from "@/lib/api-client/api-client";

interface DeleteTransformDialogProps {
  transformId: string | null;
  onClose: () => void;
  onConfirm: () => void;
  isDeleting: boolean;
}

interface DependentSectionProps {
  label: string;
  items: TransformDependentRef[];
  buildLink: (id: string) => string;
  onClose: () => void;
}

const DependentSection: React.FC<DependentSectionProps> = ({ label, items, buildLink, onClose }) => {
  if (items.length === 0) return null;

  return (
    <Alert severity="error" sx={{ mb: 2 }}>
      <Typography variant="body2" sx={{ fontWeight: 500, mb: 1 }}>
        {label} ({items.length}):
      </Typography>
      <List dense disablePadding>
        {items.map((item) => (
          <ListItem key={item.id} disableGutters sx={{ py: 0 }}>
            <ListItemText
              primary={
                <MuiLink component={Link} to={buildLink(item.id)} onClick={onClose} variant="body2">
                  {item.name}
                </MuiLink>
              }
            />
          </ListItem>
        ))}
      </List>
    </Alert>
  );
};

const DeleteTransformDialog: React.FC<DeleteTransformDialogProps> = ({ transformId, onClose, onConfirm, isDeleting }) => {
  const { task } = useTask();
  const { dependents, isLoading } = useTransformDependents(transformId);

  const hasDependents =
    (dependents.continuous_evals?.length ?? 0) > 0 ||
    (dependents.agentic_experiments?.length ?? 0) > 0 ||
    (dependents.agentic_notebooks?.length ?? 0) > 0;

  const taskId = task?.id;

  return (
    <Dialog open={!!transformId} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ textAlign: "center", pb: 1 }}>
        <Box sx={{ display: "flex", justifyContent: "center", mb: 2 }}>
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: "50%",
              bgcolor: "error.light",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <WarningIcon sx={{ color: "error.main", fontSize: 24 }} />
          </Box>
        </Box>
        {isLoading ? "Delete Transform" : hasDependents ? "Cannot Delete Transform" : "Delete Transform"}
      </DialogTitle>

      <DialogContent>
        {isLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
            <CircularProgress size={24} />
          </Box>
        ) : hasDependents ? (
          <>
            <DependentSection
              label="Continuous Evals"
              items={dependents.continuous_evals ?? []}
              buildLink={(id) => `/tasks/${taskId}/continuous-evals/${id}`}
              onClose={onClose}
            />
            <DependentSection
              label="Agent Experiments"
              items={dependents.agentic_experiments ?? []}
              buildLink={(id) => `/tasks/${taskId}/agent-experiments/${id}`}
              onClose={onClose}
            />
            <DependentSection
              label="Agentic Notebooks"
              items={dependents.agentic_notebooks ?? []}
              buildLink={(id) => `/tasks/${taskId}/agentic-notebooks/${id}`}
              onClose={onClose}
            />

            <Typography variant="body2" color="text.secondary">
              Remove these references before deleting this transform.
            </Typography>
          </>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center" }}>
            Are you sure you want to delete this transform? This action cannot be undone.
          </Typography>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 3 }}>
        {isLoading ? (
          <Button onClick={onClose} variant="outlined">
            Cancel
          </Button>
        ) : hasDependents ? (
          <Button onClick={onClose} variant="outlined" fullWidth>
            Close
          </Button>
        ) : (
          <>
            <Button onClick={onClose} disabled={isDeleting} variant="outlined">
              Cancel
            </Button>
            <Button
              onClick={onConfirm}
              disabled={isDeleting}
              color="error"
              variant="contained"
              startIcon={isDeleting ? <CircularProgress size={16} /> : null}
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default DeleteTransformDialog;
