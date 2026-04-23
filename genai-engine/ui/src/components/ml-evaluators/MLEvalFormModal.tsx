import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";
import FormLabel from "@mui/material/FormLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Slider from "@mui/material/Slider";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { isAxiosError } from "axios";
import React, { useEffect, useState } from "react";

import type { CreateMLEvalRequest, CreateMlEvalRequestEvalTypeEnum } from "@/lib/api-client/api-client";

const ML_EVAL_TYPES = [
  { value: "pii", label: "PII Detection (Strict)" },
  { value: "pii_v1", label: "PII Detection (Standard)" },
  { value: "toxicity", label: "Toxicity" },
  { value: "prompt_injection", label: "Prompt Injection" },
];

const ALL_PII_ENTITIES = [
  "CREDIT_CARD",
  "CRYPTO",
  "DATE_TIME",
  "EMAIL_ADDRESS",
  "IBAN_CODE",
  "IP_ADDRESS",
  "NRP",
  "LOCATION",
  "PERSON",
  "PHONE_NUMBER",
  "MEDICAL_LICENSE",
  "URL",
  "US_BANK_NUMBER",
  "US_DRIVER_LICENSE",
  "US_ITIN",
  "US_PASSPORT",
  "US_SSN",
] as const;

interface MLEvalFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (evalName: string, data: CreateMLEvalRequest) => Promise<void>;
  isLoading?: boolean;
  /** Pre-fill and lock the eval name (for adding a new version to an existing eval) */
  initialName?: string;
  /** Pre-select the eval type (for adding a new version to an existing eval) */
  initialType?: string;
  /** Pre-populate config fields from an existing eval version */
  initialConfig?: Record<string, unknown> | null;
}

const MLEvalFormModal = ({ open, onClose, onSubmit, isLoading = false, initialName, initialType, initialConfig }: MLEvalFormModalProps) => {
  const [evalName, setEvalName] = useState(initialName ?? "");
  const [mlEvalType, setMlEvalType] = useState<CreateMlEvalRequestEvalTypeEnum>((initialType ?? "pii") as CreateMlEvalRequestEvalTypeEnum);
  const [toxicityThreshold, setToxicityThreshold] = useState(0.5);
  // All entities enabled by default (none disabled)
  const [disabledEntities, setDisabledEntities] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setEvalName(initialName ?? "");
      setMlEvalType((initialType ?? "pii") as CreateMlEvalRequestEvalTypeEnum);
      setToxicityThreshold(typeof initialConfig?.toxicity_threshold === "number" ? initialConfig.toxicity_threshold : 0.5);
      setDisabledEntities(Array.isArray(initialConfig?.disabled_pii_entities) ? new Set(initialConfig.disabled_pii_entities as string[]) : new Set());
      setError(null);
    }
  }, [open, initialName, initialType, initialConfig]);

  const isPiiType = mlEvalType === "pii" || mlEvalType === "pii_v1";

  const toggleEntity = (entity: string) => {
    setDisabledEntities((prev) => {
      const next = new Set(prev);
      if (next.has(entity)) {
        next.delete(entity);
      } else {
        next.add(entity);
      }
      return next;
    });
  };

  const buildConfig = (): Record<string, unknown> | null => {
    if (mlEvalType === "toxicity") {
      return { toxicity_threshold: toxicityThreshold };
    }
    if (isPiiType && disabledEntities.size > 0) {
      return { disabled_pii_entities: Array.from(disabledEntities) };
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!evalName.trim()) {
      setError("Eval name is required");
      return;
    }

    try {
      const data: CreateMLEvalRequest = {
        eval_type: mlEvalType,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        config: buildConfig() as any,
      };
      await onSubmit(evalName.trim(), data);
      handleClose();
    } catch (err: unknown) {
      let errorMessage = "Failed to create ML eval. Please try again.";
      if (isAxiosError(err) && err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      setError(errorMessage);
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setEvalName("");
      setMlEvalType("pii");
      setToxicityThreshold(0.5);
      setDisabledEntities(new Set());
      setError(null);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>{initialName ? "Edit ML Eval" : "Create New ML Eval"}</DialogTitle>
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
                variant="filled"
                value={evalName}
                onChange={(e) => setEvalName(e.target.value)}
                placeholder="Enter eval name..."
                required
                size="small"
                autoFocus={!initialName}
                disabled={isLoading || !!initialName}
                helperText={initialName ? "A new version will be created for this evaluator" : undefined}
              />
            </FormControl>

            <FormControl fullWidth>
              <FormLabel>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  Evaluator Type
                </Typography>
              </FormLabel>
              <Select
                value={mlEvalType}
                onChange={(e) => setMlEvalType(e.target.value as CreateMlEvalRequestEvalTypeEnum)}
                size="small"
                disabled={isLoading}
              >
                {ML_EVAL_TYPES.map((t) => (
                  <MenuItem key={t.value} value={t.value}>
                    {t.label}
                  </MenuItem>
                ))}
              </Select>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                {mlEvalType === "pii" &&
                  "Strict PII detection using an ML model (GLiNER) combined with rule-based analysis. Catches more entities but may have more false positives."}
                {mlEvalType === "pii_v1" && "Standard PII detection using rule-based analysis (Presidio). More precise with fewer false positives."}
                {mlEvalType === "toxicity" && "Classifies text toxicity using a built-in ML model."}
                {mlEvalType === "prompt_injection" && "Detects prompt injection attacks using a built-in ML model."}
              </Typography>
            </FormControl>

            {isPiiType && (
              <FormControl fullWidth>
                <FormLabel>
                  <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                    PII Entity Types
                  </Typography>
                </FormLabel>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1 }}>
                  All entities are detected by default. Uncheck to disable specific types.
                </Typography>
                <FormGroup sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
                  {ALL_PII_ENTITIES.map((entity) => (
                    <FormControlLabel
                      key={entity}
                      control={
                        <Checkbox checked={!disabledEntities.has(entity)} onChange={() => toggleEntity(entity)} size="small" disabled={isLoading} />
                      }
                      label={<Typography variant="caption">{entity.replace(/_/g, " ")}</Typography>}
                    />
                  ))}
                </FormGroup>
              </FormControl>
            )}

            {mlEvalType === "toxicity" && (
              <FormControl fullWidth>
                <FormLabel>
                  <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                    Toxicity Threshold: {toxicityThreshold.toFixed(2)}
                  </Typography>
                </FormLabel>
                <Slider
                  value={toxicityThreshold}
                  onChange={(_, v) => setToxicityThreshold(v as number)}
                  min={0}
                  max={1}
                  step={0.01}
                  marks={[
                    { value: 0, label: "0" },
                    { value: 0.5, label: "0.5" },
                    { value: 1, label: "1" },
                  ]}
                  disabled={isLoading}
                />
                <Typography variant="caption" color="text.secondary">
                  Text with toxicity score above this threshold will fail. Lower = stricter.
                </Typography>
              </FormControl>
            )}

            {error && (
              <Alert severity="error" onClose={() => setError(null)}>
                {error}
              </Alert>
            )}
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button variant="text" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="contained" disabled={isLoading || !evalName.trim()} sx={{ minWidth: 120 }}>
            {isLoading ? "Saving..." : initialName ? "Save New Version" : "Save ML Eval"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default MLEvalFormModal;
