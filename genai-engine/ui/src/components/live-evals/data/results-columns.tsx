import VisibilityIcon from "@mui/icons-material/Visibility";
import { IconButton } from "@mui/material";
import { createColumnHelper } from "@tanstack/react-table";

import { AgenticAnnotationMetadataResponse } from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";

const columnHelper = createColumnHelper<AgenticAnnotationMetadataResponse>();

export const createColumns = ({ onView }: { onView: (annotationId: string) => void }) => [
  columnHelper.accessor("annotation_type", {
    header: "Annotation Type",
    cell: ({ getValue }) => getValue(),
  }),
  columnHelper.accessor("annotation_score", {
    header: "Annotation Score",
    cell: ({ getValue }) => getValue(),
  }),
  columnHelper.accessor("cost", {
    header: "Cost",
    cell: ({ getValue }) => formatCurrency(getValue() ?? 0),
  }),
  columnHelper.accessor("run_status", {
    header: "Run Status",
    cell: ({ getValue }) => getValue(),
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
