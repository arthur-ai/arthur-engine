import DoneAllIcon from "@mui/icons-material/DoneAll";
import ErrorIcon from "@mui/icons-material/Error";
import WarningIcon from "@mui/icons-material/Warning";
import { Stack, Tooltip } from "@mui/material";

type Props = {
  statusCode: StatusCode;
};

export const StatusCode = ({ statusCode }: Props) => {
  const Icon = STATUS_CODE_ICONS[statusCode] ?? STATUS_CODE_ICONS.Unset;
  const color = STATUS_CODE_COLORS[statusCode] ?? STATUS_CODE_COLORS.Unset;

  return (
    <Tooltip title={statusCode} sx={{ width: "min-content" }}>
      <Stack gap={0.5} direction="row" alignItems="center">
        <Icon sx={{ fontSize: 16 }} color={color} />
      </Stack>
    </Tooltip>
  );
};

const STATUS_CODE_COLORS = {
  Ok: "success",
  Error: "error",
  Unset: "warning",
} as const;

const STATUS_CODE_ICONS = {
  Ok: DoneAllIcon,
  Error: ErrorIcon,
  Unset: WarningIcon,
} as const;

type StatusCode = keyof typeof STATUS_CODE_COLORS;

export const isValidStatusCode = (statusCode: string): statusCode is StatusCode => {
  return Object.keys(STATUS_CODE_COLORS).includes(statusCode);
};
