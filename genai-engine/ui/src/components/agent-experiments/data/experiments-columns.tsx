import { createMRTColumnHelper } from "material-react-table";

import { CopyableChip } from "@/components/common";
import { AgenticExperimentSummary } from "@/lib/api-client/api-client";

const columnHelper = createMRTColumnHelper<AgenticExperimentSummary>();

export const createColumns = () => [
  columnHelper.accessor("name", {
    header: "Name",
  }),
  columnHelper.accessor("dataset_name", {
    header: "Dataset Name",
  }),
  columnHelper.accessor("http_template.endpoint_name", {
    header: "Endpoint Name",
  }),
  columnHelper.accessor("http_template.endpoint_url", {
    header: "Endpoint URL",
  }),
  columnHelper.accessor("id", {
    header: "ID",
    Cell: ({ cell }) => {
      const value = cell.getValue() as string;
      return <CopyableChip label={value} sx={{ fontFamily: "monospace" }} />;
    },
  }),
  columnHelper.accessor("dataset_id", {
    header: "Dataset ID",
    Cell: ({ cell }) => {
      const value = cell.getValue() as string;
      return <CopyableChip label={value} sx={{ fontFamily: "monospace" }} />;
    },
  }),
];
