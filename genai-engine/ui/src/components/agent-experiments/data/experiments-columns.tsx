import { createMRTColumnHelper } from "material-react-table";

import type { AgentExperiment } from "../types";

const columnHelper = createMRTColumnHelper<AgentExperiment>();

export const createColumns = () => [
  columnHelper.accessor("name", {
    header: "Name",
  }),
  columnHelper.accessor("dataset_id", {
    header: "Dataset ID",
  }),
  columnHelper.accessor("endpoint_id", {
    header: "Endpoint ID",
  }),
];
