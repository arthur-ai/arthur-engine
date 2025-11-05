import { Chip } from "@mui/material";

type Props = {
  input: number;
  output: number;
  total: number;
};

export const TokenCountWidget = ({ input, output, total }: Props) => {
  return (
    <Chip
      variant="outlined"
      size="small"
      label={
        <span className="text-inherit">
          {input} input → {output} output (&sum; {total} total)
        </span>
      }
    />
  );
};
