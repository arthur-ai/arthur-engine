import Papa from "papaparse";

import {
  AUTO_DETECT_PREVIEW_LIMIT,
  CSV_IMPORT_MESSAGES,
  MAX_DATASET_ROWS,
  PARSE_PREVIEW_LIMIT,
  RAGGED_ROW_WARNING_THRESHOLD,
  type CsvParseConfig,
  type ParsedPreviewData,
  type ValidationResult,
} from "./csvImportConstants";

interface DelimiterScore {
  delimiter: string;
  score: number;
}

export async function autoDetectDelimiter(file: File): Promise<string> {
  const delimiters = [",", ";", "\t", "|"];
  const scores: DelimiterScore[] = [];

  for (const delimiter of delimiters) {
    const score = await new Promise<number>((resolve) => {
      Papa.parse(file, {
        delimiter,
        preview: AUTO_DETECT_PREVIEW_LIMIT,
        skipEmptyLines: true,
        complete: (results) => {
          if (results.data.length === 0) {
            resolve(-1);
            return;
          }

          const rowLengths = results.data.map((row) => (row as string[]).length);
          const avgLength =
            rowLengths.reduce((a, b) => a + b, 0) / rowLengths.length;
          const variance =
            rowLengths.reduce(
              (sum, len) => sum + Math.pow(len - avgLength, 2),
              0
            ) / rowLengths.length;
          const stdDev = Math.sqrt(variance);

          // Score: prefer more columns with less variance
          const calculatedScore = avgLength > 1 ? avgLength / (stdDev + 1) : -1;
          resolve(calculatedScore);
        },
        error: () => resolve(-1),
      });
    });

    scores.push({ delimiter, score });
  }

  const best = scores.reduce((prev, current) =>
    current.score > prev.score ? current : prev
  );

  return best.score > 0 ? best.delimiter : ",";
}

export function validateParseResults(
  columns: string[],
  rows: Record<string, string>[],
  parseErrors: Papa.ParseError[],
  config: CsvParseConfig,
  currentRowCount: number
): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check for critical parse errors
  if (parseErrors.length > 0) {
    const criticalErrors = parseErrors.filter(
      (e) => e.type === "Delimiter" || e.type === "Quotes"
    );
    if (criticalErrors.length > 0) {
      errors.push(
        CSV_IMPORT_MESSAGES.errors.parseErrors(
          criticalErrors.map((e) => e.message).join(", ")
        )
      );
    }
  }

  // Check for columns
  if (columns.length === 0 && config.header) {
    errors.push(CSV_IMPORT_MESSAGES.errors.noColumns);
  }

  // Check for rows
  if (rows.length === 0) {
    errors.push(CSV_IMPORT_MESSAGES.errors.noRows);
  }

  // Check for empty headers
  if (config.header && columns.some((col) => !col || col.trim() === "")) {
    errors.push(CSV_IMPORT_MESSAGES.errors.emptyHeaders);
  }

  // Check for ragged rows (inconsistent column counts)
  if (rows.length > 0 && columns.length > 0) {
    const expectedCols = columns.length;
    const raggedRowCount = rows.filter(
      (row) => Object.keys(row).length !== expectedCols
    ).length;

    if (raggedRowCount > RAGGED_ROW_WARNING_THRESHOLD) {
      warnings.push(CSV_IMPORT_MESSAGES.warnings.raggedRows(raggedRowCount));
    }
  }

  // Check for empty columns
  if (columns.length > 0 && rows.length > 0) {
    const emptyColCount = columns.filter((col) =>
      rows.every((row) => !row[col] || row[col].trim() === "")
    ).length;

    if (emptyColCount > 0) {
      warnings.push(CSV_IMPORT_MESSAGES.warnings.emptyColumns(emptyColCount));
    }
  }

  // Check dataset capacity
  const availableRows = MAX_DATASET_ROWS - currentRowCount;
  if (availableRows <= 0) {
    errors.push(
      CSV_IMPORT_MESSAGES.errors.datasetAtCapacity(MAX_DATASET_ROWS)
    );
  } else if (rows.length > availableRows) {
    warnings.push(
      CSV_IMPORT_MESSAGES.warnings.rowTruncation(
        rows.length,
        availableRows,
        MAX_DATASET_ROWS
      )
    );
  }

  // Check if all data is in one column (likely wrong delimiter)
  if (columns.length === 1 && rows.length > 0) {
    warnings.push(CSV_IMPORT_MESSAGES.warnings.singleColumn);
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
}

export function parseCSVPreview(
  file: File,
  config: CsvParseConfig,
  currentRowCount: number,
  onSuccess: (data: ParsedPreviewData, validation: ValidationResult) => void,
  onError: (error: string) => void
): void {
  Papa.parse(file, {
    delimiter: config.delimiter,
    quoteChar: config.quoteChar,
    escapeChar: config.escapeChar,
    header: config.header,
    skipEmptyLines: config.skipEmptyLines,
    preview: PARSE_PREVIEW_LIMIT,
    transformHeader: config.trimFields ? (header) => header.trim() : undefined,
    transform: config.trimFields ? (value) => value.trim() : undefined,
    complete: (results) => {
      const columns = config.header ? results.meta.fields || [] : [];
      const rows = results.data as Record<string, string>[];

      const validation = validateParseResults(
        columns,
        rows,
        results.errors,
        config,
        currentRowCount
      );

      const previewData: ParsedPreviewData = {
        columns,
        rows: rows.slice(0, 10),
        totalRows: rows.length,
        errors: results.errors,
        warnings: validation.warnings,
      };

      onSuccess(previewData, validation);
    },
    error: (err) => {
      onError(CSV_IMPORT_MESSAGES.errors.parseFailed(err.message));
    },
  });
}

export function parseCSVFull(
  file: File,
  config: CsvParseConfig,
  currentRowCount: number,
  onSuccess: (columns: string[], rows: Record<string, string>[]) => void,
  onError: (error: string) => void
): void {
  Papa.parse(file, {
    delimiter: config.delimiter,
    quoteChar: config.quoteChar,
    escapeChar: config.escapeChar,
    header: config.header,
    skipEmptyLines: config.skipEmptyLines,
    transformHeader: config.trimFields ? (header) => header.trim() : undefined,
    transform: config.trimFields ? (value) => value.trim() : undefined,
    complete: (results) => {
      const columns = results.meta.fields || [];
      const rows = results.data as Record<string, string>[];
      const maxRowsToImport = MAX_DATASET_ROWS - currentRowCount;
      const rowsToImport = rows.slice(0, maxRowsToImport);

      onSuccess(columns, rowsToImport);
    },
    error: (err) => {
      onError(CSV_IMPORT_MESSAGES.errors.importFailed(err.message));
    },
  });
}

