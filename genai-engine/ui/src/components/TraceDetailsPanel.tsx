import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TraceResponse, NestedSpanWithMetricsResponse } from "@/lib/api";
import {
  OpenInferenceSpanKind,
  SemanticConventions,
} from "@arizeai/openinference-semantic-conventions";

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
    const inputTokens =
      span.raw_data.attributes[SemanticConventions.LLM_TOKEN_COUNT_PROMPT];
    return inputTokens ? parseInt(inputTokens) : 0;
  }
  return 0;
};

const getOutputTokens = (span: NestedSpanWithMetricsResponse) => {
  if (span.raw_data && span.raw_data.attributes) {
    const outputTokens =
      span.raw_data.attributes[SemanticConventions.LLM_TOKEN_COUNT_COMPLETION];
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

const SpanNode: React.FC<SpanNodeProps> = ({
  span,
  level,
  onSpanClick,
  selectedSpanId,
}) => {
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
      const inputTokens =
        span.raw_data.attributes[SemanticConventions.LLM_TOKEN_COUNT_PROMPT];
      return inputTokens ? parseInt(inputTokens) : 0;
    }
    return 0;
  };

  const getOutputTokens = (span: NestedSpanWithMetricsResponse) => {
    // Try to get output tokens from various possible locations
    if (span.raw_data && span.raw_data.attributes) {
      const outputTokens =
        span.raw_data.attributes[
          SemanticConventions.LLM_TOKEN_COUNT_COMPLETION
        ];
      return outputTokens ? parseInt(outputTokens) : 0;
    }
    return 0;
  };

  const getSpanType = (span: NestedSpanWithMetricsResponse) => {
    if (span.raw_data && span.raw_data.attributes) {
      return span.raw_data.attributes[
        SemanticConventions.OPENINFERENCE_SPAN_KIND
      ];
    }
    return null;
  };

  const getSpanTypeColor = (spanType: string | null) => {
    switch (spanType) {
      case OpenInferenceSpanKind.LLM:
        return "text-blue-600";
      case OpenInferenceSpanKind.RETRIEVER:
        return "text-green-600";
      case OpenInferenceSpanKind.EMBEDDING:
        return "text-purple-600";
      case OpenInferenceSpanKind.CHAIN:
        return "text-orange-600";
      case OpenInferenceSpanKind.AGENT:
        return "text-red-600";
      case OpenInferenceSpanKind.TOOL:
        return "text-yellow-600";
      case OpenInferenceSpanKind.RERANKER:
        return "text-indigo-600";
      case OpenInferenceSpanKind.GUARDRAIL:
        return "text-red-700";
      case OpenInferenceSpanKind.EVALUATOR:
        return "text-green-700";
      default:
        return "text-gray-600";
    }
  };

  const inputTokens = getInputTokens(span);
  const outputTokens = getOutputTokens(span);
  const totalTokens = inputTokens + outputTokens;
  const spanType = getSpanType(span);

  return (
    <div className="ml-4">
      <div
        className={`flex items-center py-1 hover:bg-gray-100 rounded ${
          isSelected ? "bg-blue-100" : ""
        }`}
        style={{ marginLeft: `${level * 16}px` }}
      >
        <div
          className="flex-1 cursor-pointer flex items-center"
          onClick={() => onSpanClick(span)}
        >
          {spanType && (
            <span
              className={`mr-2 text-xs px-2 py-0.5 rounded-full bg-gray-100 ${getSpanTypeColor(
                spanType
              )}`}
            >
              {spanType}
            </span>
          )}
          <span className="text-gray-900 font-medium">{span.span_name}</span>
          <span className="text-gray-600 ml-2">
            ({formatDuration(span.start_time, span.end_time)})
          </span>
          {totalTokens > 0 && (
            <span className="text-gray-600 ml-2">
              {inputTokens} → {outputTokens} (Σ {totalTokens})
            </span>
          )}
        </div>

        {hasChildren && (
          <div
            className="ml-2 text-gray-600 cursor-pointer hover:text-gray-800 flex-shrink-0"
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
            className="absolute w-px bg-gray-300"
            style={{
              left: `${level * 16 + 6}px`,
              top: "0px",
              height: "calc(100% - 12px)",
            }}
          />
          {span.children?.map((child, index) => (
            <SpanNode
              key={index}
              span={child}
              level={level + 1}
              onSpanClick={onSpanClick}
              selectedSpanId={selectedSpanId}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const SpanDetails: React.FC<SpanDetailsProps> = ({ span }) => {
  if (!span) {
    return (
      <div className="h-full flex items-center justify-center text-gray-600">
        Select a span to view details
      </div>
    );
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const utcTimestamp = timestamp.endsWith("Z")
        ? timestamp
        : timestamp + "Z";
      const date = new Date(utcTimestamp);
      if (isNaN(date.getTime())) {
        return "Invalid Date";
      }
      return date.toLocaleString("en-US", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
        timeZoneName: "short",
      });
    } catch {
      return "Invalid Date";
    }
  };

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
    if (
      span.raw_data &&
      span.raw_data.attributes &&
      span.raw_data.attributes[SemanticConventions.INPUT_VALUE]
    ) {
      return span.raw_data.attributes[SemanticConventions.INPUT_VALUE];
    }
    return "No input data";
  };

  const getOutputContent = (span: NestedSpanWithMetricsResponse) => {
    if (
      span.raw_data &&
      span.raw_data.attributes &&
      span.raw_data.attributes[SemanticConventions.OUTPUT_VALUE]
    ) {
      return span.raw_data.attributes[SemanticConventions.OUTPUT_VALUE];
    }
    return "No output data";
  };

  const getInputMimeType = (span: NestedSpanWithMetricsResponse) => {
    if (
      span.raw_data &&
      span.raw_data.attributes &&
      span.raw_data.attributes[SemanticConventions.INPUT_MIME_TYPE]
    ) {
      return span.raw_data.attributes[SemanticConventions.INPUT_MIME_TYPE];
    }
    return null;
  };

  const getOutputMimeType = (span: NestedSpanWithMetricsResponse) => {
    if (
      span.raw_data &&
      span.raw_data.attributes &&
      span.raw_data.attributes[SemanticConventions.OUTPUT_MIME_TYPE]
    ) {
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
          <h2 className="text-xl font-semibold mb-2 text-gray-900">
            {span.span_name}
          </h2>
          <p className="text-gray-600 text-sm mb-4">{span.span_id}</p>

          {/* Metrics */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Duration:</span>
              <span className="ml-1 text-gray-900">
                {formatDuration(span.start_time, span.end_time)}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Start Time:</span>
              <span className="ml-1 text-gray-900">
                {formatTimestamp(span.start_time)}
              </span>
            </div>
            {totalTokens > 0 && (
              <>
                <div>
                  <span className="text-gray-600">Input Tokens:</span>
                  <span className="ml-1 text-gray-900">
                    {inputTokens.toLocaleString()}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Output Tokens:</span>
                  <span className="ml-1 text-gray-900">
                    {outputTokens.toLocaleString()}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Input/Output */}
        <div>
          <h3 className="text-sm font-medium text-gray-600 mb-2">Input</h3>
          <div className="bg-gray-100 p-3 rounded text-sm text-gray-900">
            {inputMimeType === "application/json" ? (
              <pre className="whitespace-pre-wrap font-mono text-xs">
                {formatJsonContent(inputContent)}
              </pre>
            ) : (
              inputContent
            )}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-medium text-gray-600 mb-2">Output</h3>
          <div className="bg-gray-100 p-3 rounded text-sm text-gray-900">
            {outputMimeType === "application/json" ? (
              <pre className="whitespace-pre-wrap font-mono text-xs">
                {formatJsonContent(outputContent)}
              </pre>
            ) : (
              <div className="whitespace-pre-wrap">{outputContent}</div>
            )}
          </div>
        </div>

        {/* Metadata */}
        <div>
          <h3 className="text-sm font-medium text-gray-600 mb-2">Metadata</h3>
          <div className="bg-gray-100 p-3 rounded text-sm text-gray-900">
            <div className="space-y-2">
              <div className="flex">
                <span className="text-gray-600 w-24">Span ID:</span>
                <span className="font-mono text-xs text-gray-900">
                  {span.span_id}
                </span>
              </div>
              <div className="flex">
                <span className="text-gray-600 w-24">Span Name:</span>
                <span className="text-gray-900">{span.span_name}</span>
              </div>
              <div className="flex">
                <span className="text-gray-600 w-24">Start Time:</span>
                <span className="font-mono text-xs text-gray-900">
                  {span.start_time}
                </span>
              </div>
              <div className="flex">
                <span className="text-gray-600 w-24">End Time:</span>
                <span className="font-mono text-xs text-gray-900">
                  {span.end_time}
                </span>
              </div>
              {span.raw_data && span.raw_data.attributes && (
                <div>
                  <span className="text-gray-600">Attributes:</span>
                  <pre className="mt-1 text-xs bg-white p-2 rounded overflow-x-auto text-gray-900 border">
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

export const TraceDetailsPanel: React.FC<TraceDetailsPanelProps> = ({
  trace,
  isOpen,
  onClose,
}) => {
  const [selectedSpan, setSelectedSpan] =
    useState<NestedSpanWithMetricsResponse | null>(null);
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
    if (
      isOpen &&
      trace &&
      trace.root_spans &&
      trace.root_spans.length > 0 &&
      !selectedSpan
    ) {
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
            className="absolute right-0 top-0 h-full w-4/5 bg-white text-gray-900 shadow-xl flex flex-col"
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
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    {getSpanName(trace)}
                  </h2>
                  <p className="text-gray-600 text-sm">{trace.trace_id}</p>
                </div>
                <button
                  onClick={onClose}
                  className="text-gray-600 hover:text-gray-900"
                >
                  <svg
                    className="h-6 w-6"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Duration:</span>
                  <span className="ml-1 text-gray-900">
                    {formatDuration(trace.start_time, trace.end_time)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Total Cost:</span>
                  <span className="ml-1 text-gray-900">
                    ${getTotalCost(trace).toFixed(5)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Token Counts:</span>
                  <span className="ml-1 text-gray-900">
                    {getTotalTokens(trace).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            {/* Two-panel layout */}
            <div className="flex flex-1 min-h-0">
              {/* Left panel - Trace tree */}
              <div className="w-1/2 border-r border-gray-200 flex flex-col">
                <div className="p-4 flex-1 overflow-y-auto">
                  <h3 className="text-sm font-medium text-gray-600 mb-4">
                    Trace
                  </h3>
                  {trace.root_spans && trace.root_spans.length > 0 ? (
                    <div>
                      {trace.root_spans.map((span, index) => (
                        <SpanNode
                          key={index}
                          span={span}
                          level={0}
                          onSpanClick={handleSpanClick}
                          selectedSpanId={selectedSpan?.span_id}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="text-gray-400">No trace data available</div>
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
