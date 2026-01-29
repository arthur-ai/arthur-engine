import AccessTimeOutlinedIcon from "@mui/icons-material/AccessTimeOutlined";
import { Stack, Typography } from "@mui/material";
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

export const BUCKET_COLORS = {
  ok: "var(--color-green-700)",
  warning: "var(--color-amber-700)",
  bad: "var(--color-red-800)",
} as const;

type Props = {
  duration: number;
  bucketer?: Bucketer;
  formatDuration?: (n: number) => string;
};

export const DurationCell = ({ duration, bucketer, formatDuration }: Props) => {
  const b = bucketer ?? defaultBucketer;
  const bucket = duration ? b(duration) : "ok";
  const color = BUCKET_COLORS[bucket];
  const formatted = (formatDuration ?? defaultFormatDuration)(duration);

  return (
    <Stack
      gap={0.5}
      direction="row"
      alignItems="center"
      color={color}
      className="px-1 bg-[color-mix(in_oklab,var(--bucket-color)_20%,white)] w-fit border border-(--bucket-color)/50 rounded-md text-nowrap"
      style={{ "--bucket-color": color } as React.CSSProperties}
    >
      <AccessTimeOutlinedIcon sx={{ fontSize: 12 }} />
      <Typography variant="caption" color={color} fontWeight={500} className="select-none">
        {formatted}
      </Typography>
    </Stack>
  );
};
