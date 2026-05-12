import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import { useCallback } from "react";

import { useTransformVersions } from "../hooks/useTransformVersions";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { formatDateInTimezone } from "@/utils/formatters";

interface TransformVersionDrawerProps {
  transformId: string;
  transformName: string;
  selectedVersionId: string | null;
  latestVersionId: string | null;
  onSelectVersion: (versionId: string) => void;
}

const TransformVersionDrawer = ({ transformId, transformName, selectedVersionId, latestVersionId, onSelectVersion }: TransformVersionDrawerProps) => {
  const { timezone, use24Hour } = useDisplaySettings();
  const { data: versions = [], isLoading, error } = useTransformVersions(transformId);

  const handleVersionClick = useCallback(
    (versionId: string) => {
      onSelectVersion(versionId);
    },
    [onSelectVersion]
  );

  return (
    <Drawer
      variant="permanent"
      anchor="left"
      open
      sx={{
        width: 400,
        flexShrink: 0,
        position: "relative",
        "& .MuiDrawer-paper": {
          width: 400,
          boxSizing: "border-box",
          position: "relative",
          height: "100%",
          borderRight: "1px solid",
          borderColor: "divider",
          overflow: "visible",
        },
      }}
    >
      <Box sx={{ p: 2, display: "flex", flexDirection: "column", height: "100%" }}>
        <Typography variant="h6" noWrap sx={{ mb: 2, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis" }}>
          Versions: {transformName}
        </Typography>

        <Divider sx={{ mb: 2 }} />

        {isLoading && (
          <Box sx={{ p: 2, display: "flex", justifyContent: "center" }}>
            <CircularProgress size={24} />
          </Box>
        )}

        {error && (
          <Box sx={{ p: 2 }}>
            <Typography variant="body2" color="error">
              Error loading versions: {error.message}
            </Typography>
          </Box>
        )}

        {!isLoading && !error && versions.length === 0 && (
          <Box sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              No versions found
            </Typography>
          </Box>
        )}

        {!isLoading && !error && versions.length > 0 && (
          <List sx={{ flex: 1, overflow: "auto" }}>
            {versions.map((version) => {
              const isSelected = selectedVersionId === version.id;
              const isLatest = version.id === latestVersionId;

              return (
                <ListItem key={version.id} disablePadding>
                  <ListItemButton
                    selected={isSelected}
                    onClick={() => handleVersionClick(version.id)}
                    sx={{
                      backgroundColor: isSelected ? "action.selected" : "transparent",
                      "&:hover": {
                        backgroundColor: "action.hover",
                      },
                    }}
                  >
                    <ListItemText
                      primary={
                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexWrap: "wrap" }}>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            Version {version.version_number}
                          </Typography>
                          {isLatest && <Chip label="Latest" size="small" color="default" sx={{ height: 18, fontSize: "0.7rem" }} />}
                        </Box>
                      }
                      secondary={
                        <Box component="span" sx={{ mt: 0.5, display: "block" }}>
                          <Typography variant="caption" color="text.secondary" component="span" sx={{ display: "block", mt: 0.25 }}>
                            {formatDateInTimezone(version.created_at, timezone, { hour12: !use24Hour })}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        )}
      </Box>
    </Drawer>
  );
};

export default TransformVersionDrawer;
