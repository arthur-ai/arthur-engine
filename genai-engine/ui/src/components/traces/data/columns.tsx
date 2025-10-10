import { createColumnHelper } from "@tanstack/react-table";
import { TraceResponse } from "@/lib/api-client/api-client";
import dayjs from "dayjs";
import { getSpanInput, getSpanOutput } from "../utils/spans";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { CopyableChip } from "../../common";
import Tooltip from "@mui/material/Tooltip";

const columnHelper = createColumnHelper<TraceResponse>();

export const columns = [
  columnHelper.accessor("trace_id", {
    header: "Trace ID",
    size: 100,
    cell: ({ getValue }) => {
      const label = getValue();
      return (
        <Tooltip title={label}>
          <span>
            <CopyableChip label={label} sx={{ fontFamily: "monospace" }} />
          </span>
        </Tooltip>
      );
    },
  }),
  columnHelper.accessor(({ root_spans }) => root_spans?.at(0)?.span_name, {
    header: "Name",
  }),
  columnHelper.accessor(({ root_spans }) => getSpanInput(root_spans?.[0]), {
    header: "Input",
    cell: ({ getValue }) => {
      const label = getValue();

      if (!label)
        return <Chip color="default" variant="outlined" label="No input" />;

      return (
        <Typography
          variant="caption"
          sx={{
            fontFamily: "monospace",
          }}
        >
          {label}
        </Typography>
      );
    },
    size: 200,
  }),
  columnHelper.accessor(({ root_spans }) => getSpanOutput(root_spans?.[0]), {
    header: "Output",
    cell: ({ getValue }) => {
      const label = getValue();

      if (!label)
        return <Chip color="default" variant="outlined" label="No output" />;

      return (
        <Typography
          variant="caption"
          sx={{
            fontFamily: "monospace",
          }}
        >
          {label}
        </Typography>
      );
    },
    size: 200,
  }),
  columnHelper.accessor("start_time", {
    header: "Timestamp",
    cell: ({ getValue }) => dayjs(getValue()).format("YYYY-MM-DD HH:mm:ss"),
    sortingFn: "datetime",
  }),
  columnHelper.accessor(
    ({ start_time, end_time }) => {
      const start = dayjs(start_time);
      const end = dayjs(end_time);
      return end.diff(start, "ms");
    },
    {
      header: "Duration",
      cell: ({ getValue }) => {
        const duration = getValue();
        return `${duration}ms`;
      },
    }
  ),
];
