import AccessTimeOutlinedIcon from "@mui/icons-material/AccessTimeOutlined";
import { Stack, Typography } from "@mui/material";

import { useBucketer } from "../../context/bucket-context";
import { Bucket } from "../../utils/duration";

import { formatDuration } from "@/utils/formatters";

export const DurationCell = ({ duration }: { duration: number }) => {
  const bucketer = useBucketer();
  const bucket = duration ? bucketer(duration) : "ok";
  const color = BUCKET_COLORS[bucket];

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
        {formatDuration(duration)}
      </Typography>
    </Stack>
  );
};

export const BUCKET_COLORS: Record<Bucket, string> = {
  ok: "var(--color-green-700)",
  warning: "var(--color-amber-700)",
  bad: "var(--color-red-800)",
};
