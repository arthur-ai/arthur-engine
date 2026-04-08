import AddIcon from "@mui/icons-material/Add";
import LiveTvOutlinedIcon from "@mui/icons-material/LiveTvOutlined";
import { Box, Button, Chip, Link as MuiLink, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { LiveEvalActions } from "@/components/live-evals/components/actions";
import { EditFormDialog } from "@/components/live-evals/components/edit-form";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import type { ContinuousEvalResponse } from "@/lib/api-client/api-client";
import { formatDateInTimezone } from "@/utils/formatters";

interface MLEvaluatorPipelinesPanelProps {
  taskId: string;
  evalName: string;
  pipelines: ContinuousEvalResponse[];
}

export const MLEvaluatorPipelinesPanel = ({ taskId, evalName, pipelines }: MLEvaluatorPipelinesPanelProps) => {
  const { timezone, use24Hour } = useDisplaySettings();
  const navigate = useNavigate();
  const [editCEId, setEditCEId] = useState<string | undefined>();

  const handleAddContinuousEval = () => {
    navigate(`/tasks/${taskId}/continuous-evals/new?mlEvalName=${encodeURIComponent(evalName)}`);
  };

  if (pipelines.length === 0) {
    return (
      <Stack alignItems="center" justifyContent="center" sx={{ py: 4, px: 3 }} gap={1.5}>
        <LiveTvOutlinedIcon sx={{ fontSize: 40, color: "text.secondary" }} />
        <Typography variant="body2" color="text.secondary" textAlign="center">
          No continuous evals yet. Add one to start running this evaluator automatically on incoming traces.
        </Typography>
        <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={handleAddContinuousEval}>
          Continuous Eval
        </Button>
      </Stack>
    );
  }

  return (
    <Box>
      <Table size="small">
        <TableHead>
          <TableRow sx={{ bgcolor: "action.hover" }}>
            <TableCell sx={{ fontWeight: 600, py: 1 }}>Continuous Eval</TableCell>
            <TableCell sx={{ fontWeight: 600, py: 1 }}>Status</TableCell>
            <TableCell sx={{ fontWeight: 600, py: 1 }}>Description</TableCell>
            <TableCell sx={{ fontWeight: 600, py: 1 }}>Version</TableCell>
            <TableCell sx={{ fontWeight: 600, py: 1 }}>Created</TableCell>
            <TableCell sx={{ fontWeight: 600, py: 1 }} />
          </TableRow>
        </TableHead>
        <TableBody>
          {pipelines.map((ce) => (
            <TableRow key={ce.id} hover>
              <TableCell>
                <MuiLink component={Link} to={`/tasks/${taskId}/continuous-evals/${ce.id}`} underline="hover">
                  <Typography variant="body2" fontWeight={500}>
                    {ce.name}
                  </Typography>
                </MuiLink>
              </TableCell>

              <TableCell>
                <Chip label={ce.enabled ? "Enabled" : "Disabled"} color={ce.enabled ? "success" : "default"} size="small" />
              </TableCell>

              <TableCell sx={{ maxWidth: 200 }}>
                {ce.description ? (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 180 }}
                    title={ce.description}
                  >
                    {ce.description}
                  </Typography>
                ) : (
                  <Typography variant="body2" color="text.disabled">
                    —
                  </Typography>
                )}
              </TableCell>

              <TableCell>
                <Chip
                  label={ce.ml_eval_version != null ? `v${ce.ml_eval_version}` : "latest"}
                  size="small"
                  variant="outlined"
                  sx={{ height: 20, fontSize: "0.7rem" }}
                />
              </TableCell>

              <TableCell>
                <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: "nowrap" }}>
                  {formatDateInTimezone(ce.created_at, timezone, { hour12: !use24Hour })}
                </Typography>
              </TableCell>

              <TableCell align="right">
                <LiveEvalActions config={ce} onEdit={setEditCEId} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Box sx={{ p: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
        <Button variant="outlined" size="small" startIcon={<AddIcon />} onClick={handleAddContinuousEval}>
          Continuous Eval
        </Button>
      </Box>

      <EditFormDialog continuousEvalId={editCEId} onClose={() => setEditCEId(undefined)} />
    </Box>
  );
};
