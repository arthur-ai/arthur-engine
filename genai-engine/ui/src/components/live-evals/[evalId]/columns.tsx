import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { Chip, IconButton, Tooltip, Typography } from "@mui/material";
import { createMRTColumnHelper } from "material-react-table";
import { Link } from "react-router-dom";

import { CopyableChip } from "@/components/common";
import { serializeDrawerTarget } from "@/components/traces/hooks/useDrawerTarget";
import { AgenticAnnotationResponse } from "@/lib/api-client/api-client";
import { formatCurrency, formatDate } from "@/utils/formatters";
import { getStatusChipSx } from "@/utils/statusChipStyles";

const columnHelper = createMRTColumnHelper<AgenticAnnotationResponse>();

export const createColumns = ({ taskId }: { taskId: string }) => [
  columnHelper.accessor("trace_id", {
    header: "Trace ID",
    Cell: ({ cell }) => <CopyableChip label={cell.getValue()} sx={{ fontFamily: "monospace", fontSize: "0.75rem" }} />,
  }),
  columnHelper.accessor("annotation_score", {
    header: "Score",
    Cell: ({ cell }) => {
      const score = cell.getValue();
      return <Typography variant="body2">{score != null ? score : "—"}</Typography>;
    },
  }),
  columnHelper.accessor("run_status", {
    header: "Status",
    Cell: ({ cell }) => {
      const status = cell.getValue();
      return status ? (
        <Chip label={status} size="small" variant="outlined" sx={getStatusChipSx(status)} />
      ) : (
        <Typography variant="body2">—</Typography>
      );
    },
  }),
  columnHelper.accessor("cost", {
    header: "Cost",
    Cell: ({ cell }) => {
      const cost = cell.getValue();
      return <Typography variant="body2">{cost != null ? formatCurrency(cost) : "N/A"}</Typography>;
    },
  }),
  columnHelper.accessor("created_at", {
    header: "Created",
    Cell: ({ cell }) => (
      <Typography variant="body2" color="text.secondary">
        {formatDate(cell.getValue())}
      </Typography>
    ),
  }),
  columnHelper.display({
    id: "view_trace",
    header: "",
    size: 48,
    Cell: ({ row }) => (
      <Tooltip title="View trace">
        <IconButton
          size="small"
          component={Link}
          to={`/tasks/${taskId}/traces${serializeDrawerTarget({ target: "trace", id: row.original.trace_id })}`}
          onClick={(e: React.MouseEvent) => e.stopPropagation()}
        >
          <OpenInNewIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    ),
  }),
];
