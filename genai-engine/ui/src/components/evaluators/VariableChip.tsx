import Chip, { ChipProps } from "@mui/material/Chip";

interface VariableChipProps extends ChipProps {
  variable: string;
}

export const VariableChip = ({ variable, sx, ...props }: VariableChipProps) => {
  return (
    <Chip
      label={variable}
      size="small"
      sx={[
        {
          height: 20,
          fontSize: "0.7rem",
          fontFamily: "monospace",
          backgroundColor: "rgba(180, 190, 165, 0.2)",
          color: "primary.main",
          fontWeight: 400,
          cursor: "pointer",
          "&:hover": {
            backgroundColor: "rgba(180, 190, 165, 0.35)",
          },
          "& .MuiChip-label": {
            px: 1,
            py: 0,
            lineHeight: "20px",
          },
        },
        ...(Array.isArray(sx) ? sx : sx ? [sx] : []),
      ]}
      {...props}
    />
  );
};
