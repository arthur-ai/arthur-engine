import React, { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select, { type SelectChangeEvent } from "@mui/material/Select";

import { DEFAULT_TIMEZONE_OPTIONS } from "./constants";
import type { UserSettingsModalProps } from "./types";

const TITLE_ID = "user-settings-dialog-title";
const DESCRIPTION_ID = "user-settings-dialog-description";

const getDefaultTimezone = (): string => {
  if (typeof Intl !== "undefined" && typeof Intl.DateTimeFormat !== "undefined") {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch {
      return "UTC";
    }
  }
  return "UTC";
};

export const UserSettingsModal: React.FC<UserSettingsModalProps> = ({
  open,
  onClose,
  initialSettings,
  onSave,
  isLoading = false,
  isSaving = false,
  timezoneOptions = DEFAULT_TIMEZONE_OPTIONS,
  title = "Settings",
  saveLabel = "Save",
  savingLabel = "Saving...",
  cancelLabel = "Cancel",
  timezoneLabel = "Timezone",
  timeFormatLabel = "Time format",
}) => {
  const resolvedTimezone = initialSettings?.timezone ?? getDefaultTimezone();
  const resolvedUse24Hour = initialSettings?.use24Hour ?? true;
  const [timezone, setTimezone] = useState<string>(resolvedTimezone);
  const [use24Hour, setUse24Hour] = useState<boolean>(resolvedUse24Hour);

  useEffect(() => {
    if (open) {
      setTimezone(initialSettings?.timezone ?? getDefaultTimezone());
      setUse24Hour(initialSettings?.use24Hour ?? true);
    }
  }, [open, initialSettings?.timezone, initialSettings?.use24Hour]);

  const options = timezoneOptions.length > 0 ? timezoneOptions : DEFAULT_TIMEZONE_OPTIONS;
  const value = options.some((opt) => opt.value === timezone) ? timezone : (options[0]?.value ?? "UTC");

  const handleTimezoneChange = (event: SelectChangeEvent<string>) => {
    setTimezone(event.target.value);
  };

  const handleTimeFormatChange = (event: SelectChangeEvent<string>) => {
    setUse24Hour(event.target.value === "24");
  };

  const handleSave = () => {
    onSave({ timezone: value, use24Hour });
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
          <Select
            labelId="user-settings-time-format-label"
            label={timeFormatLabel}
            value={use24Hour ? "24" : "12"}
            onChange={handleTimeFormatChange}
          >
            <MenuItem value="12">12-hour</MenuItem>
            <MenuItem value="24">24-hour</MenuItem>
          </Select>
        </FormControl>
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
