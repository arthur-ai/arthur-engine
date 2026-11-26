import { formatCost, type DisplayCurrency } from "@arthur/shared-components";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { Chip, IconButton } from "@mui/material";
import { createColumnHelper, tableFeatures } from "@tanstack/react-table";

import { AgenticAnnotationResponse } from "@/lib/api-client/api-client";
import { getStatusChipSx } from "@/utils/statusChipStyles";

export const resultsFeatures = tableFeatures({});

const columnHelper = createColumnHelper<typeof resultsFeatures, AgenticAnnotationResponse>();

/** What a run judged: the trace, the trace through its span runs, or one span. */
export const describeRunTarget = (run: Pick<AgenticAnnotationResponse, "run_level" | "span_id">): string => {
  if (run.run_level === "span") return `Span ${run.span_id ?? ""}`.trim();
  if (run.run_level === "span_rollup") return "Trace, from its spans";
  return "Trace";
};

export const createColumns = ({ onView, currency }: { onView: (annotationId: string) => void; currency: DisplayCurrency }) =>
  columnHelper.columns([
    columnHelper.accessor("continuous_eval_name", {
      header: "Eval Name",
      cell: ({ getValue }) => getValue() ?? "N/A",
    }),
    columnHelper.accessor((run) => describeRunTarget(run), {
      id: "judged",
      header: "Judged",
      cell: ({ getValue }) => getValue(),
    }),
    columnHelper.accessor("label", {
      header: "Label",
      cell: ({ getValue }) => {
        const label = getValue();
        return label ? <Chip label={label} size="small" variant="outlined" /> : null;
      },
    }),
    columnHelper.accessor("annotation_score", {
      header: "Annotation Score",
      cell: ({ getValue }) => getValue(),
    }),
    columnHelper.accessor("cost", {
      header: "Cost",
      cell: ({ getValue }) => {
        const cost = getValue();
        return cost != null ? formatCost(cost, currency) : "N/A";
      },
    }),
    columnHelper.accessor("run_status", {
      header: "Run Status",
      cell: ({ getValue }) => {
        const status = getValue();
        return status ? <Chip label={status} size="small" sx={getStatusChipSx(status)} /> : null;
      },
    }),
    columnHelper.display({
      id: "actions",
      cell: ({ row }) => {
        const annotationId = row.original.id;
        return (
          <IconButton size="small" onClick={() => onView(annotationId)}>
            <VisibilityIcon fontSize="small" />
          </IconButton>
        );
      },
    }),
  ]);
