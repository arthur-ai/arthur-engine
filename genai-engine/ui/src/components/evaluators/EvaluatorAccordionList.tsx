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
  Table,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { EvaluatorPipelinesPanel } from "./EvaluatorPipelinesPanel";
import { MLEvaluatorPipelinesPanel } from "./MLEvaluatorPipelinesPanel";

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
      // Key by the relevant eval name based on eval_type
      const key = ce.llm_eval_name ?? "";
      if (!key) return;
      const existing = map.get(key) ?? [];
      map.set(key, [...existing, ce]);
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
      {/* Column headers — matches MUI Table header style used across the app */}
      <Table sx={{ mb: 1, tableLayout: "fixed" }}>
        <TableHead>
          <TableRow>
            <TableCell>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Name
              </Typography>
            </TableCell>
            <TableCell sx={{ width: 220 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Last Updated
              </Typography>
            </TableCell>
            <TableCell sx={{ width: 96 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                Actions
              </Typography>
            </TableCell>
          </TableRow>
        </TableHead>
      </Table>

      {evals.map((evalMeta) => {
        const pipelines = cesByEval.get(evalMeta.name) ?? [];
        const activePipelines = pipelines.filter((ce) => ce.enabled).length;
        const isLLM = evalMeta.eval_type === "llm_as_a_judge";
        // Stale check only applies to LLM evals (version-controlled)
        const stalePipelines = isLLM ? pipelines.filter((ce) => (ce.llm_eval_version ?? 0) < evalMeta.versions).length : 0;

        return (
          <Box key={evalMeta.name} sx={{ position: "relative", mb: 1 }}>
            <Accordion
              expanded={expanded === evalMeta.name}
              onChange={handleAccordionChange(evalMeta.name)}
              disableGutters
              elevation={0}
              sx={{
                border: "1px solid",
                borderColor: "divider",
                borderRadius: "8px !important",
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
                  // Reserve space on the right so summary text doesn't overlap the action buttons
                  pr: 14,
                  "& .MuiAccordionSummary-content": { my: 1.5, mr: 1 },
                }}
              >
                {/* Left: name, type chip, version chip, continuous eval count */}
                <Stack direction="row" alignItems="center" gap={1.5} flexShrink={0} flexWrap="wrap">
                  <Typography variant="body1" fontWeight={500}>
                    {evalMeta.name}
                  </Typography>
                  {/* Eval type chip */}
                  {isLLM ? (
                    <Chip label="LLM" size="small" color="primary" variant="outlined" sx={{ height: 20, fontSize: "0.7rem", fontWeight: 600 }} />
                  ) : (
                    <Chip label="ML" size="small" color="secondary" variant="outlined" sx={{ height: 20, fontSize: "0.7rem", fontWeight: 600 }} />
                  )}
                  {!isLLM && <Chip label={evalMeta.eval_type} size="small" variant="outlined" sx={{ height: 20, fontSize: "0.7rem" }} />}
                  <Chip label={`v${evalMeta.versions}`} size="small" variant="outlined" sx={{ height: 20, fontSize: "0.7rem", fontWeight: 600 }} />
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
              </AccordionSummary>

              <AccordionDetails sx={{ p: 0, borderTop: "1px solid", borderColor: "divider" }}>
                {isLLM ? (
                  <EvaluatorPipelinesPanel taskId={taskId} evalName={evalMeta.name} latestVersion={evalMeta.versions} pipelines={pipelines} />
                ) : (
                  <MLEvaluatorPipelinesPanel taskId={taskId} evalName={evalMeta.name} pipelines={pipelines} />
                )}
              </AccordionDetails>
            </Accordion>

            {/* Date text — aligned with "Last Updated" column header */}
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                position: "absolute",
                top: 0,
                right: 100,
                height: 56,
                display: "flex",
                alignItems: "center",
                whiteSpace: "nowrap",
                pointerEvents: "none",
              }}
            >
              Updated {formatDateInTimezone(evalMeta.latest_version_created_at ?? null, timezone, { hour12: !use24Hour })}
            </Typography>
            {/* Action icons — positioned outside AccordionSummary to avoid nested <button> elements */}
            <Stack direction="row" alignItems="center" gap={0.5} sx={{ position: "absolute", top: 0, right: 48, height: 56, zIndex: 2 }}>
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
          </Box>
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
              <strong>Warning:</strong> This will permanently delete the evaluator and its entire version history. Any continuous evals using this
              evaluator will also be affected. This action cannot be undone.
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleDeleteCancel} disabled={isDeleting} variant="outlined">
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
