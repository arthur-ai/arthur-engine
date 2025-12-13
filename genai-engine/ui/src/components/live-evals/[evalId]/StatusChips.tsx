import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import PauseCircleOutlineIcon from "@mui/icons-material/PauseCircleOutline";
import PlayCircleOutlineIcon from "@mui/icons-material/PlayCircleOutline";
import RemoveCircleOutlineIcon from "@mui/icons-material/RemoveCircleOutline";
import { Chip } from "@mui/material";

import type { EvaluatedTrace, LiveEvalDetail } from "./types";

// Status chip for the live eval itself (active/inactive)
export const LiveEvalStatusChip = ({ status }: { status: LiveEvalDetail["status"] }) => {
  if (status === "active") {
    return (
      <Chip
        label="Active"
        color="success"
        size="small"
        icon={<PlayCircleOutlineIcon sx={{ fontSize: 16 }} />}
        variant="outlined"
      />
    );
  }
  return (
    <Chip
      label="Inactive"
      color="default"
      size="small"
      icon={<PauseCircleOutlineIcon sx={{ fontSize: 16 }} />}
      variant="outlined"
    />
  );
};

// Result chip for individual trace evaluations (pass/fail/error)
export const ResultChip = ({ result, score }: { result: EvaluatedTrace["result"]; score: number | null }) => {
  const config = {
    pass: {
      label: score !== null ? `Pass (${score.toFixed(2)})` : "Pass",
      color: "success" as const,
      icon: <CheckCircleIcon sx={{ fontSize: 14 }} />,
    },
    fail: {
      label: score !== null ? `Fail (${score.toFixed(2)})` : "Fail",
      color: "error" as const,
      icon: <RemoveCircleOutlineIcon sx={{ fontSize: 14 }} />,
    },
    error: {
      label: "Error",
      color: "warning" as const,
      icon: <ErrorOutlineIcon sx={{ fontSize: 14 }} />,
    },
  };

  const { label, color, icon } = config[result];

  return (
    <Chip
      label={label}
      color={color}
      size="small"
      icon={icon}
      sx={{
        fontWeight: 500,
        "& .MuiChip-icon": { ml: 0.5 },
      }}
    />
  );
};

