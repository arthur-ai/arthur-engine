import Close from "@mui/icons-material/Close";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select, { type SelectChangeEvent } from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import React, { useEffect, useState } from "react";

import { DEFAULT_TIMEZONE_OPTIONS } from "./constants";
import type { UserSettingsModalProps } from "./types";

import type { ModelProvider } from "@/lib/api-client/api-client";

const METHOD_COLORS: Record<string, string> = {
  GET: "info.main",
  POST: "success.main",
  PUT: "warning.main",
  PATCH: "primary.main",
  DELETE: "error.main",
};

function MethodChip({ method, compact = false }: { method: string; compact?: boolean }) {
  const color = METHOD_COLORS[method.toUpperCase()] ?? "text.secondary";
  return (
    <Chip
      label={method.toUpperCase()}
      size="small"
      sx={{
        bgcolor: color,
        color: "common.white",
        fontWeight: 700,
        fontSize: compact ? "0.55rem" : "0.65rem",
        height: compact ? 16 : 20,
        minWidth: compact ? 40 : 52,
        "& .MuiChip-label": { px: 0.75, py: 0, display: "flex", alignItems: "center" },
      }}
    />
  );
}

const TITLE_ID = "user-settings-dialog-title";
const DESCRIPTION_ID = "user-settings-dialog-description";

export const UserSettingsModal: React.FC<UserSettingsModalProps> = ({
  open,
  onClose,
  initialSettings,
  onSave,
  isLoading = false,
  isSaving = false,
  timezoneOptions = DEFAULT_TIMEZONE_OPTIONS,
  enabledProviders = [],
  availableModelsMap = new Map(),
  availableEndpoints = [],
  chatbotEnabled = false,
  traceRetentionEnabled = false,
  initialTraceRetentionDays,
  allowedTraceRetentionDays = [],
  isLoadingTraceRetention = false,
  title = "Settings",
  saveLabel = "Save",
  savingLabel = "Saving...",
  cancelLabel = "Cancel",
  timezoneLabel = "Timezone",
  timeFormatLabel = "Time format",
}) => {
  const resolvedTimezone = initialSettings?.timezone ?? "UTC";
  const resolvedUse24Hour = initialSettings?.use24Hour ?? false;
  const resolvedEnableChatbot = initialSettings?.enableChatbot ?? true;
  const [timezone, setTimezone] = useState<string>(resolvedTimezone);
  const [use24Hour, setUse24Hour] = useState<boolean>(resolvedUse24Hour);
  const [enableChatbot, setEnableChatbot] = useState<boolean>(resolvedEnableChatbot);
  const [chatbotProvider, setChatbotProvider] = useState<ModelProvider | "">(initialSettings?.chatbotModelProvider ?? "");
  const [chatbotModelName, setChatbotModelName] = useState<string>(initialSettings?.chatbotModelName ?? "");
  const [blacklistEndpoints, setBlacklistEndpoints] = useState<string[]>(initialSettings?.blacklistEndpoints ?? []);
  const [blacklistSearch, setBlacklistSearch] = useState("");
  const retentionDefault = initialTraceRetentionDays ?? allowedTraceRetentionDays[0];
  const [traceRetentionDays, setTraceRetentionDays] = useState<number | undefined>(retentionDefault);

  useEffect(() => {
    if (open) {
      setTimezone(initialSettings?.timezone ?? "UTC");
      setUse24Hour(initialSettings?.use24Hour ?? false);
      setEnableChatbot(initialSettings?.enableChatbot ?? true);
      setChatbotProvider(initialSettings?.chatbotModelProvider ?? "");
      setChatbotModelName(initialSettings?.chatbotModelName ?? "");
      setBlacklistEndpoints(initialSettings?.blacklistEndpoints ?? []);
      setBlacklistSearch("");
      setTraceRetentionDays(initialTraceRetentionDays ?? allowedTraceRetentionDays[0]);
    }
  }, [
    open,
    initialSettings?.timezone,
    initialSettings?.use24Hour,
    initialSettings?.enableChatbot,
    initialSettings?.chatbotModelProvider,
    initialSettings?.chatbotModelName,
    initialSettings?.blacklistEndpoints,
    initialTraceRetentionDays,
    allowedTraceRetentionDays,
  ]);

  const options = timezoneOptions.length > 0 ? timezoneOptions : DEFAULT_TIMEZONE_OPTIONS;
  const value = options.some((opt) => opt.value === timezone) ? timezone : (options[0]?.value ?? "UTC");

  const chatbotModels = chatbotProvider ? (availableModelsMap.get(chatbotProvider) ?? []) : [];

  const handleTimezoneChange = (event: SelectChangeEvent<string>) => {
    setTimezone(event.target.value);
  };

  const handleTimeFormatChange = (event: SelectChangeEvent<string>) => {
    setUse24Hour(event.target.value === "24");
  };

  const handleProviderChange = (event: SelectChangeEvent<string>) => {
    const newProvider = event.target.value as ModelProvider | "";
    setChatbotProvider(newProvider);
    setChatbotModelName("");
  };

  const handleModelNameChange = (event: SelectChangeEvent<string>) => {
    setChatbotModelName(event.target.value);
  };

  const handleSave = () => {
    onSave({
      timezone: value,
      use24Hour,
      traceRetentionDays: traceRetentionDays !== initialTraceRetentionDays ? traceRetentionDays : undefined,
      enableChatbot,
      chatbotModelProvider: chatbotProvider,
      chatbotModelName,
      blacklistEndpoints,
    });
  };

  const handleCancel = () => {
    onClose();
  };

  const saveDisabled = isLoading || isSaving;
  const cancelDisabled = isSaving;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth aria-labelledby={TITLE_ID} aria-describedby={DESCRIPTION_ID}>
      <DialogTitle id={TITLE_ID}>{title}</DialogTitle>
      <DialogContent id={DESCRIPTION_ID}>
        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
        <FormControl fullWidth size="small" disabled={isLoading} sx={{ mt: 1 }}>
          <InputLabel id="user-settings-timezone-label">{timezoneLabel}</InputLabel>
          <Select labelId="user-settings-timezone-label" label={timezoneLabel} value={value} onChange={handleTimezoneChange}>
            {options.map((opt) => (
              <MenuItem key={opt.value} value={opt.value}>
                {opt.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl fullWidth size="small" disabled={isLoading} sx={{ mt: 2 }}>
          <InputLabel id="user-settings-time-format-label">{timeFormatLabel}</InputLabel>
          <Select labelId="user-settings-time-format-label" label={timeFormatLabel} value={use24Hour ? "24" : "12"} onChange={handleTimeFormatChange}>
            <MenuItem value="12">12-hour</MenuItem>
            <MenuItem value="24">24-hour</MenuItem>
          </Select>
        </FormControl>

        {traceRetentionEnabled && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              Application
            </Typography>
            <FormControl fullWidth size="small" disabled={isLoading || isLoadingTraceRetention}>
              <InputLabel id="trace-retention-label">Trace retention (days)</InputLabel>
              <Select
                labelId="trace-retention-label"
                label="Trace retention (days)"
                value={traceRetentionDays ?? ""}
                onChange={(e) => setTraceRetentionDays(e.target.value as number)}
              >
                {allowedTraceRetentionDays.map((days) => (
                  <MenuItem key={days} value={days}>
                    {days} days
                  </MenuItem>
                ))}
              </Select>
              <Typography variant="caption" sx={{ mt: 1, display: "block", color: "text.secondary" }}>
                Traces older than this many days are automatically deleted.
              </Typography>
            </FormControl>
          </>
        )}

        {chatbotEnabled && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              AI Assistant
            </Typography>
            <FormControlLabel
              control={<Switch checked={enableChatbot} onChange={(e) => setEnableChatbot(e.target.checked)} disabled={isLoading} />}
              label="Enable AI Assistant"
            />
            {enableChatbot && enabledProviders.length > 0 && (
              <>
                <FormControl fullWidth size="small" disabled={isLoading} sx={{ mt: 2 }}>
                  <InputLabel id="chatbot-provider-label">Model Provider</InputLabel>
                  <Select labelId="chatbot-provider-label" label="Model Provider" value={chatbotProvider} onChange={handleProviderChange}>
                    {enabledProviders.map((provider) => (
                      <MenuItem key={provider} value={provider}>
                        {provider}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl fullWidth size="small" disabled={isLoading || !chatbotProvider} sx={{ mt: 2 }}>
                  <InputLabel id="chatbot-model-label">Model Name</InputLabel>
                  <Select labelId="chatbot-model-label" label="Model Name" value={chatbotModelName} onChange={handleModelNameChange}>
                    {chatbotModels.map((model: string) => (
                      <MenuItem key={model} value={model}>
                        {model}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </>
            )}
            {availableEndpoints.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                  Blocked Endpoints
                </Typography>
                <Autocomplete
                  options={availableEndpoints.filter((ep) => !blacklistEndpoints.includes(ep))}
                  onChange={(_event, value) => {
                    if (value) {
                      setBlacklistEndpoints([...blacklistEndpoints, value]);
                      setBlacklistSearch("");
                    }
                  }}
                  value={null}
                  inputValue={blacklistSearch}
                  onInputChange={(_event, value, reason) => {
                    if (reason === "selectOption") return;
                    setBlacklistSearch(value);
                  }}
                  disabled={isLoading}
                  getOptionLabel={(option) => option}
                  renderOption={(props, option) => {
                    const method = option.split(" ")[0];
                    return (
                      <li {...props} key={option}>
                        <MethodChip method={method} />
                        <Typography variant="body2" sx={{ ml: 1 }}>
                          {option.substring(method.length + 1)}
                        </Typography>
                      </li>
                    );
                  }}
                  renderInput={(params) => <TextField {...params} placeholder="Search endpoints..." size="small" />}
                  slotProps={{
                    popper: { placement: "bottom-start", modifiers: [{ name: "flip", enabled: false }] },
                    listbox: { sx: { maxHeight: 350 } },
                  }}
                  size="small"
                />
                <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 1 }}>
                  {blacklistEndpoints.map((ep) => {
                    const method = ep.split(" ")[0];
                    const path = ep.split(" - ")[0].substring(method.length + 1);
                    return (
                      <Chip
                        key={ep}
                        label={
                          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                            <MethodChip method={method} compact />
                            <Typography variant="body2">{path}</Typography>
                          </Box>
                        }
                        size="small"
                        onDelete={() => setBlacklistEndpoints(blacklistEndpoints.filter((e) => e !== ep))}
                        deleteIcon={<Close />}
                      />
                    );
                  })}
                </Stack>
              </Box>
            )}
          </>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleCancel} color="inherit" disabled={cancelDisabled}>
          {cancelLabel}
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={saveDisabled}
          startIcon={isSaving ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {isSaving ? savingLabel : saveLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
