import { createMRTColumnHelper } from "material-react-table";

import type { AgenticTestCase } from "@/lib/api-client/api-client";

const columnHelper = createMRTColumnHelper<AgenticTestCase>();

export const columns = [
  columnHelper.accessor("dataset_row_id", {
    header: "Dataset Row ID",
  }),
  columnHelper.accessor("status", {
    header: "Status",
  }),
  columnHelper.accessor("agentic_result.output.status_code", {
    header: "Status Code",
  }),
];
