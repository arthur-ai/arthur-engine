import VisibilityIcon from "@mui/icons-material/Visibility";
import { Chip, IconButton } from "@mui/material";
import { createColumnHelper } from "@tanstack/react-table";

import { AgenticAnnotationResponse } from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";

const columnHelper = createColumnHelper<AgenticAnnotationResponse>();

const getStatusChipSx = (status: string) => {
  const colorMap: Record<string, any> = {
    pending: { color: "text.secondary", borderColor: "text.secondary" },
    running: { color: "primary.main", borderColor: "primary.main" },
    passed: { color: "success.main", borderColor: "success.main" },
    failed: { color: "error.main", borderColor: "error.main" },
    error: { color: "error.main", borderColor: "error.main" },
    skipped: { color: "warning.main", borderColor: "warning.main" },
  };

  const colors = colorMap[status.toLowerCase()] || { color: "text.secondary", borderColor: "text.secondary" };
  return {
    ...colors,
    backgroundColor: "transparent",
    borderWidth: 1,
    borderStyle: "solid",
  };
};

export const createColumns = ({ onView }: { onView: (annotationId: string) => void }) => [
  columnHelper.accessor("continuous_eval_name", {
    header: "Eval Name",
    cell: ({ getValue }) => getValue() ?? "N/A",
  }),
  columnHelper.accessor("annotation_score", {
    header: "Annotation Score",
    cell: ({ getValue }) => getValue(),
  }),
  columnHelper.accessor("cost", {
    header: "Cost",
    cell: ({ getValue }) => {
      const cost = getValue();
      return cost != null ? formatCurrency(cost) : "N/A";
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
];
