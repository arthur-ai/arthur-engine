'use client';

import React, { useState, useEffect } from 'react';
import { TraceResponse, NestedSpanWithMetricsResponse } from '@/lib/api';

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

const SpanNode: React.FC<SpanNodeProps> = ({ span, level, onSpanClick, selectedSpanId }) => {
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
      const inputTokens = span.raw_data.attributes["input.tokens"] || 
                         span.raw_data.attributes["llm.usage.prompt_tokens"];
      return inputTokens ? parseInt(inputTokens) : 0;
    }
    return 0;
  };

  const getOutputTokens = (span: NestedSpanWithMetricsResponse) => {
    // Try to get output tokens from various possible locations
    if (span.raw_data && span.raw_data.attributes) {
      const outputTokens = span.raw_data.attributes["output.tokens"] || 
                          span.raw_data.attributes["llm.usage.completion_tokens"];
      return outputTokens ? parseInt(outputTokens) : 0;
    }
    return 0;
  };

  const inputTokens = getInputTokens(span);
  const outputTokens = getOutputTokens(span);
  const totalTokens = inputTokens + outputTokens;

  return (
    <div className="ml-4">
      <div 
        className={`flex items-center py-1 cursor-pointer hover:bg-gray-100 rounded ${
          isSelected ? 'bg-blue-100' : ''
        }`}
        onClick={() => {
          onSpanClick(span);
          if (hasChildren) {
            setIsExpanded(!isExpanded);
          }
        }}
      >
        {hasChildren && (
          <div className="mr-2 text-gray-600">
            {isExpanded ? '▼' : '▶'}
          </div>
        )}
        {!hasChildren && <div className="mr-2 w-4" />}
        
        <div className="flex-1">
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
      </div>
      
      {hasChildren && isExpanded && (
        <div className="ml-4">
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
      const utcTimestamp = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z';
      const date = new Date(utcTimestamp);
      if (isNaN(date.getTime())) {
        return 'Invalid Date';
      }
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        timeZoneName: 'short',
      });
    } catch {
      return 'Invalid Date';
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
    if (span.raw_data && span.raw_data.attributes && span.raw_data.attributes["input.value"]) {
      return span.raw_data.attributes["input.value"];
    }
    return 'No input data';
  };

  const getOutputContent = (span: NestedSpanWithMetricsResponse) => {
    if (span.raw_data && span.raw_data.attributes && span.raw_data.attributes["output.value"]) {
      return span.raw_data.attributes["output.value"];
    }
    return 'No output data';
  };

  const getInputTokens = (span: NestedSpanWithMetricsResponse) => {
    if (span.raw_data && span.raw_data.attributes) {
      const inputTokens = span.raw_data.attributes["input.tokens"] || 
                         span.raw_data.attributes["llm.usage.prompt_tokens"];
      return inputTokens ? parseInt(inputTokens) : 0;
    }
    return 0;
  };

  const getOutputTokens = (span: NestedSpanWithMetricsResponse) => {
    if (span.raw_data && span.raw_data.attributes) {
      const outputTokens = span.raw_data.attributes["output.tokens"] || 
                          span.raw_data.attributes["llm.usage.completion_tokens"];
      return outputTokens ? parseInt(outputTokens) : 0;
    }
    return 0;
  };

  const inputTokens = getInputTokens(span);
  const outputTokens = getOutputTokens(span);
  const totalTokens = inputTokens + outputTokens;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-xl font-semibold mb-2 text-gray-900">{span.span_name}</h2>
        <p className="text-gray-600 text-sm mb-4">{span.span_id}</p>
        
        {/* Metrics */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Duration:</span>
            <span className="ml-1 text-gray-900">{formatDuration(span.start_time, span.end_time)}</span>
          </div>
          <div>
            <span className="text-gray-600">Start Time:</span>
            <span className="ml-1 text-gray-900">{formatTimestamp(span.start_time)}</span>
          </div>
          {totalTokens > 0 && (
            <>
              <div>
                <span className="text-gray-600">Input Tokens:</span>
                <span className="ml-1 text-gray-900">{inputTokens.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-gray-600">Output Tokens:</span>
                <span className="ml-1 text-gray-900">{outputTokens.toLocaleString()}</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-6">
          {/* Input/Output */}
          <div>
            <h3 className="text-sm font-medium text-gray-600 mb-2">Input</h3>
            <div className="bg-gray-100 p-3 rounded text-sm text-gray-900">
              {getInputContent(span)}
            </div>
          </div>
          
          <div>
            <h3 className="text-sm font-medium text-gray-600 mb-2">Output</h3>
            <div className="bg-gray-100 p-3 rounded text-sm text-gray-900 whitespace-pre-wrap">
              {getOutputContent(span)}
            </div>
          </div>

          {/* Metadata */}
          <div>
            <h3 className="text-sm font-medium text-gray-600 mb-2">Metadata</h3>
            <div className="bg-gray-100 p-3 rounded text-sm text-gray-900">
              <div className="space-y-2">
                <div className="flex">
                  <span className="text-gray-600 w-24">Span ID:</span>
                  <span className="font-mono text-xs text-gray-900">{span.span_id}</span>
                </div>
                <div className="flex">
                  <span className="text-gray-600 w-24">Span Name:</span>
                  <span className="text-gray-900">{span.span_name}</span>
                </div>
                <div className="flex">
                  <span className="text-gray-600 w-24">Start Time:</span>
                  <span className="font-mono text-xs text-gray-900">{span.start_time}</span>
                </div>
                <div className="flex">
                  <span className="text-gray-600 w-24">End Time:</span>
                  <span className="font-mono text-xs text-gray-900">{span.end_time}</span>
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
    </div>
  );
};

export const TraceDetailsPanel: React.FC<TraceDetailsPanelProps> = ({
  trace,
  isOpen,
  onClose
}) => {
  const [selectedSpan, setSelectedSpan] = useState<NestedSpanWithMetricsResponse | null>(null);

  // Auto-select the first span when the panel opens
  useEffect(() => {
    if (isOpen && trace && trace.root_spans && trace.root_spans.length > 0 && !selectedSpan) {
      setSelectedSpan(trace.root_spans[0]);
    }
  }, [isOpen, trace, selectedSpan]);

  if (!trace) return null;

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
      return trace.root_spans[0].span_name || 'Unknown';
    }
    return 'Unknown';
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

  const handleSpanClick = (span: NestedSpanWithMetricsResponse) => {
    setSelectedSpan(span);
  };

  return (
    <div className={`fixed inset-0 z-50 ${isOpen ? 'block' : 'hidden'}`}>
      {/* Backdrop */}
      <div 
        className="absolute inset-0"
        style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}
        onClick={onClose}
      />
      
      {/* Panel */}
      <div className={`absolute right-0 top-0 h-full w-4/5 bg-white text-gray-900 transform transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">{getSpanName(trace)}</h2>
              <p className="text-gray-600 text-sm">{trace.trace_id}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-600 hover:text-gray-900"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Action Buttons */}
          <div className="flex space-x-2 mb-4">
            <button className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm text-white">
              Add to datasets
            </button>
            <button className="px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded text-sm text-gray-900">
              Annotate
            </button>
            <button className="px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded text-sm text-gray-900">
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </button>
          </div>
          
          {/* Metrics */}
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Env:</span>
              <span className="ml-1 text-gray-900">default</span>
            </div>
            <div>
              <span className="text-gray-600">Duration:</span>
              <span className="ml-1 text-gray-900">{formatDuration(trace.start_time, trace.end_time)}</span>
            </div>
            <div>
              <span className="text-gray-600">Total Cost:</span>
              <span className="ml-1 text-gray-900">$0.00000</span>
            </div>
            <div>
              <span className="text-gray-600">Token Counts:</span>
              <span className="ml-1 text-gray-900">{getTotalTokens(trace).toLocaleString()}</span>
            </div>
          </div>
        </div>
        
        {/* Two-panel layout */}
        <div className="flex h-full">
          {/* Left panel - Trace tree */}
          <div className="w-1/2 border-r border-gray-200 overflow-y-auto">
            <div className="p-4">
              <h3 className="text-sm font-medium text-gray-600 mb-4">Trace</h3>
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
          <div className="w-1/2">
            <SpanDetails span={selectedSpan} />
          </div>
        </div>
      </div>
    </div>
  );
};
