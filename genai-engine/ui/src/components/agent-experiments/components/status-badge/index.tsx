import DoneAllIcon from "@mui/icons-material/DoneAll";
import ErrorIcon from "@mui/icons-material/Error";
import PendingOutlinedIcon from "@mui/icons-material/PendingOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { capitalize, Stack, Typography } from "@mui/material";
import { alpha, type Theme, useTheme } from "@mui/material/styles";

import { TestCaseStatus } from "@/lib/api-client/api-client";

type Props = {
  status: TestCaseStatus;
};

const getStatusColor = (theme: Theme, status: TestCaseStatus): string => {
  const map: Record<TestCaseStatus, string> = {
    queued: theme.palette.text.secondary,
    running: theme.palette.info.main,
    evaluating: theme.palette.text.secondary,
    failed: theme.palette.error.main,
    completed: theme.palette.success.main,
  };
  return map[status];
};

export const StatusBadge = ({ status }: Props) => {
  const theme = useTheme();
  const color = getStatusColor(theme, status);
  const Icon = ICONS[status];

  return (
    <Stack
      gap={0.5}
      direction="row"
      alignItems="center"
      sx={{
        color,
        px: 1,
        backgroundColor: alpha(color, 0.12),
        width: "fit-content",
        border: `1px solid ${alpha(color, 0.4)}`,
        borderRadius: 1,
        whiteSpace: "nowrap",
      }}
    >
      <Icon sx={{ fontSize: 12 }} />
      <Typography variant="caption" sx={{ color }} fontWeight={500} className="select-none">
        {capitalize(status)}
      </Typography>
    </Stack>
  );
};

const ICONS = {
  queued: PendingOutlinedIcon,
  running: PlayArrowIcon,
  evaluating: PendingOutlinedIcon,
  failed: ErrorIcon,
  completed: DoneAllIcon,
} as const;
