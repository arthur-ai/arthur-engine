import AccessTimeOutlinedIcon from "@mui/icons-material/AccessTimeOutlined";
import { Stack, Typography } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import dayjs from "dayjs";
import duration from "dayjs/plugin/duration";

import { defaultBucketer, type Bucketer } from "../../utils/duration";

dayjs.extend(duration);

function defaultFormatDuration(durationMs: number): string {
  return dayjs
    .duration(+durationMs.toFixed(0), "millisecond")
    .format("H[h] m[m] s[s] SSS[ms]")
    .replace(/\b0[hmst]\b/g, "");
}

const BUCKET_PALETTE = {
  ok: "success",
  warning: "warning",
  bad: "error",
} as const;

type Props = {
  duration: number;
  bucketer?: Bucketer;
  formatDuration?: (n: number) => string;
};

export const DurationCell = ({ duration, bucketer, formatDuration }: Props) => {
  const theme = useTheme();
  const b = bucketer ?? defaultBucketer;
  const bucket = duration ? b(duration) : "ok";
  const color = theme.palette[BUCKET_PALETTE[bucket]].main;
  const formatted = (formatDuration ?? defaultFormatDuration)(duration);

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
      <AccessTimeOutlinedIcon sx={{ fontSize: 12 }} />
      <Typography variant="caption" sx={{ color }} fontWeight={500} className="select-none">
        {formatted}
      </Typography>
    </Stack>
  );
};
