import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import React from "react";

import { useRagConfigVersions } from "@/hooks/rag-search-settings/useRagConfigVersions";
import type { RagSearchSettingConfigurationVersionResponse } from "@/lib/api-client/api-client";

interface RagConfigVersionSelectorProps {
  configId: string | null;
  currentVersion: number | null;
  onVersionSelect: (version: number) => void;
}

export const RagConfigVersionSelector: React.FC<RagConfigVersionSelectorProps> = ({ configId, currentVersion, onVersionSelect }) => {
  const { data, isLoading } = useRagConfigVersions(configId, {
    page_size: 100,
    sort: "desc",
  });

  const versions = data?.versions ?? [];

  const handleChange = (_event: React.SyntheticEvent, newValue: RagSearchSettingConfigurationVersionResponse | null) => {
    if (newValue) {
      onVersionSelect(newValue.version_number);
    }
  };

  // Disable if no config selected or less than 2 versions
  const isDisabled = !configId || isLoading || versions.length < 2;

  return (
    <Autocomplete
      options={versions}
      value={versions.find((v) => v.version_number === currentVersion) || null}
      onChange={handleChange}
      getOptionLabel={(option) => `Version ${option.version_number}`}
      isOptionEqualToValue={(option, value) => option.version_number === value?.version_number}
      disabled={isDisabled}
      loading={isLoading}
      renderOption={(props, option) => {
        const { key, ...optionProps } = props;
        return (
          <Box key={key} component="li" {...optionProps}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="body1">Version {option.version_number}</Typography>
              <Typography variant="body2" color="text.secondary">
                {new Date(option.created_at).toLocaleString()}
              </Typography>
              {option.tags && option.tags.length > 0 && (
                <Box sx={{ display: "flex", gap: 0.5, mt: 0.5 }}>
                  {option.tags.map((tag) => (
                    <Chip key={tag} label={tag} size="small" variant="outlined" />
                  ))}
                </Box>
              )}
            </Box>
          </Box>
        );
      }}
      renderInput={(params) => <TextField {...params} label="Version" variant="outlined" size="small" sx={{ backgroundColor: "white" }} />}
      sx={{ flex: 1, minWidth: 0 }}
    />
  );
};
