import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import React, { SyntheticEvent, useCallback, useEffect, useRef, useState } from "react";

import { usePromptContext } from "../PromptsPlaygroundContext";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { AgenticPromptVersionResponse } from "@/lib/api-client/api-client";

interface VersionSelectorProps {
  promptName: string;
  promptId: string;
  currentVersion?: number | null;
  onVersionSelect: (version: number) => void;
}

const VersionSelector = ({ promptName, promptId, currentVersion, onVersionSelect }: VersionSelectorProps) => {
  const [versions, setVersions] = useState<AgenticPromptVersionResponse[]>([]);
  const isFetchingVersions = useRef<boolean>(false);

  const { state } = usePromptContext();
  const apiClient = useApi();
  const { task } = useTask();
  const taskId = task?.id;

  const fetchVersions = useCallback(async () => {
    if (!promptName || !taskId || !apiClient) {
      return;
    }
    if (isFetchingVersions.current) {
      return;
    }

    // This case usually happens when duplicating a backend prompt
    const backendPrompt = state.backendPrompts.find((bp) => bp.name === promptName);
    if (typeof backendPrompt === "undefined") {
      return;
    }

    isFetchingVersions.current = true;
    try {
      const response = await apiClient.api.getAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGet({
        promptName,
        taskId,
        page_size: 100,
        sort: "desc",
      });
      setVersions(response.data.versions);
    } catch (error) {
      console.error("Failed to fetch prompt versions:", error);
      setVersions([]);
    } finally {
      isFetchingVersions.current = false;
    }
  }, [apiClient, promptName, taskId, state.backendPrompts]);

  const handleAutocompleteChange = (_event: SyntheticEvent<Element, Event>, newValue: AgenticPromptVersionResponse | null) => {
    if (newValue) {
      onVersionSelect(newValue.version);
    }
  };

  // Fetch versions when selected prompt (promptName) changes
  useEffect(() => {
    if (promptName && !isFetchingVersions.current) {
      setVersions([]);
      fetchVersions();
    }
  }, [promptName, fetchVersions, isFetchingVersions]);

  if (versions.length <= 1) {
    return null;
  }
  return (
    <div className="flex-1 min-w-0">
      <Autocomplete<AgenticPromptVersionResponse>
        id={`version-select-${promptId}`}
        options={versions}
        value={versions.find((v) => v.version === currentVersion) || null}
        onChange={handleAutocompleteChange}
        getOptionLabel={(option) => `Version ${option.version}`}
        isOptionEqualToValue={(option, value) => option.version === value?.version}
        disabled={!promptName || isFetchingVersions.current || versions.length === 0}
        loading={isFetchingVersions.current}
        noOptionsText={isFetchingVersions.current ? "Loading versions..." : "No versions available"}
        sx={{ backgroundColor: "white" }}
        renderOption={(props, option) => {
          const { key, ...optionProps } = props;
          return (
            <Box key={key} component="li" {...optionProps}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="body1" color="text.primary">
                  Version {option.version}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {new Date(option.created_at).toLocaleString()}
                </Typography>
              </Box>
            </Box>
          );
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Version"
            variant="outlined"
            size="small"
            sx={{
              backgroundColor: "white",
            }}
          />
        )}
      />
    </div>
  );
};

export default VersionSelector;
