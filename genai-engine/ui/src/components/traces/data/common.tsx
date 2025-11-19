import AccessTimeOutlinedIcon from "@mui/icons-material/AccessTimeOutlined";
import GeneratingTokensOutlinedIcon from "@mui/icons-material/GeneratingTokensOutlined";
import TollOutlinedIcon from "@mui/icons-material/TollOutlined";
import { Stack, Tooltip, Typography } from "@mui/material";

import { useBucketer } from "../context/bucket-context";
import { Bucket } from "../utils/duration";

import { formatCurrency, formatDuration } from "@/utils/formatters";

type TokenCountProps = {
  prompt?: number;
  completion?: number;
  total: number;
};

export const TokenCountTooltip = ({ prompt, completion, total }: TokenCountProps) => {
  if (!total)
    return (
      <Stack direction="row" alignItems="center" gap={0.5}>
        <GeneratingTokensOutlinedIcon sx={{ fontSize: 16 }} />
        <Typography variant="body2" color="text.primary" fontWeight={700} fontSize={12} className="select-none">
          N/A
        </Typography>
      </Stack>
    );
  return (
    <Tooltip
      title={
        <Stack direction="column" gap={0} sx={{ fontFamily: "monospace" }}>
          <Typography variant="body2" fontSize={12}>
            Prompt: {prompt ?? "N/A"} tokens
          </Typography>
          <Typography variant="body2" fontSize={12}>
            Completion: {completion ?? "N/A"} tokens
          </Typography>
        </Stack>
      }
    >
      <Typography variant="body2" color="text.primary" fontWeight={700} fontSize={12} className="select-none">
        <GeneratingTokensOutlinedIcon sx={{ fontSize: 16, mr: 0.5 }} /> {total} tokens
      </Typography>
    </Tooltip>
  );
};

type TokenCostProps = TokenCountProps;

export const TokenCostTooltip = ({ prompt, completion, total }: TokenCostProps) => {
  if (!total)
    return (
      <Stack direction="row" alignItems="center" gap={0.5}>
        <TollOutlinedIcon sx={{ fontSize: 16 }} />
        <Typography variant="body2" color="text.primary" fontWeight={700} fontSize={12} className="select-none">
          N/A
        </Typography>
      </Stack>
    );

  return (
    <Tooltip
      title={
        <Stack direction="column" gap={0} sx={{ fontFamily: "monospace" }}>
          <Typography variant="body2" fontSize={12}>
            Prompt: {prompt ? formatCurrency(prompt) : "N/A"}
          </Typography>
          <Typography variant="body2" fontSize={12}>
            Completion: {completion ? formatCurrency(completion) : "N/A"}
          </Typography>
        </Stack>
      }
    >
      <Typography variant="body2" color="text.primary" fontWeight={700} fontSize={12} className="select-none">
        <TollOutlinedIcon sx={{ fontSize: 16, mr: 0.5 }} /> {formatCurrency(total)}
      </Typography>
    </Tooltip>
  );
};

export const TruncatedText = ({ text }: { text: string }) => {
  return <span className="truncate p-2 bg-gray-100 rounded-md">{text}</span>;
};

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
