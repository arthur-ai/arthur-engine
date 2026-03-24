import HistoryIcon from "@mui/icons-material/History";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Typography from "@mui/material/Typography";
import React from "react";

interface RestoreTransformVersionDialogProps {
  open: boolean;
  versionNumber: number | null;
  onClose: () => void;
  onConfirm: () => void;
  isRestoring: boolean;
}

const RestoreTransformVersionDialog: React.FC<RestoreTransformVersionDialogProps> = ({ open, versionNumber, onClose, onConfirm, isRestoring }) => {
  return (
    <Dialog open={open} onClose={isRestoring ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ textAlign: "center", pb: 1 }}>
        <Box sx={{ display: "flex", justifyContent: "center", mb: 2 }}>
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: "50%",
              bgcolor: "primary.50",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <HistoryIcon sx={{ color: "primary.main", fontSize: 24 }} />
          </Box>
        </Box>
        Restore to Version {versionNumber}
      </DialogTitle>

      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center" }}>
          This will create a new version with the configuration from Version {versionNumber}. The current configuration will be preserved in the
          version history.
        </Typography>
      </DialogContent>

      <DialogActions sx={{ p: 3 }}>
        <Button onClick={onClose} disabled={isRestoring} variant="outlined">
          Cancel
        </Button>
        <Button
          onClick={onConfirm}
          disabled={isRestoring}
          color="primary"
          variant="contained"
          startIcon={isRestoring ? <CircularProgress size={16} /> : null}
        >
          {isRestoring ? "Restoring..." : "Restore"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default RestoreTransformVersionDialog;
