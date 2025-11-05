import {
  Alert,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import React from "react";

import {
  CSV_IMPORT_MESSAGES,
  MAX_DATASET_ROWS,
  type ParsedPreviewData,
  type ValidationResult,
} from "./csvImportConstants";

interface ImportPreviewStepProps {
  previewData: ParsedPreviewData;
  validation: ValidationResult;
  currentRowCount: number;
  error: string | null;
}

export const ImportPreviewStep: React.FC<ImportPreviewStepProps> = ({
  previewData,
  validation,
  currentRowCount,
  error,
}) => {
  const rowsToImport = Math.min(
    previewData.totalRows,
    MAX_DATASET_ROWS - currentRowCount
  );

  return (
    <>
      <Paper sx={{ p: 2, backgroundColor: "background.default" }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          {CSV_IMPORT_MESSAGES.labels.importSummary}
        </Typography>
        <Box sx={{ display: "flex", gap: 3 }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              {CSV_IMPORT_MESSAGES.labels.columns}
            </Typography>
            <Typography variant="h6">{previewData.columns.length}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              {CSV_IMPORT_MESSAGES.labels.totalRows}
            </Typography>
            <Typography variant="h6">{previewData.totalRows}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              {CSV_IMPORT_MESSAGES.labels.willImport}
            </Typography>
            <Typography variant="h6">{rowsToImport}</Typography>
          </Box>
        </Box>
      </Paper>

      {validation.warnings.length > 0 && (
        <Alert severity="warning">
          {validation.warnings.map((warning, idx) => (
            <div key={idx}>{warning}</div>
          ))}
        </Alert>
      )}

      <Box>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          {CSV_IMPORT_MESSAGES.labels.dataPreview}
        </Typography>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ mb: 1, display: "block" }}
        >
          {CSV_IMPORT_MESSAGES.info.previewDescription(
            previewData.rows.length,
            previewData.totalRows
          )}
        </Typography>
        <TableContainer
          component={Paper}
          sx={{ maxHeight: 300, overflow: "auto" }}
        >
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                {previewData.columns.map((col, idx) => (
                  <TableCell
                    key={idx}
                    sx={{
                      fontWeight: 600,
                      backgroundColor: "background.paper",
                    }}
                  >
                    {col}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {previewData.rows.map((row, rowIdx) => (
                <TableRow key={rowIdx}>
                  {previewData.columns.map((col, colIdx) => (
                    <TableCell key={colIdx}>{row[col] ?? ""}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}
    </>
  );
};
