import { OpenInferenceSpanKind, SemanticConventions } from "@arizeai/openinference-semantic-conventions";
import Chip from "@mui/material/Chip";
import { alpha, type Theme, useTheme } from "@mui/material/styles";
import { motion, AnimatePresence } from "framer-motion";
import React, { useState, useEffect } from "react";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { TraceResponse, NestedSpanWithMetricsResponse } from "@/lib/api";
import { formatCurrency, formatDateInTimezone } from "@/utils/formatters";

interface TraceDetailsPanelProps {
  trace: TraceResponse | null;
  isOpen: boolean;
  onClose: () => void;
}

interface SpanDetailsProps {
  span: NestedSpanWithMetricsResponse | null;
}

interface SpanNodeProps {
  span: NestedSpanWithMetricsResponse;
  level: number;
  onSpanClick: (span: NestedSpanWithMetricsResponse) => void;
  selectedSpanId: string | undefined;
}

// Shared utility functions
const getInputTokens = (span: NestedSpanWithMetricsResponse) => {
  if (span.raw_data && span.raw_data.attributes) {
    const inputTokens = span.raw_data.attributes[SemanticConventions.LLM_TOKEN_COUNT_PROMPT];
    return inputTokens ? parseInt(inputTokens) : 0;
  }
  return 0;
};

const getOutputTokens = (span: NestedSpanWithMetricsResponse) => {
  if (span.raw_data && span.raw_data.attributes) {
    const outputTokens = span.raw_data.attributes[SemanticConventions.LLM_TOKEN_COUNT_COMPLETION];
    return outputTokens ? parseInt(outputTokens) : 0;
  }
  return 0;
};

const getSpanTotalCost = (span: NestedSpanWithMetricsResponse) => {
  if (span.raw_data && span.raw_data.attributes) {
    const cost = span.raw_data.attributes[SemanticConventions.LLM_COST_TOTAL];
    return cost ? parseFloat(cost) : 0;
  }
  return 0;
};

const SpanNode: React.FC<SpanNodeProps> = ({ span, level, onSpanClick, selectedSpanId }) => {
  const theme = useTheme();
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = span.children && span.children.length > 0;
  const isSelected = span.span_id === selectedSpanId;

  const formatDuration = (startTime: string, endTime: string) => {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const durationMs = end.getTime() - start.getTime();

    if (durationMs < 1000) {
      return `${durationMs}ms`;
    } else if (durationMs < 60000) {
      return `${(durationMs / 1000).toFixed(2)}s`;
    } else {
      const minutes = Math.floor(durationMs / 60000);
      const seconds = Math.floor((durationMs % 60000) / 1000);
      return `${minutes}m ${seconds}s`;
    }
  };

  const getInputTokens = (span: NestedSpanWithMetricsResponse) => {
    // Try to get input tokens from various possible locations
    if (span.raw_data && span.raw_data.attributes) {
      const inputTokens = span.raw_data.attributes[SemanticConventions.LLM_TOKEN_COUNT_PROMPT];
      return inputTokens ? parseInt(inputTokens) : 0;
    }
    return 0;
  };

  const getOutputTokens = (span: NestedSpanWithMetricsResponse) => {
    // Try to get output tokens from various possible locations
    if (span.raw_data && span.raw_data.attributes) {
      const outputTokens = span.raw_data.attributes[SemanticConventions.LLM_TOKEN_COUNT_COMPLETION];
      return outputTokens ? parseInt(outputTokens) : 0;
    }
    return 0;
  };

  const getSpanType = (span: NestedSpanWithMetricsResponse) => {
    if (span.raw_data && span.raw_data.attributes) {
      return span.raw_data.attributes[SemanticConventions.OPENINFERENCE_SPAN_KIND];
    }
    return null;
  };

  const getSpanTypeColor = (theme: Theme, spanType: string | null): string => {
    const colorMap: Record<string, string> = {
      [OpenInferenceSpanKind.LLM]: theme.palette.info.main,
      [OpenInferenceSpanKind.RETRIEVER]: theme.palette.success.main,
      [OpenInferenceSpanKind.EMBEDDING]: theme.palette.secondary.main,
      [OpenInferenceSpanKind.CHAIN]: theme.palette.warning.main,
      [OpenInferenceSpanKind.AGENT]: theme.palette.error.main,
      [OpenInferenceSpanKind.TOOL]: theme.palette.warning.light,
      [OpenInferenceSpanKind.RERANKER]: theme.palette.primary.main,
      [OpenInferenceSpanKind.GUARDRAIL]: theme.palette.error.dark,
      [OpenInferenceSpanKind.EVALUATOR]: theme.palette.success.dark,
    };
    return spanType ? (colorMap[spanType] ?? theme.palette.text.secondary) : theme.palette.text.secondary;
  };

  const inputTokens = getInputTokens(span);
  const outputTokens = getOutputTokens(span);
  const totalTokens = inputTokens + outputTokens;
  const spanType = getSpanType(span);

  return (
    <div className="ml-4">
      <div
        className={`flex items-center py-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded ${isSelected ? "bg-blue-100 dark:bg-blue-900/30" : ""}`}
        style={{ marginLeft: `${level * 16}px` }}
      >
        <div className="flex-1 cursor-pointer flex items-center" onClick={() => onSpanClick(span)}>
          {spanType && (
            <Chip
              label={spanType}
              size="small"
              sx={{
                mr: 1,
                height: 20,
                fontSize: "0.75rem",
                color: getSpanTypeColor(theme, spanType),
                backgroundColor: (theme) => alpha(getSpanTypeColor(theme, spanType), 0.12),
                "& .MuiChip-label": {
                  px: 1,
                  py: 0,
                },
              }}
            />
          )}
          <span className="text-gray-900 dark:text-gray-100 font-medium">{span.span_name}</span>
          <span className="text-gray-600 dark:text-gray-400 ml-2">({formatDuration(span.start_time, span.end_time)})</span>
          {totalTokens > 0 && (
            <span className="text-gray-600 dark:text-gray-400 ml-2">
              {inputTokens} → {outputTokens} (Σ {totalTokens})
            </span>
          )}
        </div>

        {hasChildren && (
          <div
            className="ml-2 text-gray-600 dark:text-gray-400 cursor-pointer hover:text-gray-800 dark:hover:text-gray-200 flex-shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
          >
            {isExpanded ? "▼" : "▶"}
          </div>
        )}
      </div>

      {hasChildren && isExpanded && (
        <div className="relative ml-4">
          {/* Vertical line from parent to middle of last child */}
          <div
            className="absolute w-px bg-gray-300 dark:bg-gray-600"
            style={{
              left: `${level * 16 + 6}px`,
              top: "0px",
              height: "calc(100% - 12px)",
            }}
          />
          {span.children?.map((child, index) => (
            <SpanNode key={index} span={child} level={level + 1} onSpanClick={onSpanClick} selectedSpanId={selectedSpanId} />
          ))}
        </div>
      )}
    </div>
  );
};

const SpanDetails: React.FC<SpanDetailsProps> = ({ span }) => {
  const { timezone, use24Hour } = useDisplaySettings();

  if (!span) {
    return <div className="h-full flex items-center justify-center text-gray-600 dark:text-gray-400">Select a span to view details</div>;
  }

  const formatDuration = (startTime: string, endTime: string) => {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const durationMs = end.getTime() - start.getTime();

    if (durationMs < 1000) {
      return `${durationMs}ms`;
    } else if (durationMs < 60000) {
      return `${(durationMs / 1000).toFixed(2)}s`;
    } else {
      const minutes = Math.floor(durationMs / 60000);
      const seconds = Math.floor((durationMs % 60000) / 1000);
      return `${minutes}m ${seconds}s`;
    }
  };

  const getInputContent = (span: NestedSpanWithMetricsResponse) => {
    if (span.raw_data && span.raw_data.attributes && span.raw_data.attributes[SemanticConventions.INPUT_VALUE]) {
      return span.raw_data.attributes[SemanticConventions.INPUT_VALUE];
    }
    return "No input data";
  };

  const getOutputContent = (span: NestedSpanWithMetricsResponse) => {
    if (span.raw_data && span.raw_data.attributes && span.raw_data.attributes[SemanticConventions.OUTPUT_VALUE]) {
      return span.raw_data.attributes[SemanticConventions.OUTPUT_VALUE];
    }
    return "No output data";
  };

  const getInputMimeType = (span: NestedSpanWithMetricsResponse) => {
    if (span.raw_data && span.raw_data.attributes && span.raw_data.attributes[SemanticConventions.INPUT_MIME_TYPE]) {
      return span.raw_data.attributes[SemanticConventions.INPUT_MIME_TYPE];
    }
    return null;
  };

  const getOutputMimeType = (span: NestedSpanWithMetricsResponse) => {
    if (span.raw_data && span.raw_data.attributes && span.raw_data.attributes[SemanticConventions.OUTPUT_MIME_TYPE]) {
      return span.raw_data.attributes[SemanticConventions.OUTPUT_MIME_TYPE];
    }
    return null;
  };

  const formatJsonContent = (content: string) => {
    try {
      const parsed = JSON.parse(content);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return content;
    }
  };

  const inputTokens = getInputTokens(span);
  const outputTokens = getOutputTokens(span);
  const totalTokens = inputTokens + outputTokens;
  const inputMimeType = getInputMimeType(span);
  const outputMimeType = getOutputMimeType(span);
  const inputContent = getInputContent(span);
  const outputContent = getOutputContent(span);

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-semibold mb-2 text-gray-900 dark:text-gray-100">{span.span_name}</h2>
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">{span.span_id}</p>

          {/* Metrics */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600 dark:text-gray-400">Duration:</span>
              <span className="ml-1 text-gray-900 dark:text-gray-100">{formatDuration(span.start_time, span.end_time)}</span>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">Start Time:</span>
              <span className="ml-1 text-gray-900 dark:text-gray-100">{formatDateInTimezone(span.start_time, timezone, { hour12: !use24Hour })}</span>
            </div>
            {totalTokens > 0 && (
              <>
                <div>
                  <span className="text-gray-600 dark:text-gray-400">Input Tokens:</span>
                  <span className="ml-1 text-gray-900 dark:text-gray-100">{inputTokens.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-gray-600 dark:text-gray-400">Output Tokens:</span>
                  <span className="ml-1 text-gray-900 dark:text-gray-100">{outputTokens.toLocaleString()}</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Input/Output */}
        <div>
          <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Input</h3>
          <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded text-sm text-gray-900 dark:text-gray-100">
            {inputMimeType === "application/json" ? (
              <pre className="whitespace-pre-wrap font-mono text-xs">{formatJsonContent(inputContent)}</pre>
            ) : (
              inputContent
            )}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Output</h3>
          <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded text-sm text-gray-900 dark:text-gray-100">
            {outputMimeType === "application/json" ? (
              <pre className="whitespace-pre-wrap font-mono text-xs">{formatJsonContent(outputContent)}</pre>
            ) : (
              <div className="whitespace-pre-wrap">{outputContent}</div>
            )}
          </div>
        </div>

        {/* Metadata */}
        <div>
          <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Metadata</h3>
          <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded text-sm text-gray-900 dark:text-gray-100">
            <div className="space-y-2">
              <div className="flex">
                <span className="text-gray-600 dark:text-gray-400 w-24">Span ID:</span>
                <span className="font-mono text-xs text-gray-900 dark:text-gray-100">{span.span_id}</span>
              </div>
              <div className="flex">
                <span className="text-gray-600 dark:text-gray-400 w-24">Span Name:</span>
                <span className="text-gray-900 dark:text-gray-100">{span.span_name}</span>
              </div>
              <div className="flex">
                <span className="text-gray-600 dark:text-gray-400 w-24">Start Time:</span>
                <span className="font-mono text-xs text-gray-900 dark:text-gray-100">{span.start_time}</span>
              </div>
              <div className="flex">
                <span className="text-gray-600 dark:text-gray-400 w-24">End Time:</span>
                <span className="font-mono text-xs text-gray-900 dark:text-gray-100">{span.end_time}</span>
              </div>
              {span.raw_data && span.raw_data.attributes && (
                <div>
                  <span className="text-gray-600 dark:text-gray-400">Attributes:</span>
                  <pre className="mt-1 text-xs bg-white dark:bg-gray-900 p-2 rounded overflow-x-auto text-gray-900 dark:text-gray-100 border dark:border-gray-600">
                    {JSON.stringify(span.raw_data.attributes, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export const TraceDetailsPanel: React.FC<TraceDetailsPanelProps> = ({ trace, isOpen, onClose }) => {
  const { defaultCurrency } = useDisplaySettings();
  const [selectedSpan, setSelectedSpan] = useState<NestedSpanWithMetricsResponse | null>(null);
  const [shouldRender, setShouldRender] = useState(false);

  // Handle mounting/unmounting with proper timing for animations
  useEffect(() => {
    if (isOpen) {
      setShouldRender(true);
    } else {
      // Keep component mounted during exit animation
      const timer = setTimeout(() => setShouldRender(false), 300);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Auto-select the first span when the panel opens
  useEffect(() => {
    if (isOpen && trace && trace.root_spans && trace.root_spans.length > 0 && !selectedSpan) {
      setSelectedSpan(trace.root_spans[0]);
    }
  }, [isOpen, trace, selectedSpan]);

  if (!trace || !shouldRender) return null;

  const formatDuration = (startTime: string, endTime: string) => {
    const start = new Date(startTime);
    const end = new Date(endTime);
    const durationMs = end.getTime() - start.getTime();

    if (durationMs < 1000) {
      return `${durationMs}ms`;
    } else if (durationMs < 60000) {
      return `${(durationMs / 1000).toFixed(2)}s`;
    } else {
      const minutes = Math.floor(durationMs / 60000);
      const seconds = Math.floor((durationMs % 60000) / 1000);
      return `${minutes}m ${seconds}s`;
    }
  };

  const getSpanName = (trace: TraceResponse) => {
    if (trace.root_spans && trace.root_spans.length > 0) {
      return trace.root_spans[0].span_name || "Unknown";
    }
    return "Unknown";
  };

  const getTotalTokens = (trace: TraceResponse) => {
    if (trace.root_spans && trace.root_spans.length > 0) {
      const span = trace.root_spans[0];
      if (span.raw_data && span.raw_data.tokens) {
        return span.raw_data.tokens;
      }
    }
    return 0;
  };

  const getTotalCost = (trace: TraceResponse) => {
    if (trace.root_spans && trace.root_spans.length > 0) {
      const span = trace.root_spans[0];
      return getSpanTotalCost(span);
    }
    return 0;
  };

  const handleSpanClick = (span: NestedSpanWithMetricsResponse) => {
    setSelectedSpan(span);
  };

  return (
    <AnimatePresence>
      {shouldRender && (
        <motion.div
          className="fixed inset-0 z-50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0"
            style={{ backgroundColor: "rgba(0, 0, 0, 0.2)" }}
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          />

          {/* Panel */}
          <motion.div
            className="absolute right-0 top-0 h-full w-4/5 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-xl flex flex-col"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{
              type: "tween",
              duration: 0.3,
              ease: "easeInOut",
            }}
          >
            {/* Header */}
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{getSpanName(trace)}</h2>
                  <p className="text-gray-600 dark:text-gray-400 text-sm">{trace.trace_id}</p>
                </div>
                <button onClick={onClose} className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100">
                  <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600 dark:text-gray-400">Duration:</span>
                  <span className="ml-1 text-gray-900 dark:text-gray-100">{formatDuration(trace.start_time, trace.end_time)}</span>
                </div>
                <div>
                  <span className="text-gray-600 dark:text-gray-400">Total Cost:</span>
                  <span className="ml-1 text-gray-900 dark:text-gray-100">{formatCurrency(getTotalCost(trace), defaultCurrency)}</span>
                </div>
                <div>
                  <span className="text-gray-600 dark:text-gray-400">Token Counts:</span>
                  <span className="ml-1 text-gray-900 dark:text-gray-100">{getTotalTokens(trace).toLocaleString()}</span>
                </div>
              </div>
            </div>

            {/* Two-panel layout */}
            <div className="flex flex-1 min-h-0">
              {/* Left panel - Trace tree */}
              <div className="w-1/2 border-r border-gray-200 dark:border-gray-700 flex flex-col">
                <div className="p-4 flex-1 overflow-y-auto">
                  <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-4">Trace</h3>
                  {trace.root_spans && trace.root_spans.length > 0 ? (
                    <div>
                      {trace.root_spans.map((span, index) => (
                        <SpanNode key={index} span={span} level={0} onSpanClick={handleSpanClick} selectedSpanId={selectedSpan?.span_id} />
                      ))}
                    </div>
                  ) : (
                    <div className="text-gray-400 dark:text-gray-500">No trace data available</div>
                  )}
                </div>
              </div>

              {/* Right panel - Span details */}
              <div className="w-1/2 flex flex-col min-h-0">
                <SpanDetails span={selectedSpan} />
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
