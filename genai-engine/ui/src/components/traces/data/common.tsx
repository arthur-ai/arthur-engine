import { Stack, Tooltip, Typography } from "@mui/material";

import { formatCurrency } from "@/utils/formatters";

type TokenCountProps = {
  prompt?: number;
  completion?: number;
  total: number;
};

export const TokenCountTooltip = ({ prompt, completion, total }: TokenCountProps) => {
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
        &sum; {total} tokens
      </Typography>
    </Tooltip>
  );
};

type TokenCostProps = TokenCountProps;

export const TokenCostTooltip = ({ prompt, completion, total }: TokenCostProps) => {
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
        &sum; {formatCurrency(total)}
      </Typography>
    </Tooltip>
  );
};
