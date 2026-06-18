import { StatusBadge } from "@arthur/shared-components";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useMemo, useState } from "react";

import type { GuardrailInvocation, GuardrailStatus } from "../../utils/guardrails";
import { summarizeGuardrails } from "../../utils/guardrails";

import { GuardrailInvocationRow } from "./GuardrailInvocationRow";

type Filter = GuardrailStatus | "all";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "failed", label: "Failed" },
  { key: "degraded", label: "Degraded" },
  { key: "passed", label: "Passed" },
];

type Props = {
  invocations: GuardrailInvocation[];
  selectedSpanId: string | null;
  onJumpToSpan: (spanId: string) => void;
};

export function GuardrailSummaryBar({ invocations, selectedSpanId, onJumpToSpan }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");

  const summary = useMemo(() => summarizeGuardrails(invocations), [invocations]);

  const filtered = useMemo(() => (filter === "all" ? invocations : invocations.filter((inv) => inv.status === filter)), [invocations, filter]);

  // No guardrail invocations in this trace — render nothing so the annotation
  // row layout is unchanged.
  if (invocations.length === 0) return null;

  return (
    <Paper variant="outlined" sx={{ borderRadius: 1, overflow: "hidden" }}>
      <Stack direction="row" alignItems="center" spacing={1.5} sx={{ px: 2, py: 1.25 }}>
        <ShieldOutlinedIcon sx={{ fontSize: 20, color: "text.secondary" }} />
        <Typography variant="subtitle2" sx={{ whiteSpace: "nowrap" }}>
          {summary.total} {summary.total === 1 ? "guardrail" : "guardrails"}
        </Typography>

        <Stack direction="row" alignItems="center" spacing={1}>
          {summary.failed > 0 && <StatusBadge paletteKey="error" label={`${summary.failed} failed`} size="small" />}
          {summary.degraded > 0 && <StatusBadge paletteKey="warning" label={`${summary.degraded} degraded`} size="small" />}
          {summary.passed > 0 && <StatusBadge paletteKey="success" label={`${summary.passed} passed`} size="small" />}
        </Stack>

        <Button
          variant="text"
          size="small"
          onClick={() => setExpanded((prev) => !prev)}
          endIcon={<KeyboardArrowDownIcon sx={{ transform: expanded ? "rotate(180deg)" : "none", transition: "transform 150ms" }} />}
          sx={{ ml: "auto", flexShrink: 0 }}
        >
          {expanded ? "Hide" : "Show"}
        </Button>
      </Stack>

      <Collapse in={expanded}>
        <Box sx={{ px: 2, pb: 1.5 }}>
          <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: "wrap", rowGap: 1 }}>
            {FILTERS.map((f) => (
              <Chip
                key={f.key}
                label={f.label}
                size="small"
                onClick={() => setFilter(f.key)}
                color={filter === f.key ? "primary" : "default"}
                variant={filter === f.key ? "filled" : "outlined"}
              />
            ))}
          </Stack>

          {filtered.length === 0 ? (
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", px: 1.5, py: 1 }}>
              No {filter} guardrails in this trace.
            </Typography>
          ) : (
            <Stack divider={<Box sx={{ borderBottom: "1px solid", borderColor: "divider" }} />}>
              {filtered.map((inv) => (
                <GuardrailInvocationRow
                  key={inv.spanId}
                  invocation={inv}
                  selected={inv.spanId === selectedSpanId}
                  onJump={() => onJumpToSpan(inv.spanId)}
                />
              ))}
            </Stack>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
}
