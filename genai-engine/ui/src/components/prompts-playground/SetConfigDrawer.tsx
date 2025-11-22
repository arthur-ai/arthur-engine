import CloseIcon from "@mui/icons-material/Close";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useState, useCallback } from "react";

import { usePromptExperiments } from "@/hooks/usePromptExperiments";
import { useApi } from "@/hooks/useApi";
import type { PromptExperimentSummary } from "@/lib/api-client/api-client";

interface SetConfigDrawerProps {
  open: boolean;
  onClose: () => void;
  taskId: string | undefined;
  onLoadConfig: (config: any, overwritePrompts: boolean) => void;
  onCreateNewConfig: () => void;
  hasExistingPrompts: boolean;
}

const SetConfigDrawer = ({
  open,
  onClose,
  taskId,
  onLoadConfig,
  onCreateNewConfig,
  hasExistingPrompts,
}: SetConfigDrawerProps) => {
  const [selectedExperimentId, setSelectedExperimentId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [showOverwriteDialog, setShowOverwriteDialog] = useState(false);
  const [pendingConfig, setPendingConfig] = useState<any>(null);

  const apiClient = useApi();
  const { experiments, isLoading: experimentsLoading } = usePromptExperiments(taskId, 0, 100);

  const handleLoadConfig = useCallback(async () => {
    if (!selectedExperimentId || !apiClient) return;

    setIsLoading(true);
    try {
      // Fetch the full experiment details
      const response = await apiClient.api.getPromptExperimentApiV1PromptExperimentsExperimentIdGet(
        selectedExperimentId
      );

      const experimentDetail = response.data;

      // Transform to config format expected by notebook state
      const config = {
        experimentId: selectedExperimentId, // Pass experiment ID for prompt loading
        name: experimentDetail.name,
        description: experimentDetail.description || "",
        dataset_ref: experimentDetail.dataset_ref,
        eval_list: experimentDetail.eval_list || [],
        prompt_variable_mapping: experimentDetail.prompt_variable_mapping || [],
        dataset_row_filter: experimentDetail.dataset_row_filter || [],
        prompt_configs: experimentDetail.prompt_configs || [], // Include prompt configs
      };

      // If there are existing prompts, show confirmation dialog
      if (hasExistingPrompts) {
        setPendingConfig(config);
        setShowOverwriteDialog(true);
      } else {
        // No prompts, load with overwrite
        onLoadConfig(config, true);
        onClose();
      }
    } catch (error) {
      console.error("Failed to load experiment config:", error);
    } finally {
      setIsLoading(false);
    }
  }, [selectedExperimentId, apiClient, hasExistingPrompts, onLoadConfig, onClose]);

  const handleOverwriteConfirm = useCallback((overwrite: boolean) => {
    if (pendingConfig) {
      onLoadConfig(pendingConfig, overwrite);
      setPendingConfig(null);
      setShowOverwriteDialog(false);
      onClose();
    }
  }, [pendingConfig, onLoadConfig, onClose]);

  const handleOverwriteCancel = useCallback(() => {
    setPendingConfig(null);
    setShowOverwriteDialog(false);
  }, []);

  const handleCreateNew = useCallback(() => {
    onCreateNewConfig();
    onClose();
  }, [onCreateNewConfig, onClose]);

  return (
    <>
      <Drawer
        anchor="right"
        open={open}
        onClose={onClose}
        sx={{
          "& .MuiDrawer-paper": {
            width: 400,
            p: 3,
          },
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Set Configuration
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {/* Load Configuration */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
              Load Configuration
            </Typography>
            <TextField
              select
              fullWidth
              size="small"
              label="Select experiment"
              value={selectedExperimentId}
              onChange={(e) => setSelectedExperimentId(e.target.value)}
              disabled={experimentsLoading || experiments.length === 0}
              helperText={
                experiments.length === 0 && !experimentsLoading
                  ? "No experiments available"
                  : undefined
              }
            >
              {experiments.map((exp: PromptExperimentSummary) => {
                // Build display string with only available data
                const parts = [exp.name];
                if (exp.dataset_name) {
                  parts.push(exp.dataset_name);
                }
                if (exp.dataset_version) {
                  parts.push(`v${exp.dataset_version}`);
                }
                return (
                  <MenuItem key={exp.id} value={exp.id}>
                    {parts.join(" - ")}
                  </MenuItem>
                );
              })}
            </TextField>
            <Button
              variant="outlined"
              fullWidth
              onClick={handleLoadConfig}
              disabled={!selectedExperimentId || isLoading}
              sx={{ mt: 1.5 }}
            >
              {isLoading ? "Loading..." : "Load"}
            </Button>
          </Box>

          <Divider>
            <Typography variant="caption" color="text.secondary">
              OR
            </Typography>
          </Divider>

          {/* Create New Configuration */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
              Create New Configuration
            </Typography>
            <Button variant="contained" fullWidth onClick={handleCreateNew}>
              Create New
            </Button>
          </Box>
        </Box>
      </Drawer>

      {/* Overwrite Confirmation Dialog */}
      <Dialog
        open={showOverwriteDialog}
        onClose={handleOverwriteCancel}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Overwrite Existing Prompts?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This notebook already contains prompts. Would you like to overwrite them with the prompts from the selected experiment, or keep your existing prompts and only load the configuration?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleOverwriteCancel} color="inherit">
            Cancel
          </Button>
          <Button onClick={() => handleOverwriteConfirm(false)} variant="outlined">
            Keep Existing Prompts
          </Button>
          <Button onClick={() => handleOverwriteConfirm(true)} variant="contained" color="primary">
            Overwrite Prompts
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default SetConfigDrawer;
