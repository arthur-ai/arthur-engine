import { MAX_DATASET_ROWS } from "@/constants/datasetConstants";

export interface CsvParseConfig {
  delimiter: string;
  quoteChar: string;
  escapeChar: string;
  encoding: string;
  header: boolean;
  skipEmptyLines: boolean | "greedy";
  trimFields: boolean;
}

export interface ParsedPreviewData {
  columns: string[];
  rows: Record<string, string>[];
  totalRows: number;
  errors: Papa.ParseError[];
  warnings: string[];
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export const DEFAULT_CONFIG: CsvParseConfig = {
  delimiter: ",",
  quoteChar: '"',
  escapeChar: '"',
  encoding: "UTF-8",
  header: true,
  skipEmptyLines: true,
  trimFields: true,
};

export const DELIMITER_OPTIONS = [
  { value: ",", label: "Comma (,)" },
  { value: ";", label: "Semicolon (;)" },
  { value: "\t", label: "Tab" },
  { value: "|", label: "Pipe (|)" },
] as const;

export const ENCODING_OPTIONS = [
  { value: "UTF-8", label: "UTF-8" },
  { value: "ISO-8859-1", label: "ISO-8859-1" },
  { value: "Windows-1252", label: "Windows-1252" },
] as const;

export const CSV_IMPORT_MESSAGES = {
  errors: {
    autoDetectFailed: "Failed to auto-detect configuration",
    noColumns: "No columns detected in CSV file",
    noRows: "No data rows found in CSV file",
    emptyHeaders: "Some column headers are empty",
    datasetAtCapacity: (maxRows: number) =>
      `Dataset is already at maximum capacity (${maxRows} rows)`,
    parseFailed: (message: string) => `Failed to parse CSV: ${message}`,
    importFailed: (message: string) => `Failed to import CSV: ${message}`,
    parseErrors: (messages: string) => `Parse errors: ${messages}`,
  },
  warnings: {
    raggedRows: (count: number) =>
      `${count} rows have inconsistent column counts`,
    emptyColumns: (count: number) => `${count} columns appear to be empty`,
    rowTruncation: (csvRows: number, available: number, maxRows: number) =>
      `CSV has ${csvRows} rows, but only ${available} can be imported (dataset limit: ${maxRows} total rows)`,
    singleColumn:
      "All data appears in one column. Check if delimiter is correct.",
  },
  info: {
    configAutoDetected: "Configuration auto-detected",
    autoDetecting: "Auto-detecting configuration...",
    processing: "Processing...",
    importing: "Importing...",
    uploadInstructions: "Upload a CSV file and configure parsing options.",
    importNote: (maxRows: number) =>
      `New columns will be added to existing columns. Rows will be appended to existing data. Maximum total rows: ${maxRows}.`,
    previewDescription: (shown: number, total: number) =>
      `Showing first ${shown} of ${total} rows`,
  },
  labels: {
    configureTitle: "Configure CSV Import",
    previewTitle: "Preview & Confirm Import",
    parseConfiguration: "Parse Configuration",
    importSummary: "Import Summary",
    dataPreview: "Data Preview",
    chooseFile: "Choose CSV File",
    columns: "Columns",
    totalRows: "Total Rows",
    willImport: "Will Import",
    delimiter: "Delimiter",
    quoteChar: "Quote Character",
    escapeChar: "Escape Character",
    encoding: "Encoding",
    firstRowHeaders: "First row contains headers",
    skipEmptyLines: "Skip empty lines",
    trimWhitespace: "Trim whitespace from fields",
    next: "Next",
    back: "Back",
    cancel: "Cancel",
    import: "Import",
  },
} as const;

export const PREVIEW_ROW_LIMIT = 10;
export const PARSE_PREVIEW_LIMIT = 100;
export const AUTO_DETECT_PREVIEW_LIMIT = 100;
export const RAGGED_ROW_WARNING_THRESHOLD = 5;

export { MAX_DATASET_ROWS };
