import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { Chip, IconButton } from "@mui/material";
import { createColumnHelper } from "@tanstack/react-table";

import { AgenticAnnotationResponse } from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";
import { getStatusChipSx } from "@/utils/statusChipStyles";

const columnHelper = createColumnHelper<AgenticAnnotationResponse>();

const renderAnnotationScore = (score: number | null | undefined) => {
  if (score === 1) {
    return <Chip icon={<CheckCircleIcon />} label="Pass" color="success" size="small" sx={{ fontWeight: 600 }} />;
  }
  if (score === 0) {
    return <Chip icon={<ErrorIcon />} label="Fail" color="error" size="small" sx={{ fontWeight: 600 }} />;
  }
  return score ?? "N/A";
};

export const createColumns = ({ onView, defaultCurrency }: { onView: (annotationId: string) => void; defaultCurrency: string }) => [
  columnHelper.accessor("continuous_eval_name", {
    header: "Eval Name",
    cell: ({ getValue }) => getValue() ?? "N/A",
  }),
  columnHelper.accessor("annotation_score", {
    header: "Annotation Score",
    cell: ({ getValue }) => renderAnnotationScore(getValue()),
  }),
  columnHelper.accessor("cost", {
    header: "Cost",
    cell: ({ getValue }) => {
      const cost = getValue();
      return cost != null ? formatCurrency(cost, defaultCurrency) : "N/A";
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
