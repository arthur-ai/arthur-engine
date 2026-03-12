import { Chip, Link as MuiLink, Tooltip, Typography } from "@mui/material";
import { createColumnHelper } from "@tanstack/react-table";
import { Link } from "react-router-dom";

import { LiveEvalActions } from "../components/actions";

import { CopyableChip } from "@/components/common";
import type { ContinuousEvalResponse } from "@/lib/api-client/api-client";
import { formatDateInTimezone } from "@/utils/formatters";

const columnHelper = createColumnHelper<ContinuousEvalResponse>();

export const createColumns = ({ onEdit, timezone, use24Hour }: { onEdit: (id: string) => void; timezone: string; use24Hour: boolean }) => {
  const columns = [
    columnHelper.accessor("name", {
      header: "Name",
      cell: ({ getValue, row }) => {
        const { task_id, id } = row.original;
        return (
          <MuiLink component={Link} to={`/tasks/${task_id}/continuous-evals/${id}`} className="text-nowrap">
            {getValue()}
          </MuiLink>
        );
      },
    }),
    columnHelper.accessor("enabled", {
      header: "Status",
      cell: ({ getValue }) => {
        const enabled = getValue();
        return <Chip label={enabled ? "Enabled" : "Disabled"} color={enabled ? "success" : "default"} size="small" />;
      },
    }),
    columnHelper.accessor("description", {
      header: "Description",
      cell: ({ getValue }) => {
        const description = getValue();
        return (
          <Tooltip title={description} className="w-min">
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 200 }}
            >
              {description}
            </Typography>
          </Tooltip>
        );
      },
    }),
    columnHelper.accessor(
      (row) => {
        const { llm_eval_name, llm_eval_version } = row;
        return `${llm_eval_name} v${llm_eval_version}`;
      },
      {
        id: "llm-evaluator",
        header: "Evaluator",
        cell: ({ getValue }) => {
          return (
            <Typography variant="body2" color="text.secondary">
              {getValue()}
            </Typography>
          );
        },
      }
    ),
    columnHelper.accessor("created_at", {
      header: "Created At",
      sortingFn: "datetime",
      cell: ({ getValue }) => formatDateInTimezone(getValue(), timezone, { hour12: !use24Hour }),
    }),
    columnHelper.accessor("updated_at", {
      header: "Updated At",
      sortingFn: "datetime",
      cell: ({ getValue }) => formatDateInTimezone(getValue(), timezone, { hour12: !use24Hour }),
    }),
    columnHelper.accessor("id", {
      header: "ID",
      cell: ({ getValue }) => {
        const id = getValue();
        return <CopyableChip label={id} sx={{ fontFamily: "monospace" }} />;
      },
    }),
    columnHelper.display({
      id: "actions",
      cell: ({ row }) => {
        return <LiveEvalActions config={row.original} onEdit={onEdit} />;
      },
    }),
  ];

  return columns;
};
