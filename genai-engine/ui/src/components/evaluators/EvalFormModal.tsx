import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import FormLabel from "@mui/material/FormLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import React, { useState } from "react";

import { EvalFormModalProps } from "./types";

import type { CreateEvalRequest, ModelProvider } from "@/lib/api-client/api-client";

const MODEL_PROVIDERS: ModelProvider[] = ["openai", "anthropic", "gemini"];

const EvalFormModal = ({ open, onClose, onSubmit, isLoading = false }: EvalFormModalProps) => {
  const [evalName, setEvalName] = useState("");
  const [instructions, setInstructions] = useState("");
  const [modelProvider, setModelProvider] = useState<ModelProvider>("openai");
  const [modelName, setModelName] = useState("");
  const [minScore, setMinScore] = useState<number>(0);
  const [maxScore, setMaxScore] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!evalName.trim()) {
      setError("Eval name is required");
      return;
    }

    if (!instructions.trim()) {
      setError("Instructions are required");
      return;
    }

    if (!modelName.trim()) {
      setError("Model name is required");
      return;
    }

    try {
      const data: CreateEvalRequest = {
        instructions: instructions.trim(),
        model_provider: modelProvider,
        model_name: modelName.trim(),
        min_score: minScore,
        max_score: maxScore,
      };

      await onSubmit(evalName.trim(), data);

      // Reset form on success
      setEvalName("");
      setInstructions("");
      setModelProvider("openai");
      setModelName("");
      setMinScore(0);
      setMaxScore(1);
      setError(null);
    } catch (err) {
      console.error("Failed to create eval:", err);
      setError(err instanceof Error ? err.message : "Failed to create eval. Please try again.");
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setEvalName("");
      setInstructions("");
      setModelProvider("openai");
      setModelName("");
      setMinScore(0);
      setMaxScore(1);
      setError(null);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Create New Eval</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3, pt: 1 }}>
            <FormControl fullWidth>
              <FormLabel>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  Eval Name
                </Typography>
              </FormLabel>
              <TextField
                value={evalName}
                onChange={(e) => setEvalName(e.target.value)}
                placeholder="Enter eval name..."
                disabled={isLoading}
                autoFocus
                required
                size="small"
              />
            </FormControl>

            <FormControl fullWidth>
              <FormLabel>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  Instructions
                </Typography>
              </FormLabel>
              <TextField
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Enter eval instructions..."
                disabled={isLoading}
                required
                multiline
                minRows={4}
                maxRows={10}
                size="small"
              />
            </FormControl>

            <Box sx={{ display: "flex", gap: 2 }}>
              <FormControl fullWidth>
                <InputLabel id="model-provider-label" size="small">
                  Model Provider
                </InputLabel>
                <Select
                  labelId="model-provider-label"
                  value={modelProvider}
                  onChange={(e) => setModelProvider(e.target.value as ModelProvider)}
                  disabled={isLoading}
                  required
                  label="Model Provider"
                  size="small"
                >
                  {MODEL_PROVIDERS.map((provider) => (
                    <MenuItem key={provider} value={provider}>
                      {provider}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <FormLabel>
                  <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                    Model Name
                  </Typography>
                </FormLabel>
                <TextField
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  placeholder="e.g., gpt-4o, claude-3-sonnet"
                  disabled={isLoading}
                  required
                  size="small"
                />
              </FormControl>
            </Box>

            <Box sx={{ display: "flex", gap: 2 }}>
              <FormControl fullWidth>
                <FormLabel>
                  <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                    Min Score
                  </Typography>
                </FormLabel>
                <TextField
                  type="number"
                  value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  disabled={isLoading}
                  size="small"
                  slotProps={{ htmlInput: { min: 0, step: 1 } }}
                />
              </FormControl>

              <FormControl fullWidth>
                <FormLabel>
                  <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                    Max Score
                  </Typography>
                </FormLabel>
                <TextField
                  type="number"
                  value={maxScore}
                  onChange={(e) => setMaxScore(Number(e.target.value))}
                  disabled={isLoading}
                  size="small"
                  slotProps={{ htmlInput: { min: 0, step: 1 } }}
                />
              </FormControl>
            </Box>

            {error && (
              <Alert severity="error" onClose={() => setError(null)}>
                {error}
              </Alert>
            )}
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={isLoading || !evalName.trim() || !instructions.trim() || !modelName.trim()}
            sx={{ minWidth: 120 }}
          >
            {isLoading ? "Creating..." : "Create Eval"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default EvalFormModal;
