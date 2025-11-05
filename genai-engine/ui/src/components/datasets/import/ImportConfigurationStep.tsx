import UploadFileIcon from "@mui/icons-material/UploadFile";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
} from "@mui/material";
import React from "react";

import {
  CSV_IMPORT_MESSAGES,
  DELIMITER_OPTIONS,
  ENCODING_OPTIONS,
  MAX_DATASET_ROWS,
  type CsvParseConfig,
} from "./csvImportConstants";

interface ImportConfigurationStepProps {
  selectedFile: File | null;
  config: CsvParseConfig;
  isAutoDetecting: boolean;
  autoDetected: boolean;
  error: string | null;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onConfigChange: (config: CsvParseConfig) => void;
}

export const ImportConfigurationStep: React.FC<
  ImportConfigurationStepProps
> = ({
  selectedFile,
  config,
  isAutoDetecting,
  autoDetected,
  error,
  onFileChange,
  onConfigChange,
}) => {
  return (
    <>
      <Typography variant="body2" color="text.secondary">
        {CSV_IMPORT_MESSAGES.info.uploadInstructions}
      </Typography>

      <Box
        sx={{
          border: 2,
          borderStyle: "dashed",
          borderColor: "divider",
          borderRadius: 1,
          p: 3,
          textAlign: "center",
          backgroundColor: "background.default",
        }}
      >
        <input
          type="file"
          accept=".csv,.txt"
          onChange={onFileChange}
          style={{ display: "none" }}
          id="csv-upload-input"
          disabled={isAutoDetecting}
        />
        <label htmlFor="csv-upload-input">
          <Button
            variant="outlined"
            component="span"
            startIcon={<UploadFileIcon />}
            disabled={isAutoDetecting}
          >
            {CSV_IMPORT_MESSAGES.labels.chooseFile}
          </Button>
        </label>

        {selectedFile && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2">
              Selected: {selectedFile.name} (
              {(selectedFile.size / 1024).toFixed(1)} KB)
            </Typography>
            {autoDetected && (
              <Chip
                label={CSV_IMPORT_MESSAGES.info.configAutoDetected}
                color="success"
                size="small"
                sx={{
                  mt: 1,
                  backgroundColor: "background.paper",
                  color: "text.primary",
                  border: 1,
                  borderColor: "divider",
                }}
              />
            )}
          </Box>
        )}

        {isAutoDetecting && (
          <Box sx={{ mt: 2 }}>
            <CircularProgress size={24} />
            <Typography variant="body2" sx={{ mt: 1 }}>
              {CSV_IMPORT_MESSAGES.info.autoDetecting}
            </Typography>
          </Box>
        )}
      </Box>

      {selectedFile && !isAutoDetecting && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            {CSV_IMPORT_MESSAGES.labels.parseConfiguration}
          </Typography>

          <FormControl fullWidth size="small">
            <InputLabel>{CSV_IMPORT_MESSAGES.labels.delimiter}</InputLabel>
            <Select
              value={config.delimiter}
              label={CSV_IMPORT_MESSAGES.labels.delimiter}
              onChange={(e) =>
                onConfigChange({ ...config, delimiter: e.target.value })
              }
            >
              {DELIMITER_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              label={CSV_IMPORT_MESSAGES.labels.quoteChar}
              value={config.quoteChar}
              onChange={(e) =>
                onConfigChange({ ...config, quoteChar: e.target.value })
              }
              size="small"
              fullWidth
              inputProps={{ maxLength: 1 }}
            />
            <TextField
              label={CSV_IMPORT_MESSAGES.labels.escapeChar}
              value={config.escapeChar}
              onChange={(e) =>
                onConfigChange({ ...config, escapeChar: e.target.value })
              }
              size="small"
              fullWidth
              inputProps={{ maxLength: 1 }}
            />
          </Box>

          <FormControl fullWidth size="small">
            <InputLabel>{CSV_IMPORT_MESSAGES.labels.encoding}</InputLabel>
            <Select
              value={config.encoding}
              label={CSV_IMPORT_MESSAGES.labels.encoding}
              onChange={(e) =>
                onConfigChange({ ...config, encoding: e.target.value })
              }
            >
              {ENCODING_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Box>
            <FormControlLabel
              control={
                <Checkbox
                  checked={config.header}
                  onChange={(e) =>
                    onConfigChange({ ...config, header: e.target.checked })
                  }
                />
              }
              label={CSV_IMPORT_MESSAGES.labels.firstRowHeaders}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={!!config.skipEmptyLines}
                  onChange={(e) =>
                    onConfigChange({
                      ...config,
                      skipEmptyLines: e.target.checked,
                    })
                  }
                />
              }
              label={CSV_IMPORT_MESSAGES.labels.skipEmptyLines}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={config.trimFields}
                  onChange={(e) =>
                    onConfigChange({
                      ...config,
                      trimFields: e.target.checked,
                    })
                  }
                />
              }
              label={CSV_IMPORT_MESSAGES.labels.trimWhitespace}
            />
          </Box>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      <Typography variant="caption" color="text.secondary">
        {CSV_IMPORT_MESSAGES.info.importNote(MAX_DATASET_ROWS)}
      </Typography>
    </>
  );
};
