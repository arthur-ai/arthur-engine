import DoneAllIcon from "@mui/icons-material/DoneAll";
import ErrorIcon from "@mui/icons-material/Error";
import PendingOutlinedIcon from "@mui/icons-material/PendingOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { capitalize, Stack, Typography } from "@mui/material";

import { TestCaseStatus } from "@/lib/api-client/api-client";

type Props = {
  status: TestCaseStatus;
};

export const StatusBadge = ({ status }: Props) => {
  const color = STATUS_COLORS[status];
  const Icon = ICONS[status];
  return (
    <Stack
      gap={0.5}
      direction="row"
      alignItems="center"
      color={color}
      className="px-1 bg-[color-mix(in_oklab,var(--bucket-color)_20%,white)] w-fit border border-(--bucket-color)/50 rounded-md text-nowrap"
      style={{ "--bucket-color": color } as React.CSSProperties}
    >
      <Icon sx={{ fontSize: 12 }} />
      <Typography variant="caption" color={color} fontWeight={500} className="select-none">
        {capitalize(status)}
      </Typography>
    </Stack>
  );
};

const STATUS_COLORS: Record<TestCaseStatus, string> = {
  queued: "var(--color-gray-600)",
  running: "var(--color-blue-600)",
  evaluating: "var(--color-gray-600)",
  failed: "var(--color-red-600)",
  completed: "var(--color-green-600)",
};

const ICONS = {
  queued: PendingOutlinedIcon,
  running: PlayArrowIcon,
  evaluating: PendingOutlinedIcon,
  failed: ErrorIcon,
  completed: DoneAllIcon,
} as const;
