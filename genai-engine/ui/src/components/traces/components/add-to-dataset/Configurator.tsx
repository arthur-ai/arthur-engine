import { Alert, Autocomplete, Badge, Button, Skeleton, TextField, Tooltip, Typography } from "@mui/material";
import { Stack } from "@mui/material";
import { useField } from "@tanstack/react-form";
import { useEffect, useRef } from "react";
import CircleNotificationsOutlinedIcon from "@mui/icons-material/CircleNotificationsOutlined";
import PriorityHighRoundedIcon from "@mui/icons-material/PriorityHighRounded";
import AddIcon from "@mui/icons-material/Add";

import { withForm } from "../filtering/hooks/form";

import { addToDatasetFormOptions } from "./form/shared";
import { SpanSelector } from "./SpanSelector";

import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";
import { DatasetResponse, NestedSpanWithMetricsResponse } from "@/lib/api-client/api-client";
import { MAX_DATASET_ROWS } from "@/constants/datasetConstants";
import { Link as RouterLink } from "react-router-dom";
import { Link } from "@mui/material";
import { useTask } from "@/hooks/useTask";

export const Configurator = withForm({
  ...addToDatasetFormOptions,
  props: {} as {
    dataset: DatasetResponse;
    spans: NestedSpanWithMetricsResponse[];
    onAddColumn: () => void;
  },
  render: function Render({ form, dataset, spans, onAddColumn }) {
    const { task } = useTask();
    const ref = useRef<HTMLDivElement>(null);
    const { version, isLoading } = useDatasetVersionData(dataset.id, dataset.latest_version_number!, 0, 1);

    useEffect(() => {
      if (!version) return;

      form.setFieldValue(
        "columns",
        version.column_names.map((columnName) => ({
          name: columnName,
          value: "",
          path: "",
        }))
      );
    }, [form, version]);

    const field = useField({ form, name: "columns" as const });

    if (isLoading)
      return (
        <div className="grid grid-cols-[1fr_2fr] gap-2">
          <Skeleton variant="rectangular" height={32} />
          <Skeleton variant="rectangular" height={124} />
        </div>
      );

    const canAddRow = (version?.total_count ?? 0) < MAX_DATASET_ROWS;

    if (!canAddRow) {
      return (
        <Alert severity="warning">
          Maximum row limit reached for this dataset.{" "}
          <Link component={RouterLink} to={`/tasks/${task?.id}/datasets/${dataset.id}`} prefetch="intent">
            View dataset
          </Link>
          .
        </Alert>
      );
    }

    return (
      <Stack direction="column" gap={2}>
        <div className="grid grid-cols-[1fr_2fr] gap-2" ref={ref}>
          {field.state.value.map((column, index) => (
            <form.Field mode="array" name={`columns[${index}].value` as const} key={column.name}>
              {(field) => (
                <>
                  <div className="grid grid-cols-subgrid col-span-2">
                    <Stack alignItems="flex-start" gap={1}>
                      <Stack direction="row" alignItems="center" gap={1}>
                        <Typography variant="body2" fontWeight="medium">
                          {column.name}
                        </Typography>
                        {column.matchCount !== undefined && column.matchCount === 0 && (
                          <Tooltip title="0 items found">
                            <PriorityHighRoundedIcon fontSize="small" color="error" />
                          </Tooltip>
                        )}
                        {column.matchCount && column.matchCount > 1 && (
                          <Tooltip title={`${column.matchCount} matching spans found`}>
                            <Badge badgeContent={column.matchCount} color="warning">
                              <CircleNotificationsOutlinedIcon fontSize="small" color="warning" />
                            </Badge>
                          </Tooltip>
                        )}
                      </Stack>
                      {column.matchCount && column.matchCount > 1 && column.allMatches ? (
                        <Autocomplete
                          size="small"
                          options={column.allMatches}
                          value={column.allMatches.find((m) => m.span_id === column.selectedSpanId) || column.allMatches[0]}
                          sx={{ width: "100%" }}
                          renderInput={(params) => (
                            <TextField {...params} label="Select Span" placeholder="Choose which span to use" />
                          )}
                          renderOption={(props, option) => (
                            <li {...props} key={option.span_id}>
                              <Stack direction="column" spacing={0.5}>
                                <Typography variant="body2" fontWeight="medium">
                                  {option.span_name}
                                </Typography>
                                <Typography variant="caption" color="text.secondary" noWrap>
                                  → {option.extractedValue}
                                </Typography>
                              </Stack>
                            </li>
                          )}
                          onChange={(_, value) => {
                            if (value) {
                              const allColumns = form.state.values.columns;
                              const updatedColumns = allColumns.map((col, idx) =>
                                idx === index
                                  ? {
                                      ...col,
                                      selectedSpanId: value.span_id,
                                      value: value.extractedValue,
                                    }
                                  : col
                              );
                              form.setFieldValue("columns", updatedColumns);
                            }
                          }}
                          getOptionLabel={(option) => `${option.span_name}`}
                          isOptionEqualToValue={(option, value) => option.span_id === value.span_id}
                        />
                      ) : (
                        <SpanSelector form={form} spans={spans} name={column.name} container={ref.current!} index={index} />
                      )}
                    </Stack>
                    <Stack gap={1}>
                      <Typography variant="body2" fontWeight="medium">
                        Extracted Value {column.path && `(${column.path})`}
                      </Typography>
                      <TextField
                        disabled={!column.path}
                        placeholder="Select a span and drill down through its keys to extract data"
                        multiline
                        minRows={3}
                        maxRows={10}
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value)}
                        slotProps={{
                          input: {
                            sx: {
                              maxHeight: "240px",
                              overflow: "auto",
                            },
                          },
                        }}
                      />
                    </Stack>
                  </div>
                </>
              )}
            </form.Field>
          ))}
        </div>
        <Button
          variant="outlined"
          startIcon={<AddIcon />}
          onClick={onAddColumn}
          fullWidth
        >
          Add New Column
        </Button>
      </Stack>
    );
  },
});
