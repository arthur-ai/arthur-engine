import { Chip, Stack, Tooltip, Typography } from "@mui/material";
import { createMRTColumnHelper } from "material-react-table";

import { StatusBadge } from "@/components/agent-experiments/components/status-badge";
import { CopyableChip } from "@/components/common";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import type { AgenticTestCase, EvalExecution, TestCaseStatus } from "@/lib/api-client/api-client";
import { isEvalPass } from "@/utils/evals";
import { formatCurrency } from "@/utils/formatters";

const columnHelper = createMRTColumnHelper<AgenticTestCase>();

function CostCell({ value }: { value: string | null | undefined }) {
  const { defaultCurrency } = useDisplaySettings();
  return value ? formatCurrency(parseFloat(value), defaultCurrency) : "N/A";
}

const isTerminalStatus = (status: TestCaseStatus): boolean => status === "completed" || status === "failed";

function EvalChip({ evalItem, status }: { evalItem: EvalExecution; status: TestCaseStatus }) {
  const label = `${evalItem.eval_name} (v${evalItem.eval_version})`;

  if (!evalItem.eval_results) {
    const pending = !isTerminalStatus(status);
    return (
      <Tooltip title={`${label}: ${pending ? "evaluation pending" : "not run"}`} arrow>
        <Chip label={evalItem.eval_name} size="small" variant="outlined" />
      </Tooltip>
    );
  }

  const pass = isEvalPass(evalItem.eval_results.score);
  return (
    <Tooltip
      title={
        <Stack gap={0.5}>
          <Typography variant="caption" fontWeight={600}>
            {label}: {pass ? "Pass" : "Fail"} (score {evalItem.eval_results.score})
          </Typography>
          {evalItem.eval_results.explanation && <Typography variant="caption">{evalItem.eval_results.explanation}</Typography>}
        </Stack>
      }
      arrow
    >
      <Chip label={evalItem.eval_name} size="small" variant="outlined" color={pass ? "success" : "error"} />
    </Tooltip>
  );
}

function EvalsCell({ evals, status }: { evals: EvalExecution[]; status: TestCaseStatus }) {
  if (evals.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        N/A
      </Typography>
    );
  }

  return (
    <Stack direction="row" gap={0.5} flexWrap="wrap">
      {evals.map((evalItem) => (
        <EvalChip key={`${evalItem.eval_name}-${evalItem.eval_version}`} evalItem={evalItem} status={status} />
      ))}
    </Stack>
  );
}

export const columns = [
  columnHelper.accessor("status", {
    header: "Status",
    Cell: ({ cell }) => <StatusBadge status={cell.getValue()} />,
  }),
  columnHelper.accessor("agentic_result.request_url", {
    header: "Request URL",
    Cell: ({ cell }) => {
      const url = cell.getValue();
      return <CopyableChip label={url} />;
    },
  }),
  columnHelper.accessor("agentic_result.output.status_code", {
    header: "Status Code",
  }),
  columnHelper.accessor("agentic_result.evals", {
    header: "Evals",
    enableSorting: false,
    Cell: ({ cell, row }) => <EvalsCell evals={cell.getValue()} status={row.original.status} />,
  }),
  columnHelper.accessor("total_cost", {
    header: "Total Cost",
    Cell: ({ cell }) => <CostCell value={cell.getValue()} />,
  }),
  columnHelper.accessor("dataset_row_id", {
    header: "Dataset Row ID",
    Cell: ({ cell }) => {
      const rowId = cell.getValue();
      return <CopyableChip label={rowId} />;
    },
  }),
];
