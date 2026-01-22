import PauseCircleOutlineIcon from "@mui/icons-material/PauseCircleOutline";
import PlayCircleOutlineIcon from "@mui/icons-material/PlayCircleOutline";
import { Chip } from "@mui/material";

import type { LiveEvalDetail } from "./types";

// Status chip for the live eval itself (active/inactive)
export const LiveEvalStatusChip = ({ status }: { status: LiveEvalDetail["status"] }) => {
  if (status === "active") {
    return <Chip label="Active" color="success" size="small" icon={<PlayCircleOutlineIcon sx={{ fontSize: 16 }} />} variant="outlined" />;
  }
  return <Chip label="Inactive" color="default" size="small" icon={<PauseCircleOutlineIcon sx={{ fontSize: 16 }} />} variant="outlined" />;
};
