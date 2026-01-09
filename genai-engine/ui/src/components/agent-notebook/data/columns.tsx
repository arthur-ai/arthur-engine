import { createMRTColumnHelper } from "material-react-table";

import { AgenticNotebookSummary } from "@/lib/api-client/api-client";

const columnHelper = createMRTColumnHelper<AgenticNotebookSummary>();

export const columns = [
  columnHelper.accessor("name", {
    header: "Name",
  }),
  columnHelper.accessor("description", {
    header: "Description",
  }),
  columnHelper.accessor("created_at", {
    header: "Created At",
  }),
  columnHelper.accessor("updated_at", {
    header: "Updated At",
  }),
  columnHelper.accessor("run_count", {
    header: "Run Count",
  }),
];
