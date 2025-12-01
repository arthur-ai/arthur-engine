import CircleIcon from "@mui/icons-material/Circle";
import { createColumnHelper } from "@tanstack/react-table";

import { CopyableChip } from "@/components/common";
import { formatDate } from "@/utils/formatters";

export type LiveEval = {
  id: string;
  name: string;
  status: "active" | "inactive";
  createdAt: string;
  updatedAt: string;
};

const columnHelper = createColumnHelper<LiveEval>();

export const columns = [
  columnHelper.accessor("name", {
    header: "Name",
  }),
  columnHelper.accessor("status", {
    header: "Status",
    cell: ({ getValue }) => {
      const status = getValue();
      const color = status === "active" ? "success.main" : "error.main";
      return <CircleIcon sx={{ color, fontSize: 16 }} />;
    },
  }),
  columnHelper.accessor("createdAt", {
    header: "Created At",
    sortingFn: "datetime",
    cell: ({ getValue }) => formatDate(getValue()),
  }),
  columnHelper.accessor("id", {
    header: "ID",
    cell: ({ getValue }) => {
      const id = getValue();
      return <CopyableChip label={id} sx={{ fontFamily: "monospace" }} />;
    },
  }),
];
