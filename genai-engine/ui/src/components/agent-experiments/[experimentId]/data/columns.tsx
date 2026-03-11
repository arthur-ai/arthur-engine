import { createMRTColumnHelper } from "material-react-table";

import { StatusBadge } from "@/components/agent-experiments/components/status-badge";
import { CopyableChip } from "@/components/common";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import type { AgenticTestCase } from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";

const columnHelper = createMRTColumnHelper<AgenticTestCase>();

function CostCell({ value }: { value: string | null | undefined }) {
  const { defaultCurrency } = useDisplaySettings();
  return value ? formatCurrency(parseFloat(value), defaultCurrency) : "N/A";
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
