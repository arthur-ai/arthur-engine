import { Box } from "@mui/material";

import adlcFlywheelSrc from "../content/assets/adlc-flywheel.png";

/**
 * Branded ADLC flywheel diagram for the welcome modal — four stages connected
 * in a cycle: Live & Simulated Usage → Identify Failure Modes & Hotspots →
 * Enhance Behavioral Suite & Evals → Experiment & Improve.
 */
export function ADLCFlywheel() {
  return (
    <Box
      sx={{
        display: "inline-flex",
        justifyContent: "center",
        bgcolor: "common.black",
        borderRadius: 2,
        overflow: "hidden",
      }}
    >
      <Box
        component="img"
        src={adlcFlywheelSrc}
        alt="Agent development flywheel: Live and Simulated Usage, Identify Failure Modes and Hotspots, Enhance Behavioral Suite and Evals, Experiment and Improve"
        loading="lazy"
        sx={{
          display: "block",
          width: 240,
          maxWidth: "100%",
          height: "auto",
        }}
      />
    </Box>
  );
}
