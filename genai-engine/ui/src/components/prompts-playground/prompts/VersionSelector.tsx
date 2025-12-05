import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { SyntheticEvent } from "react";

import { useBackendPromptVersions } from "../hooks/useBackendPromptVersions";

import { AgenticPromptVersionResponse } from "@/lib/api-client/api-client";

interface VersionSelectorProps {
  promptName: string;
  promptId: string;
  currentVersion?: number | null;
  isDirty?: boolean;
  onVersionSelect: (version: number) => void;
}

const VersionSelector = ({ promptName, promptId, currentVersion, isDirty, onVersionSelect }: VersionSelectorProps) => {
  const versions = useBackendPromptVersions(promptName);

  const handleAutocompleteChange = (_event: SyntheticEvent<Element, Event>, newValue: AgenticPromptVersionResponse | null) => {
    if (newValue) {
      onVersionSelect(newValue.version);
    }
  };

  if (!versions.data?.versions?.length) {
    return null;
  }

  const versionLabel = currentVersion ? `${currentVersion}${isDirty ? "*" : ""}` : "";
  const tooltipText = isDirty && currentVersion ? `Modified from version ${currentVersion} - unsaved changes` : "";

  return (
    <div className="flex-1 min-w-0">
      <Tooltip title={tooltipText} arrow placement="top" disableHoverListener={!isDirty}>
        <Autocomplete<AgenticPromptVersionResponse>
          id={`version-select-${promptId}`}
          options={versions.data?.versions ?? []}
          value={versions.data?.versions.find((v) => v.version === currentVersion) || null}
          onChange={handleAutocompleteChange}
          getOptionLabel={(option) => `${option.version}${isDirty ? "*" : ""}`}
          isOptionEqualToValue={(option, value) => option.version === value?.version}
          disabled={!promptName || versions.isLoading || versions.data?.versions.length === 0}
          loading={versions.isLoading}
          noOptionsText={versions.isLoading ? "Loading versions..." : "No versions available"}
          sx={{
            backgroundColor: "white",
            "& .MuiOutlinedInput-root": {
              "& fieldset": {
                borderColor: isDirty ? "#f97316" : undefined, // Orange border when dirty
                borderWidth: isDirty ? "2px" : undefined,
              },
              "&:hover fieldset": {
                borderColor: isDirty ? "#ea580c" : undefined, // Darker orange on hover
              },
              "&.Mui-focused fieldset": {
                borderColor: isDirty ? "#f97316" : undefined,
              },
            },
          }}
          renderOption={(props, option) => {
            const { key, ...optionProps } = props;
            return (
              <Box key={key} component="li" {...optionProps}>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="body1" color="text.primary">
                    {option.version}
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
      </Tooltip>
    </div>
  );
};

export default VersionSelector;
