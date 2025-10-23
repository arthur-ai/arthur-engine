import { Tooltip } from "@mui/material";
import { createColumnHelper } from "@tanstack/react-table";

import { CopyableChip } from "@/components/common";
import { TraceUserMetadataResponse } from "@/lib/api-client/api-client";

const columnHelper = createColumnHelper<TraceUserMetadataResponse>();

export const userLevelColumns = [
  columnHelper.accessor("user_id", {
    header: "User ID",
    cell: ({ getValue }) => {
      const label = getValue();
      return (
        <Tooltip title={label}>
          <span>
            <CopyableChip label={label} />
          </span>
        </Tooltip>
      );
    },
  }),
  columnHelper.accessor("session_count", {
    header: "Session Count",
    cell: ({ getValue }) => `${getValue()} sessions`,
  }),
];
