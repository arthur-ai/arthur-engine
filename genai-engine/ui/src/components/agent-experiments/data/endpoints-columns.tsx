import { createMRTColumnHelper } from "material-react-table";

import type { AgentExperimentEndpoint } from "../types";

import { Highlight } from "@/components/common/Highlight";

const columnHelper = createMRTColumnHelper<AgentExperimentEndpoint>();

export const createColumns = () => [
  columnHelper.accessor("name", {
    header: "Name",
  }),
  columnHelper.accessor("url", {
    header: "URL",
  }),
  columnHelper.accessor("body", {
    header: "Body",
    Cell: ({ cell }) => {
      const value = cell.getValue() as string;
      if (!value) return null;
      return <Highlight code={value} language="json" unwrapped />;
    },
  }),
];
