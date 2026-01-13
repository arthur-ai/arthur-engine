import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import HistoryIcon from "@mui/icons-material/History";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import RefreshIcon from "@mui/icons-material/Refresh";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import LinearProgress from "@mui/material/LinearProgress";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getStatusChipSx } from "./utils/statusChipStyles";

import { useRagNotebookHistoryWithPolling } from "@/hooks/useRagNotebooks";
import type { RagExperimentSummary } from "@/lib/api-client/api-client";

interface RagExperimentHistorySidebarProps {
  open: boolean;
  onClose: () => void;
  notebookId: string | null;
  onExperimentSelect?: (experimentId: string) => void;
}

const DRAWER_WIDTH = 360;

/**
 * Format relative time (e.g., "2 hours ago")
 */
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

/**
 * Experiment item component with expandable details
 */
interface ExperimentItemProps {
  experiment: RagExperimentSummary;
  isExpanded: boolean;
  onToggle: () => void;
  onNavigate: () => void;
}

const ExperimentItem: React.FC<ExperimentItemProps> = ({ experiment, isExpanded, onToggle, onNavigate }) => {
  const isRunning = experiment.status === "running" || experiment.status === "queued";
  const progress = experiment.total_rows > 0 ? Math.round((experiment.completed_rows / experiment.total_rows) * 100) : 0;

  return (
    <>
      <ListItem
        disablePadding
        secondaryAction={
          <IconButton size="small" onClick={onToggle}>
            <ExpandMoreIcon
              sx={{
                transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 0.2s",
              }}
            />
          </IconButton>
        }
      >
        <ListItemButton onClick={onToggle} sx={{ pr: 6 }}>
          <ListItemText
            primary={
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 500, flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>
                  {experiment.name}
                </Typography>
                <Chip label={experiment.status} size="small" sx={{ ...getStatusChipSx(experiment.status), fontSize: "0.7rem", height: 20 }} />
              </Box>
            }
            secondary={
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5 }}>
                <Typography variant="caption" color="text.secondary">
                  {formatRelativeTime(experiment.created_at)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  •
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {experiment.rag_configs?.length || 0} configs
                </Typography>
              </Box>
            }
          />
        </ListItemButton>
      </ListItem>

      <Collapse in={isExpanded} timeout="auto" unmountOnExit>
        <Box sx={{ px: 2, pb: 2, backgroundColor: "grey.50" }}>
          {/* Progress bar for running experiments */}
          {isRunning && (
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Progress
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {experiment.completed_rows} / {experiment.total_rows} rows
                </Typography>
              </Box>
              <LinearProgress variant="determinate" value={progress} sx={{ height: 6, borderRadius: 3 }} />
            </Box>
          )}

          {/* Experiment details */}
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, mb: 2 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Dataset
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {experiment.dataset_name} v{experiment.dataset_version}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Total Rows
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {experiment.total_rows}
              </Typography>
            </Box>
            {experiment.total_cost && (
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Total Cost
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  ${experiment.total_cost}
                </Typography>
              </Box>
            )}
          </Box>

          {/* RAG Configs */}
          {experiment.rag_configs && experiment.rag_configs.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
                RAG Configurations
              </Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                {experiment.rag_configs.map((config, index) => (
                  <Chip
                    key={index}
                    label={config.type === "saved" ? `Saved v${config.version}` : "Unsaved"}
                    size="small"
                    variant="outlined"
                    sx={{ fontSize: "0.7rem", height: 20 }}
                  />
                ))}
              </Box>
            </Box>
          )}

          {/* View details button */}
          <Button variant="outlined" size="small" fullWidth startIcon={<OpenInNewIcon />} onClick={onNavigate}>
            View Details
          </Button>
        </Box>
      </Collapse>
      <Divider />
    </>
  );
};

export const RagExperimentHistorySidebar: React.FC<RagExperimentHistorySidebarProps> = ({ open, onClose, notebookId, onExperimentSelect }) => {
  const navigate = useNavigate();
  const { id: taskId } = useParams<{ id: string }>();
  const { experiments, hasRunningExperiments, isLoading, refetch } = useRagNotebookHistoryWithPolling(notebookId ?? undefined);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleToggleExpand = (experimentId: string) => {
    setExpandedId((prev) => (prev === experimentId ? null : experimentId));
  };

  const handleNavigateToExperiment = (experimentId: string) => {
    if (taskId) {
      navigate(`/tasks/${taskId}/rag-experiments/${experimentId}`);
    }
    if (onExperimentSelect) {
      onExperimentSelect(experimentId);
    }
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      sx={{
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          boxSizing: "border-box",
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          p: 2,
          borderBottom: 1,
          borderColor: "divider",
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <HistoryIcon color="primary" />
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Experiment History
          </Typography>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <Tooltip title="Refresh">
            <IconButton size="small" onClick={() => refetch()} disabled={isLoading}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <IconButton size="small" onClick={onClose}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>

      {/* Content */}
      {!notebookId ? (
        <Box sx={{ p: 3, textAlign: "center" }}>
          <Typography variant="body2" color="text.secondary">
            Save your notebook to track experiment history.
          </Typography>
        </Box>
      ) : isLoading ? (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress />
        </Box>
      ) : experiments.length === 0 ? (
        <Box sx={{ p: 3, textAlign: "center" }}>
          <Typography variant="body1" sx={{ mb: 1 }}>
            No experiments yet
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Click "Run Experiment" to create your first experiment from this notebook.
          </Typography>
        </Box>
      ) : (
        <List disablePadding sx={{ overflow: "auto", flex: 1 }}>
          {experiments.map((experiment) => (
            <ExperimentItem
              key={experiment.id}
              experiment={experiment}
              isExpanded={expandedId === experiment.id}
              onToggle={() => handleToggleExpand(experiment.id)}
              onNavigate={() => handleNavigateToExperiment(experiment.id)}
            />
          ))}
        </List>
      )}

      {/* Running indicator */}
      {hasRunningExperiments && (
        <Box
          sx={{
            p: 2,
            borderTop: 1,
            borderColor: "divider",
            backgroundColor: "primary.50",
            display: "flex",
            alignItems: "center",
            gap: 1,
          }}
        >
          <CircularProgress size={16} />
          <Typography variant="caption" color="primary.main">
            Experiment in progress...
          </Typography>
        </Box>
      )}
    </Drawer>
  );
};

export default RagExperimentHistorySidebar;
