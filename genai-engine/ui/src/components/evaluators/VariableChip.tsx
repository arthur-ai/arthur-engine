import Chip, { ChipProps } from "@mui/material/Chip";
import { alpha } from "@mui/material/styles";

interface VariableChipProps extends ChipProps {
  variable: string;
}

export const VariableChip = ({ variable, sx, ...props }: VariableChipProps) => {
  return (
    <Chip
      label={variable}
      size="small"
      sx={[
        (theme) => ({
          height: 20,
          fontSize: "0.7rem",
          fontFamily: "monospace",
          backgroundColor: alpha(theme.palette.primary.main, 0.16),
          color: "primary.main",
          fontWeight: 500,
          cursor: "pointer",
          border: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
          "&:hover": {
            backgroundColor: alpha(theme.palette.primary.main, 0.28),
          },
          "& .MuiChip-label": {
            px: 1,
            py: 0,
            lineHeight: "20px",
          },
        }),
        ...(Array.isArray(sx) ? sx : sx ? [sx] : []),
      ]}
      {...props}
    />
  );
};
