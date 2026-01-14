import { Typography } from "@mui/material";
import { createMRTColumnHelper } from "material-react-table";

import { StatusBadge } from "../components/status-badge";

import { CopyableChip } from "@/components/common";
import { AgenticExperimentSummary } from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";

const columnHelper = createMRTColumnHelper<AgenticExperimentSummary>();

export const createColumns = () => [
  columnHelper.accessor("name", {
    header: "Name",
  }),
  columnHelper.accessor("dataset_name", {
    header: "Dataset Name",
  }),
  columnHelper.accessor("status", {
    header: "Status",
    Cell: ({ cell }) => <StatusBadge status={cell.getValue()} />,
  }),
  columnHelper.accessor("http_template.endpoint_name", {
    header: "Endpoint Name",
  }),
  columnHelper.accessor("http_template.endpoint_url", {
    header: "Endpoint URL",
  }),
  columnHelper.accessor("total_cost", {
    header: "Total Cost",
    Cell: ({ cell }) => {
      const value = cell.getValue() as string;
      if (!value) return "N/A";
      return <Typography variant="body2">{formatCurrency(parseFloat(value))}</Typography>;
    },
  }),
  columnHelper.accessor("id", {
    header: "ID",
    Cell: ({ cell }) => {
      const value = cell.getValue() as string;
      return <CopyableChip label={value} sx={{ fontFamily: "monospace" }} />;
    },
  }),
  columnHelper.accessor("dataset_id", {
    header: "Dataset ID",
    Cell: ({ cell }) => {
      const value = cell.getValue() as string;
      return <CopyableChip label={value} sx={{ fontFamily: "monospace" }} />;
    },
  }),
];
