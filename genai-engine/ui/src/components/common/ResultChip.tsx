import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import RemoveCircleOutlineIcon from "@mui/icons-material/RemoveCircleOutline";
import { Chip } from "@mui/material";

type Props = {
  result: "pass" | "fail" | "error";
  score: number | null;
};

export const ResultChip = ({ result, score }: Props) => {
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
