import DoneAllIcon from "@mui/icons-material/DoneAll";
import ErrorIcon from "@mui/icons-material/Error";
import PendingOutlinedIcon from "@mui/icons-material/PendingOutlined";
import { capitalize, Stack, Tooltip, Typography } from "@mui/material";
import { memo } from "react";

import { cn } from "@/utils/cn";

type Props = {
  status: string;
  disableLabel?: boolean;
  className?: string;
};

export const SpanStatusBadge = memo(({ status, disableLabel = false, className }: Props) => {
  const color = STATUS_COLORS[status] ?? STATUS_COLORS.Unset;
  const Icon = STATUS_ICONS[status] ?? STATUS_ICONS.Unset;

  return (
    <Tooltip title={capitalize(status)}>
      <Stack
        gap={0.5}
        direction="row"
        alignItems="center"
        color={color}
        data-icon-only={disableLabel ? "" : undefined}
        className={cn(
          "px-1 data-icon-only:py-1 bg-[color-mix(in_oklab,var(--bucket-color)_20%,white)] w-fit border border-(--bucket-color)/50 rounded-md text-nowrap",
          className
        )}
        style={{ "--bucket-color": color } as React.CSSProperties}
      >
        <Icon sx={{ fontSize: 12 }} />
        {!disableLabel && (
          <Typography variant="caption" color={color} fontWeight={500} className="select-none">
            {capitalize(status)}
          </Typography>
        )}
      </Stack>
    </Tooltip>
  );
});

const STATUS_COLORS = {
  Ok: "var(--color-green-600)",
  Error: "var(--color-red-600)",
  Unset: "var(--color-gray-600)",
} as Record<string, string>;

const STATUS_ICONS = {
  Ok: DoneAllIcon,
  Error: ErrorIcon,
  Unset: PendingOutlinedIcon,
} as Record<string, typeof DoneAllIcon>;
