import { Tooltip } from "@mui/material";
import type { MRT_ColumnDef, MRT_RowData } from "material-react-table";
import { createMRTColumnHelper } from "material-react-table";

import type { ColumnDependencies } from "./column-factory-types";

/**
 * Creates an ID column with Chip, Tooltip, and tracking
 */
export function createIdColumn<T extends MRT_RowData>(
  columnHelper: ReturnType<typeof createMRTColumnHelper<T>>,
  accessor: string,
  header: string,
  level: "trace" | "span" | "session" | "user",
  idType: "trace" | "span" | "session" | "user",
  deps: Pick<ColumnDependencies, "Chip" | "onTrack">,
  options?: {
    size?: number;
    emptyValue?: string | null;
    useFullWidth?: boolean;
    includeMonospace?: boolean;
  }
): MRT_ColumnDef<T> {
  const { Chip, onTrack } = deps;
  const { size, emptyValue = "-", useFullWidth = false, includeMonospace = true } = options ?? {};

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return columnHelper.accessor(accessor as any, {
    header,
    ...(size && { size }),
    Cell: ({ cell }) => {
      const label = cell.getValue() as string | null | undefined;

      if (!label) {
        return emptyValue;
      }

      const spanClassName = useFullWidth ? "w-full" : undefined;

      return (
        <Tooltip title={label}>
          <span className={spanClassName}>
            <Chip
              label={label}
              {...(includeMonospace && { sx: { fontFamily: "monospace" } })}
              onCopy={(value) =>
                onTrack("TRACING_ID_COPIED", {
                  level,
                  id_type: idType,
                  id_value: value,
                  source: "table",
                })
              }
            />
          </span>
        </Tooltip>
      );
    },
  }) as MRT_ColumnDef<T>;
}

/**
 * Creates token count and token cost columns
 */
export function createTokenColumns<T extends MRT_RowData>(
  columnHelper: ReturnType<typeof createMRTColumnHelper<T>>,
  deps: Pick<ColumnDependencies, "TokenCountTooltip" | "TokenCostTooltip">
): [MRT_ColumnDef<T>, MRT_ColumnDef<T>] {
  const { TokenCountTooltip, TokenCostTooltip } = deps;

  const tokenCountColumn = columnHelper.display({
    id: "token-count",
    header: "Token Count",
    Cell: ({ cell }) => {
      const row = cell.row.original as {
        total_token_count?: number;
        prompt_token_count?: number;
        completion_token_count?: number;
      };
      const { total_token_count = 0, prompt_token_count = 0, completion_token_count = 0 } = row;

      if (!total_token_count) return "-";

      return <TokenCountTooltip prompt={prompt_token_count ?? 0} completion={completion_token_count ?? 0} total={total_token_count} />;
    },
  }) as MRT_ColumnDef<T>;

  const tokenCostColumn = columnHelper.display({
    id: "token-cost",
    header: "Token Cost",
    Cell: ({ cell }) => {
      const row = cell.row.original as {
        total_token_cost?: number;
        prompt_token_cost?: number;
        completion_token_cost?: number;
      };
      const { total_token_cost = 0, prompt_token_cost = 0, completion_token_cost = 0 } = row;

      if (!total_token_cost) return "-";

      return <TokenCostTooltip prompt={prompt_token_cost ?? 0} completion={completion_token_cost ?? 0} total={total_token_cost} />;
    },
  }) as MRT_ColumnDef<T>;

  return [tokenCountColumn, tokenCostColumn];
}

/**
 * Creates input and output content columns
 */
export function createContentColumns<T extends MRT_RowData>(
  columnHelper: ReturnType<typeof createMRTColumnHelper<T>>,
  deps: Pick<ColumnDependencies, "TraceContentCell">,
  titlePrefix: string,
  options?: {
    includeSpanId?: boolean;
  }
): [MRT_ColumnDef<T>, MRT_ColumnDef<T>] {
  const { TraceContentCell } = deps;
  const { includeSpanId = false } = options ?? {};

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const inputColumn = columnHelper.accessor("input_content" as any, {
    header: "Input Content",
    size: 200,
    Cell: ({ cell, row }) => {
      const rowData = row.original as {
        trace_id?: string | null;
        span_id?: string | null;
      };
      return (
        <span className="w-full">
          <TraceContentCell
            value={cell.getValue()}
            title={`${titlePrefix} Input Content`}
            traceId={rowData.trace_id ?? undefined}
            {...(includeSpanId && { spanId: rowData.span_id ?? undefined })}
          />
        </span>
      );
    },
  }) as MRT_ColumnDef<T>;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const outputColumn = columnHelper.accessor("output_content" as any, {
    header: "Output Content",
    size: 200,
    Cell: ({ cell, row }) => {
      const rowData = row.original as {
        trace_id?: string | null;
        span_id?: string | null;
      };
      return (
        <span className="w-full">
          <TraceContentCell
            value={cell.getValue()}
            title={`${titlePrefix} Output Content`}
            traceId={rowData.trace_id ?? undefined}
            {...(includeSpanId && { spanId: rowData.span_id ?? undefined })}
          />
        </span>
      );
    },
  }) as MRT_ColumnDef<T>;

  return [inputColumn, outputColumn];
}

/**
 * Creates a date column with formatting
 */
export function createDateColumn<T extends MRT_RowData>(
  columnHelper: ReturnType<typeof createMRTColumnHelper<T>>,
  accessor: string,
  header: string,
  deps: Pick<ColumnDependencies, "formatDate">,
  options?: {
    sortingFn?: string;
  }
): MRT_ColumnDef<T> {
  const { formatDate } = deps;
  const { sortingFn } = options ?? {};

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return columnHelper.accessor(accessor as any, {
    header,
    ...(sortingFn && { sortingFn }),
    Cell: ({ cell }) => formatDate(cell.getValue() as string | null | undefined),
  }) as MRT_ColumnDef<T>;
}

/**
 * Creates a count column with unit label
 */
export function createCountColumn<T extends MRT_RowData>(
  columnHelper: ReturnType<typeof createMRTColumnHelper<T>>,
  accessor: string,
  header: string,
  unit: string
): MRT_ColumnDef<T> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return columnHelper.accessor(accessor as any, {
    header,
    Cell: ({ cell }) => `${cell.getValue()} ${unit}`,
  }) as MRT_ColumnDef<T>;
}
