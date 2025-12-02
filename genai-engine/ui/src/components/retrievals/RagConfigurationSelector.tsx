import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import React from "react";

import { useRagSearchSettings } from "@/hooks/rag-search-settings/useRagSearchSettings";
import { useTask } from "@/hooks/useTask";
import type { RagSearchSettingConfigurationResponse } from "@/lib/api-client/api-client";

interface RagConfigurationSelectorProps {
  currentConfigId: string | null;
  onConfigSelect: (config: RagSearchSettingConfigurationResponse | null) => void;
}

export const RagConfigurationSelector: React.FC<RagConfigurationSelectorProps> = ({ currentConfigId, onConfigSelect }) => {
  const { task } = useTask();

  const { data } = useRagSearchSettings(task?.id, { page_size: 100 });
  const configs = data?.rag_provider_setting_configurations ?? [];

  const handleChange = (_event: React.SyntheticEvent, newValue: RagSearchSettingConfigurationResponse | null) => {
    onConfigSelect(newValue);
  };

  return (
    <Autocomplete
      options={configs}
      value={configs.find((c) => c.id === currentConfigId) || null}
      onChange={handleChange}
      getOptionLabel={(option) => option.name}
      isOptionEqualToValue={(option, value) => option.id === value?.id}
      disabled={configs.length === 0}
      noOptionsText="No saved configurations"
      renderOption={(props, option) => {
        const { key, ...optionProps } = props;
        return (
          <Box key={key} component="li" {...optionProps} sx={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
            <Typography variant="body1">{option.name}</Typography>
            <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
              {option.all_possible_tags?.slice(0, 2).map((tag) => (
                <Chip key={tag} label={tag} size="small" variant="outlined" />
              ))}
            </Box>
          </Box>
        );
      }}
      renderInput={(params) => (
        <TextField {...params} label="Saved Configuration" variant="outlined" size="small" sx={{ backgroundColor: "white" }} />
      )}
      sx={{ flex: 1, minWidth: 0 }}
    />
  );
};
