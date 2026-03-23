import DoneAllIcon from "@mui/icons-material/DoneAll";
import ErrorIcon from "@mui/icons-material/Error";
import PendingOutlinedIcon from "@mui/icons-material/PendingOutlined";
import { capitalize, Stack, Tooltip, Typography } from "@mui/material";
import { alpha, type Theme, useTheme } from "@mui/material/styles";
import { memo } from "react";

type Props = {
  status: string;
  disableLabel?: boolean;
  className?: string;
};

const getStatusColor = (theme: Theme, status: string): string => {
  const map: Record<string, string> = {
    Ok: theme.palette.success.main,
    Error: theme.palette.error.main,
    Unset: theme.palette.text.secondary,
  };
  return map[status] ?? theme.palette.text.secondary;
};

export const SpanStatusBadge = memo(({ status, disableLabel = false }: Props) => {
  const theme = useTheme();
  const color = getStatusColor(theme, status);
  const Icon = STATUS_ICONS[status] ?? STATUS_ICONS.Unset;

  return (
    <Tooltip title={capitalize(status)}>
      <Stack
        gap={0.5}
        direction="row"
        alignItems="center"
        sx={{
          color,
          px: 1,
          ...(disableLabel && { py: 1 }),
          backgroundColor: alpha(color, 0.12),
          width: "fit-content",
          border: `1px solid ${alpha(color, 0.4)}`,
          borderRadius: 1,
          whiteSpace: "nowrap",
        }}
      >
        <Icon sx={{ fontSize: 12 }} />
        {!disableLabel && (
          <Typography variant="caption" sx={{ color }} fontWeight={500} className="select-none">
            {capitalize(status)}
          </Typography>
        )}
      </Stack>
    </Tooltip>
  );
});

const STATUS_ICONS = {
  Ok: DoneAllIcon,
  Error: ErrorIcon,
  Unset: PendingOutlinedIcon,
} as Record<string, typeof DoneAllIcon>;
