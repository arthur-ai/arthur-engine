import { Typography } from "@mui/material";
import { createMRTColumnHelper } from "material-react-table";

import { StatusBadge } from "@/components/agent-experiments/components/status-badge";
import { CopyableChip } from "@/components/common";
import { AgenticNotebookSummary } from "@/lib/api-client/api-client";
import { formatDateInTimezone } from "@/utils/formatters";

const columnHelper = createMRTColumnHelper<AgenticNotebookSummary>();

export const createColumns = (timezone: string) => [
  columnHelper.accessor("name", {
    header: "Name",
  }),
  columnHelper.accessor("description", {
    header: "Description",
  }),
  columnHelper.accessor("latest_run_status", {
    header: "Latest Run Status",
    Cell: ({ cell }) => {
      const value = cell.getValue();
      if (!value) return <Typography variant="body2">N/A</Typography>;
      return <StatusBadge status={value} />;
    },
  }),
  columnHelper.accessor("run_count", {
    header: "Runs",
  }),
  columnHelper.accessor("created_at", {
    header: "Created At",
    Cell: ({ cell }) => {
      const value = cell.getValue() as string;
      return <Typography variant="body2">{formatDateInTimezone(value, timezone)}</Typography>;
    },
  }),
  columnHelper.accessor("updated_at", {
    header: "Updated At",
    Cell: ({ cell }) => {
      const value = cell.getValue() as string;
      return <Typography variant="body2">{formatDateInTimezone(value, timezone)}</Typography>;
    },
  }),

  columnHelper.accessor("id", {
    header: "ID",
    Cell: ({ cell }) => {
      const value = cell.getValue();
      return <CopyableChip label={value} sx={{ fontFamily: "monospace" }} />;
    },
  }),
  columnHelper.accessor("latest_run_id", {
    header: "Latest Run ID",
    Cell: ({ cell }) => {
      const value = cell.getValue();

      if (!value) return <Typography variant="body2">N/A</Typography>;

      return <CopyableChip label={value} sx={{ fontFamily: "monospace" }} />;
    },
  }),
];
