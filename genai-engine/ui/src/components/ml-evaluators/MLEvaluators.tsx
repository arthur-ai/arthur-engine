import AddIcon from "@mui/icons-material/Add";
import PrecisionManufacturingOutlinedIcon from "@mui/icons-material/PrecisionManufacturingOutlined";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import React, { useCallback, useState } from "react";

import { useCreateMlEvalMutation } from "./hooks/useCreateMlEvalMutation";
import { useMlEvals } from "./hooks/useMlEvals";
import { MLEvalActions } from "./MLEvalActions";
import MLEvalFormModal from "./MLEvalFormModal";

import { getContentHeight } from "@/constants/layout";
import { useTask } from "@/hooks/useTask";
import type { CreateMLEvalRequest, LLMGetAllMetadataResponse } from "@/lib/api-client/api-client";

const ML_EVAL_TYPE_LABELS: Record<string, string> = {
  pii: "PII Detection (Strict)",
  pii_v1: "PII Detection (Standard)",
  toxicity: "Toxicity",
  prompt_injection: "Prompt Injection",
};

interface MLEvaluatorsProps {
  isCreateModalOpen?: boolean;
  onCreateModalClose?: () => void;
}

const MLEvaluators: React.FC<MLEvaluatorsProps> = ({ isCreateModalOpen: externalOpen, onCreateModalClose }) => {
  const { task } = useTask();
  const [internalOpen, setInternalOpen] = useState(false);
  const [editingEval, setEditingEval] = useState<{ name: string; type: string; config: Record<string, unknown> | null } | null>(null);

  const isCreateModalOpen = externalOpen === true || internalOpen || editingEval !== null;
  const handleClose = () => {
    setInternalOpen(false);
    setEditingEval(null);
    onCreateModalClose?.();
  };

  const { evals, error, isLoading, refetch } = useMlEvals(task?.id);

  const createMutation = useCreateMlEvalMutation(task?.id, () => {
    handleClose();
    refetch();
  });

  const handleCreateMlEval = useCallback(
    async (evalName: string, data: CreateMLEvalRequest) => {
      await createMutation.mutateAsync({ evalName, data });
    },
    [createMutation]
  );

  const handleEdit = useCallback(
    (evalName: string) => {
      const eval_ = evals.find((e) => e.name === evalName);
      setEditingEval({ name: evalName, type: eval_?.eval_type ?? "pii", config: null });
    },
    [evals]
  );

  if (isLoading && evals.length === 0) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: getContentHeight() }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error && evals.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error.message || "Failed to load ML evals"}</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ width: "100%", height: getContentHeight(), display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
        {evals.length === 0 ? (
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", py: 8 }}>
            <PrecisionManufacturingOutlinedIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
            <Typography variant="h5" gutterBottom sx={{ fontWeight: 500 }}>
              No ML evals yet
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Get started by creating your first ML eval
            </Typography>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setInternalOpen(true)} size="large">
              ML Evaluator
            </Button>
          </Box>
        ) : (
          <Stack spacing={1.5}>
            {evals.map((eval_: LLMGetAllMetadataResponse) => (
              <MLEvalCard key={eval_.name} eval_={eval_} onEdit={handleEdit} />
            ))}
          </Stack>
        )}
      </Box>

      <MLEvalFormModal
        open={isCreateModalOpen}
        onClose={handleClose}
        onSubmit={handleCreateMlEval}
        isLoading={createMutation.isPending}
        initialName={editingEval?.name}
        initialType={editingEval?.type}
        initialConfig={editingEval?.config}
      />
    </Box>
  );
};

const MLEvalCard = ({ eval_, onEdit }: { eval_: LLMGetAllMetadataResponse; onEdit: (evalName: string) => void }) => {
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between">
        <Box>
          <Typography variant="subtitle1" fontWeight={600}>
            {eval_.name}
          </Typography>
          <Stack direction="row" gap={1} mt={0.5}>
            <Chip label={ML_EVAL_TYPE_LABELS[eval_.eval_type ?? ""] ?? eval_.eval_type} size="small" variant="outlined" color="secondary" />
            <Chip
              label={`${eval_.versions} version${eval_.versions !== 1 ? "s" : ""}`}
              size="small"
              sx={{ height: 20, fontSize: "0.75rem", fontWeight: 500 }}
            />
          </Stack>
        </Box>
        <MLEvalActions evalName={eval_.name} evalType={eval_.eval_type ?? ""} onEdit={onEdit} />
      </Stack>
    </Paper>
  );
};

export default MLEvaluators;
