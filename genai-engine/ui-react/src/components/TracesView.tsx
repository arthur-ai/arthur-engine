

import React, { useState, useEffect } from "react";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/contexts/TaskContext";
import { TraceResponse } from "@/lib/api";
import { TraceDetailsPanel } from "./TraceDetailsPanel";

export const TracesView: React.FC = () => {
  const api = useApi();
  const { task } = useTask();
  const [traces, setTraces] = useState<TraceResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeFilter, setTimeFilter] = useState("Past 24 hours");
  const [currentPage, setCurrentPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [totalCount, setTotalCount] = useState(0);
  const [selectedTrace, setSelectedTrace] = useState<TraceResponse | null>(
    null
  );
  const [isDetailsPanelOpen, setIsDetailsPanelOpen] = useState(false);

  useEffect(() => {
    const fetchTraces = async () => {
      if (!api || !task) {
        setError("API client or task not available");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // Calculate time range based on filter
        const startTime = new Date();
        switch (timeFilter) {
          case "Past 5 minutes":
            startTime.setMinutes(startTime.getMinutes() - 5);
            break;
          case "Past 30 minutes":
            startTime.setMinutes(startTime.getMinutes() - 30);
            break;
          case "Past 1 hour":
            startTime.setHours(startTime.getHours() - 1);
            break;
          case "Past 24 hours":
            startTime.setDate(startTime.getDate() - 1);
            break;
          case "Past 7 days":
            startTime.setDate(startTime.getDate() - 7);
            break;
          case "Past 30 days":
            startTime.setDate(startTime.getDate() - 30);
            break;
        }

        const response = await api.v1.querySpansV1TracesQueryGet({
          task_ids: [task.id],
          page: currentPage,
          page_size: pageSize,
          sort: "desc",
          start_time: startTime.toISOString(),
        });

        const tracesData = response.data.traces || [];
        console.log("Raw traces data:", tracesData);
        if (tracesData.length > 0) {
          console.log("First trace start_time:", tracesData[0].start_time);
        }
        setTraces(tracesData);
        setTotalCount(response.data.count || 0);
      } catch (err) {
        console.error("Failed to fetch traces:", err);
        setError("Failed to load traces");
      } finally {
        setLoading(false);
      }
    };

    fetchTraces();
  }, [api, task, currentPage, pageSize, timeFilter]);

  const formatTimestamp = (timestamp: string) => {
    try {
      // Ensure the timestamp is treated as UTC by adding 'Z' if not present
      const utcTimestamp = timestamp.endsWith("Z")
        ? timestamp
        : timestamp + "Z";
      const date = new Date(utcTimestamp);
      if (isNaN(date.getTime())) {
        console.warn("Invalid timestamp:", timestamp);
        return "Invalid Date";
      }
      return date.toLocaleString("en-US", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false, // Use 24-hour format
        timeZoneName: "short", // Show timezone abbreviation
      });
    } catch (error) {
      console.error("Error formatting timestamp:", timestamp, error);
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

  const getSpanName = (trace: TraceResponse) => {
    if (trace.root_spans && trace.root_spans.length > 0) {
      return trace.root_spans[0].span_name || "Unknown";
    }
    return "Unknown";
  };

  const getInputContent = (trace: TraceResponse) => {
    if (trace.root_spans && trace.root_spans.length > 0) {
      const span = trace.root_spans[0];
      if (
        span.raw_data &&
        span.raw_data.attributes &&
        span.raw_data.attributes["input.value"]
      ) {
        return span.raw_data.attributes["input.value"];
      }
    }
    return "No input data";
  };

  const getOutputContent = (trace: TraceResponse) => {
    if (trace.root_spans && trace.root_spans.length > 0) {
      const span = trace.root_spans[0];
      if (
        span.raw_data &&
        span.raw_data.attributes &&
        span.raw_data.attributes["output.value"]
      ) {
        return span.raw_data.attributes["output.value"];
      }
    }
    return "No output data";
  };

  const getTokenCount = (trace: TraceResponse) => {
    if (trace.root_spans && trace.root_spans.length > 0) {
      const span = trace.root_spans[0];
      if (span.raw_data && span.raw_data.tokens) {
        return span.raw_data.tokens;
      }
    }
    return 0;
  };

  const truncateText = (text: string, maxLength: number = 100) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + "...";
  };

  const handleTraceClick = (trace: TraceResponse) => {
    setSelectedTrace(trace);
    setIsDetailsPanelOpen(true);
  };

  const handleCloseDetailsPanel = () => {
    setIsDetailsPanelOpen(false);
    setSelectedTrace(null);
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 mb-2">Error loading traces</div>
          <div className="text-gray-600">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-gray-50 flex flex-col">
      {/* Table Controls */}
      <div className="bg-white border-b border-gray-200 px-6 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">Traces: {totalCount}</span>
          </div>
          <div className="flex items-center space-x-4">
            <select
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value)}
              className="block w-40 px-3 py-2 border border-gray-300 rounded-md bg-white text-sm text-black focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="Past 5 minutes">Past 5 minutes</option>
              <option value="Past 30 minutes">Past 30 minutes</option>
              <option value="Past 1 hour">Past 1 hour</option>
              <option value="Past 24 hours">Past 24 hours</option>
              <option value="Past 7 days">Past 7 days</option>
              <option value="Past 30 days">Past 30 days</option>
            </select>
          </div>
        </div>
      </div>

      {/* Traces Table */}
      <div className="flex-1 overflow-auto">
        <div className="bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Input
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Output
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tokens
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {traces.map((trace) => (
                <tr
                  key={trace.trace_id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => handleTraceClick(trace)}
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatTimestamp(trace.start_time)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {getSpanName(trace)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 max-w-xs">
                    <div className="truncate">
                      {truncateText(getInputContent(trace))}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 max-w-xs">
                    <div className="truncate">
                      {truncateText(getOutputContent(trace))}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatDuration(trace.start_time, trace.end_time)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div className="flex items-center">
                      {getTokenCount(trace).toLocaleString()}
                      <svg
                        className="h-4 w-4 text-gray-400 ml-1"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="bg-white border-t border-gray-200 px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-700">Rows per page</span>
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="block px-2 py-1 border border-gray-300 rounded text-sm text-black focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-700">
              Page {currentPage + 1} of {Math.ceil(totalCount / pageSize)}
            </span>
            <div className="flex space-x-1">
              <button
                onClick={() => setCurrentPage(0)}
                disabled={currentPage === 0}
                className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
                  />
                </svg>
              </button>
              <button
                onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
                disabled={currentPage === 0}
                className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 19l-7-7 7-7"
                  />
                </svg>
              </button>
              <button
                onClick={() =>
                  setCurrentPage(
                    Math.min(
                      Math.ceil(totalCount / pageSize) - 1,
                      currentPage + 1
                    )
                  )
                }
                disabled={currentPage >= Math.ceil(totalCount / pageSize) - 1}
                className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </button>
              <button
                onClick={() =>
                  setCurrentPage(Math.ceil(totalCount / pageSize) - 1)
                }
                disabled={currentPage >= Math.ceil(totalCount / pageSize) - 1}
                className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 5l7 7-7 7M5 5l7 7-7 7"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Trace Details Panel */}
      <TraceDetailsPanel
        trace={selectedTrace}
        isOpen={isDetailsPanelOpen}
        onClose={handleCloseDetailsPanel}
      />
    </div>
  );
};
