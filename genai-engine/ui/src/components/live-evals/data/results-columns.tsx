import { createColumnHelper } from "@tanstack/react-table";

import { AgenticAnnotationMetadataResponse } from "@/lib/api-client/api-client";

const columnHelper = createColumnHelper<AgenticAnnotationMetadataResponse>();

export const resultsColumns = [
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
    cell: ({ getValue }) => getValue(),
  }),
  columnHelper.accessor("run_status", {
    header: "Run Status",
    cell: ({ getValue }) => getValue(),
  }),
];
