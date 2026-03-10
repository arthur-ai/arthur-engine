import WarningIcon from "@mui/icons-material/Warning";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import React from "react";

import { useTransformDependents } from "./hooks/useTransformDependents";

interface DeleteTransformDialogProps {
  transformId: string | null;
  onClose: () => void;
  onConfirm: () => void;
  isDeleting: boolean;
}

const DeleteTransformDialog: React.FC<DeleteTransformDialogProps> = ({ transformId, onClose, onConfirm, isDeleting }) => {
  const { continuousEvals, isLoading } = useTransformDependents(transformId);
  const hasDependents = continuousEvals.length > 0;

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
        Delete Transform
      </DialogTitle>

      <DialogContent>
        {isLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
            <CircularProgress size={24} />
          </Box>
        ) : (
          <>
            {hasDependents && (
              <Alert severity="error" sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ fontWeight: 500, mb: 1 }}>
                  The following continuous evals will be permanently deleted:
                </Typography>
                <List dense disablePadding>
                  {continuousEvals.map((eval_) => (
                    <ListItem key={eval_.id} disableGutters sx={{ py: 0 }}>
                      <ListItemText
                        primary={eval_.name}
                        primaryTypographyProps={{ variant: "body2" }}
                        secondary={`${eval_.llm_eval_name} v${eval_.llm_eval_version}`}
                        secondaryTypographyProps={{ variant: "caption" }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Alert>
            )}

            <Alert severity="warning" sx={{ mb: 2 }}>
              <Typography variant="body2">Agent experiments and notebooks referencing this transform may stop working correctly.</Typography>
            </Alert>

            <Typography variant="body2" color="text.secondary">
              This action cannot be undone.
            </Typography>
          </>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 3 }}>
        <Button onClick={onClose} disabled={isDeleting} variant="outlined">
          Cancel
        </Button>
        <Button
          onClick={onConfirm}
          disabled={isLoading || isDeleting}
          color="error"
          variant="contained"
          startIcon={isDeleting ? <CircularProgress size={16} /> : null}
        >
          {isDeleting ? "Deleting..." : "Delete"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DeleteTransformDialog;
