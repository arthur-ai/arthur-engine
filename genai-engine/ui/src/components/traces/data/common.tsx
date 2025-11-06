import { Stack, Tooltip } from "@mui/material";

import { formatCurrency } from "@/utils/formatters";

type TokenCountProps = {
  prompt: number;
  completion: number;
  total: number;
};

export const TokenCountTooltip = ({ prompt, completion, total }: TokenCountProps) => {
  return (
    <Tooltip
      title={
        <Stack direction="column" gap={0} sx={{ fontFamily: "monospace" }}>
          <span>Prompt: {prompt} tokens</span>
          <span>Completion: {completion} tokens</span>
        </Stack>
      }
    >
      <span className="select-none">&sum; {total} tokens</span>
    </Tooltip>
  );
};

type TokenCostProps = {
  prompt: number;
  completion: number;
  total: number;
};

export const TokenCostTooltip = ({ prompt, completion, total }: TokenCostProps) => {
  return (
    <Tooltip
      title={
        <Stack direction="column" gap={0} sx={{ fontFamily: "monospace" }}>
          <span>Prompt: {formatCurrency(prompt)}</span>
          <span>Completion: {formatCurrency(completion)}</span>
        </Stack>
      }
    >
      <span className="select-none">&sum; {formatCurrency(total)}</span>
    </Tooltip>
  );
};
