import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { Fab, useTheme } from "@mui/material";

export interface ResumeFabProps {
  onClick: () => void;
}

/**
 * Bottom-right floating action button that re-opens a dismissed tour. Styled
 * with the same brand-purple accent as the spotlight ring so the affordance
 * reads consistently against the rest of the tour overlay.
 */
export function ResumeFab({ onClick }: ResumeFabProps) {
  const theme = useTheme();
  return (
    <Fab
      onClick={onClick}
      variant="extended"
      color="secondary"
      aria-label="Resume tour"
      sx={{
        position: "fixed",
        bottom: 20,
        right: 20,
        zIndex: 1450,
        textTransform: "none",
        boxShadow: `0 8px 20px ${theme.palette.secondary.main}55`,
        fontWeight: 600,
      }}
    >
      <HelpOutlineIcon sx={{ mr: 1, fontSize: 18 }} />
      Resume tour
    </Fab>
  );
}
