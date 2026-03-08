import type { GetSpanDetailsStrategy } from "@arthur/shared-components";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Box, IconButton, Stack, Tooltip, Typography } from "@mui/material";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { AttributePickerTree } from "./AttributePickerTree";
import { ContinuousEvalStepper, type PickerState } from "./ContinuousEvalStepper";

import { SpanDetails, SpanDetailsHeader, SpanDetailsPanels, SpanDetailsWidgets } from "@/components/traces/components/SpanDetails";
import { SpanTree } from "@/components/traces/components/SpanTree";
import { getSpanDetailsStrategy } from "@/components/traces/data/details-strategy";
import { flattenSpans } from "@/components/traces/utils/spans";
import { getContentHeight } from "@/constants/layout";
import { useApi } from "@/hooks/useApi";
import type { NestedSpanWithMetricsResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";
import { getTrace } from "@/services/tracing";

type VariableRow = {
  variable_name: string;
  span_name: string;
  attribute_path: string;
  fallback: string;
  previewValue?: string;
};

type Props = {
  traceId: string;
};

export const ContinuousEvalWithTracePage = ({ traceId }: Props) => {
  const api = useApi();
  const navigate = useNavigate();

  const { data: trace } = useSuspenseQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.traces.byId(traceId),
    queryFn: () => getTrace(api!, { traceId }),
  });

  const flatSpans = useMemo(() => flattenSpans(trace?.root_spans ?? []), [trace]);
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(trace?.root_spans?.[0]?.span_id ?? null);
  const [pickerState, setPickerState] = useState<PickerState>(null);
  const [inlineVariables, setInlineVariables] = useState<VariableRow[]>([]);

  const selectedSpan = useMemo(() => flatSpans.find((s) => s.span_id === selectedSpanId) ?? null, [flatSpans, selectedSpanId]);

  const handleStartPicking = useCallback((variableIndex: number, variableName: string) => {
    setPickerState({ variableIndex, variableName });
  }, []);

  const handleCancelPicking = useCallback(() => {
    setPickerState(null);
  }, []);

  const handlePickAttribute = useCallback((variableIndex: number, spanName: string, attributePath: string, previewValue: string) => {
    setInlineVariables((prev) => {
      const updated = [...prev];
      if (updated[variableIndex]) {
        updated[variableIndex] = {
          ...updated[variableIndex],
          span_name: spanName,
          attribute_path: attributePath,
          previewValue,
        };
      }
      return updated;
    });
    setPickerState(null);
  }, []);

  const handleSelectPathInPicker = useCallback(
    (path: string) => {
      if (!pickerState || !selectedSpan) return;

      const spanName = selectedSpan.span_name ?? "";
      const value = getValueAtPath(selectedSpan.raw_data, path);
      const previewValue = value !== undefined ? JSON.stringify(value) : "";

      handlePickAttribute(pickerState.variableIndex, spanName, path, previewValue);
    },
    [pickerState, selectedSpan, handlePickAttribute]
  );

  return (
    <Stack direction="column" sx={{ height: getContentHeight() }}>
      <Stack
        direction="row"
        alignItems="center"
        gap={1}
        sx={{ px: 2, py: 1, borderBottom: 1, borderColor: "divider", backgroundColor: "background.paper" }}
      >
        <Tooltip title="Go back">
          <IconButton onClick={() => navigate(-1)} size="small">
            <ArrowBackIcon />
          </IconButton>
        </Tooltip>
        <Typography variant="subtitle1" fontWeight={600} color="text.primary">
          Create Continuous Eval from Trace
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ fontFamily: "monospace" }}>
          {traceId}
        </Typography>
      </Stack>

      <Stack direction="row" sx={{ flex: 1, overflow: "hidden" }}>
        {/* Left column: Span Tree */}
        <Box
          sx={{
            width: "25%",
            minWidth: 200,
            borderRight: 1,
            borderColor: "divider",
            overflow: "auto",
            py: 1,
          }}
        >
          <SpanTree spans={trace?.root_spans ?? []} selectedSpanId={selectedSpanId} onSelectSpan={(spanId) => setSelectedSpanId(spanId)} />
        </Box>

        {/* Center column: Span Content or Picker */}
        <Box
          sx={{
            width: "40%",
            borderRight: 1,
            borderColor: "divider",
            overflow: "auto",
          }}
        >
          {pickerState && selectedSpan ? (
            <AttributePickerTree
              rawData={selectedSpan.raw_data}
              variableName={pickerState.variableName}
              selectedPath={null}
              onSelectPath={handleSelectPathInPicker}
              onCancel={handleCancelPicking}
            />
          ) : selectedSpan ? (
            <SpanContentView span={selectedSpan} />
          ) : (
            <Box sx={{ p: 3 }}>
              <Typography variant="body2" color="text.secondary">
                Select a span to view its details
              </Typography>
            </Box>
          )}
        </Box>

        {/* Right column: Stepper Form */}
        <Box
          sx={{
            width: "35%",
            minWidth: 300,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <ContinuousEvalStepper
            selectedSpan={selectedSpan}
            pickerState={pickerState}
            onStartPicking={handleStartPicking}
            onCancelPicking={handleCancelPicking}
            inlineVariables={inlineVariables}
            onSetInlineVariables={setInlineVariables}
          />
        </Box>
      </Stack>
    </Stack>
  );
};

const SpanContentView = ({ span }: { span: NestedSpanWithMetricsResponse }) => {
  const strategy = getSpanDetailsStrategy(span.span_kind as Parameters<Exclude<GetSpanDetailsStrategy, undefined>>[0]);

  if (!strategy) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="body2" color="text.secondary">
          No details available for this span type.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <SpanDetails span={span}>
        <SpanDetailsHeader />
        <SpanDetailsWidgets />
        <SpanDetailsPanels />
      </SpanDetails>
    </Box>
  );
};

function getValueAtPath(data: Record<string, unknown>, path: string): unknown {
  const parts = path.split(/\.|\[(\d+)\]/).filter(Boolean);
  let current: unknown = data;
  for (const part of parts) {
    if (current === null || current === undefined) return undefined;
    if (typeof current === "object") {
      current = (current as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }
  return current;
}
