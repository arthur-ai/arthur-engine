import DeleteIcon from "@mui/icons-material/Delete";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { EvaluatorPipelinesPanel } from "./EvaluatorPipelinesPanel";

import { continuousEvalsQueryOptions } from "@/components/live-evals/hooks/useContinuousEvals";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useApi } from "@/hooks/useApi";
import type { ContinuousEvalResponse, LLMGetAllMetadataResponse } from "@/lib/api-client/api-client";
import { formatDateInTimezone } from "@/utils/formatters";

interface EvaluatorAccordionListProps {
  evals: LLMGetAllMetadataResponse[];
  taskId: string;
  onExpandToFullScreen: (evalName: string) => void;
  onDelete?: (evalName: string) => Promise<void>;
}

export const EvaluatorAccordionList = ({ evals, taskId, onExpandToFullScreen, onDelete }: EvaluatorAccordionListProps) => {
  const { timezone, use24Hour } = useDisplaySettings();
  const api = useApi()!;

  const [expanded, setExpanded] = useState<string | false>(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [evalToDelete, setEvalToDelete] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Fetch all CEs for this task once and group by evaluator name
  const { data: allCEsData } = useQuery(
    continuousEvalsQueryOptions({
      api,
      taskId,
      pagination: { page: 0, page_size: 500 },
      filters: [],
    })
  );

  const cesByEval = useMemo(() => {
    const map = new Map<string, ContinuousEvalResponse[]>();
    allCEsData?.evals.forEach((ce) => {
      const existing = map.get(ce.llm_eval_name) ?? [];
      map.set(ce.llm_eval_name, [...existing, ce]);
    });
    return map;
  }, [allCEsData]);

  const handleAccordionChange = (evalName: string) => (_: React.SyntheticEvent, isExpanded: boolean) => {
    setExpanded(isExpanded ? evalName : false);
  };

  const handleDeleteClick = (e: React.MouseEvent, evalName: string) => {
    e.stopPropagation();
    setEvalToDelete(evalName);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!evalToDelete || !onDelete) return;
    try {
      setIsDeleting(true);
      await onDelete(evalToDelete);
      setDeleteDialogOpen(false);
      setEvalToDelete(null);
    } catch {
      // error surfaced by the mutation hook
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setEvalToDelete(null);
  };

  return (
    <Box sx={{ px: 2, py: 1.5 }}>
      {evals.map((evalMeta) => {
        const pipelines = cesByEval.get(evalMeta.name) ?? [];
        const activePipelines = pipelines.filter((ce) => ce.enabled).length;
        const stalePipelines = pipelines.filter((ce) => ce.llm_eval_version < evalMeta.versions).length;

        return (
          <Accordion
            key={evalMeta.name}
            expanded={expanded === evalMeta.name}
            onChange={handleAccordionChange(evalMeta.name)}
            disableGutters
            elevation={0}
            sx={{
              border: "1px solid",
              borderColor: "divider",
              borderRadius: "8px !important",
              mb: 1,
              "&:before": { display: "none" },
              overflow: "hidden",
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              sx={{
                px: 2,
                py: 0,
                minHeight: 56,
                "& .MuiAccordionSummary-content": { my: 1.5, mr: 1 },
              }}
            >
              <Stack direction="row" alignItems="center" justifyContent="space-between" width="100%">
                {/* Left: name, version chip, continuous eval count */}
                <Stack direction="row" alignItems="center" gap={1.5} flexShrink={0} flexWrap="wrap">
                  <Typography variant="body1" fontWeight={500}>
                    {evalMeta.name}
                  </Typography>
                  <Chip
                    label={`v${evalMeta.versions}`}
                    size="small"
                    variant="outlined"
                    sx={{ height: 20, fontSize: "0.7rem", fontWeight: 600 }}
                  />
                  {pipelines.length > 0 && (
                    <Chip
                      label={`${activePipelines}/${pipelines.length} evals active`}
                      size="small"
                      color={activePipelines > 0 ? "success" : "default"}
                      sx={{ height: 20, fontSize: "0.7rem" }}
                    />
                  )}
                  {stalePipelines > 0 && (
                    <Tooltip title={`${stalePipelines} continuous eval${stalePipelines > 1 ? "s" : ""} using an older evaluator version`}>
                      <Chip label="Update available" size="small" color="warning" sx={{ height: 20, fontSize: "0.7rem", cursor: "help" }} />
                    </Tooltip>
                  )}
                </Stack>

                {/* Right: updated date + actions (stop accordion toggle from firing on button clicks) */}
                <Stack direction="row" alignItems="center" gap={0.5} onClick={(e) => e.stopPropagation()}>
                  <Typography variant="caption" color="text.secondary" sx={{ mr: 1, whiteSpace: "nowrap" }}>
                    Updated {formatDateInTimezone(evalMeta.latest_version_created_at, timezone, { hour12: !use24Hour })}
                  </Typography>
                  <Tooltip title="View full details">
                    <IconButton size="small" onClick={() => onExpandToFullScreen(evalMeta.name)} aria-label="View full details">
                      <OpenInFullIcon sx={{ fontSize: 16 }} />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete evaluator">
                    <IconButton
                      size="small"
                      onClick={(e) => handleDeleteClick(e, evalMeta.name)}
                      sx={{ color: "error.main" }}
                      aria-label="Delete evaluator"
                    >
                      <DeleteIcon sx={{ fontSize: 16 }} />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Stack>
            </AccordionSummary>

            <AccordionDetails sx={{ p: 0, borderTop: "1px solid", borderColor: "divider" }}>
              <EvaluatorPipelinesPanel taskId={taskId} evalName={evalMeta.name} latestVersion={evalMeta.versions} pipelines={pipelines} />
            </AccordionDetails>
          </Accordion>
        );
      })}

      <Dialog open={deleteDialogOpen} onClose={handleDeleteCancel} maxWidth="sm" fullWidth aria-labelledby="delete-eval-dialog-title">
        <DialogTitle id="delete-eval-dialog-title">Delete Evaluator?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete <strong>{evalToDelete}</strong>?
          </DialogContentText>
          <Box sx={{ mt: 2, p: 2, bgcolor: "warning.light", borderRadius: 1, opacity: 0.85 }}>
            <Typography variant="body2">
              <strong>Warning:</strong> This will permanently delete the evaluator and its entire version history. Any continuous evals using
              this evaluator will also be affected. This action cannot be undone.
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleDeleteCancel} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            color="error"
            variant="contained"
            disabled={isDeleting}
            startIcon={isDeleting ? <CircularProgress size={16} /> : <DeleteIcon />}
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
