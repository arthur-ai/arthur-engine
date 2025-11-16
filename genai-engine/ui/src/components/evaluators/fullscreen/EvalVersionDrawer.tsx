import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useMemo, useState, useCallback } from "react";

import { useEvalVersions } from "../hooks/useEvalVersions";
import type { EvalVersionDrawerProps } from "../types";

import { formatDate } from "@/utils/formatters";

const EvalVersionDrawer = ({ open, onClose, taskId, evalName, selectedVersion, onSelectVersion }: EvalVersionDrawerProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const { versions, isLoading, error } = useEvalVersions(taskId, evalName, {
    sort: sortOrder,
    exclude_deleted: false,
  });

  const sortedAndFilteredVersions = useMemo(() => {
    let filtered = versions;

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (v) =>
          v.version.toString().includes(query) ||
          v.model_name.toLowerCase().includes(query) ||
          v.model_provider.toLowerCase().includes(query) ||
          formatDate(v.created_at).toLowerCase().includes(query)
      );
    }

    // Sort by creation date
    return [...filtered].sort((a, b) => {
      const aTime = new Date(a.created_at).getTime();
      const bTime = new Date(b.created_at).getTime();
      return sortOrder === "asc" ? aTime - bTime : bTime - aTime;
    });
  }, [versions, searchQuery, sortOrder]);

  const autocompleteOptions = useMemo(() => {
    return versions.map((v) => ({
      label: `Version ${v.version} - ${v.model_provider}/${v.model_name} (${formatDate(v.created_at)})`,
      version: v.version,
    }));
  }, [versions]);

  const handleVersionClick = useCallback(
    (version: number) => {
      onSelectVersion(version);
    },
    [onSelectVersion]
  );

  const handleAutocompleteChange = useCallback(
    (_event: unknown, value: { label: string; version: number } | string | null) => {
      if (value && typeof value === "object") {
        onSelectVersion(value.version);
        setSearchQuery("");
      } else if (typeof value === "string") {
        setSearchQuery(value);
      } else {
        setSearchQuery("");
      }
    },
    [onSelectVersion]
  );

  return (
    <Drawer
      variant="permanent"
      anchor="left"
      open={open}
      onClose={onClose}
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
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
          Versions: {evalName}
        </Typography>

        <Autocomplete
          freeSolo
          options={autocompleteOptions}
          getOptionLabel={(option) => (typeof option === "string" ? option : option.label)}
          onChange={handleAutocompleteChange}
          onInputChange={(_event, value) => setSearchQuery(value)}
          inputValue={searchQuery}
          renderInput={(params) => <TextField {...params} label="Search versions" variant="outlined" size="small" sx={{ mb: 2 }} />}
        />

        <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
          <Chip
            label={`Sort: ${sortOrder === "asc" ? "Oldest First" : "Newest First"}`}
            onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
            clickable
            size="small"
          />
        </Box>

        <Divider sx={{ mb: 2 }} />

        {isLoading && (
          <Box sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              Loading versions...
            </Typography>
          </Box>
        )}

        {error && (
          <Box sx={{ p: 2 }}>
            <Typography variant="body2" color="error">
              Error loading versions: {error.message}
            </Typography>
          </Box>
        )}

        {!isLoading && !error && sortedAndFilteredVersions.length === 0 && (
          <Box sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              No versions found
            </Typography>
          </Box>
        )}

        {!isLoading && !error && sortedAndFilteredVersions.length > 0 && (
          <List sx={{ flex: 1, overflow: "auto" }}>
            {sortedAndFilteredVersions.map((version) => {
              const isSelected = selectedVersion === version.version;
              const isDeleted = !!version.deleted_at;

              return (
                <ListItem key={version.version} disablePadding>
                  <ListItemButton
                    selected={isSelected}
                    onClick={() => handleVersionClick(version.version)}
                    sx={{
                      backgroundColor: isSelected ? "action.selected" : "transparent",
                      "&:hover": {
                        backgroundColor: "action.hover",
                      },
                    }}
                  >
                    <ListItemText
                      primary={
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            Version {version.version}
                          </Typography>
                          {isDeleted && <Chip label="Deleted" size="small" color="error" sx={{ height: 18, fontSize: "0.7rem" }} />}
                        </Box>
                      }
                      secondary={
                        <Box component="span" sx={{ mt: 0.5, display: "block" }}>
                          <Typography variant="caption" color="text.secondary" component="span">
                            {version.model_provider} / {version.model_name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" component="span" sx={{ display: "block", mt: 0.5 }}>
                            {formatDate(version.created_at)}
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

export default EvalVersionDrawer;
