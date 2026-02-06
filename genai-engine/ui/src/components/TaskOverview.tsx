import {
  TrendingUpOutlined,
  OpenInNewOutlined,
  BalanceOutlined,
} from "@mui/icons-material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import GeneratingTokensOutlinedIcon from "@mui/icons-material/GeneratingTokensOutlined";
import TollOutlinedIcon from "@mui/icons-material/TollOutlined";
import React, { useState } from "react";

import { BarChart } from "./charts/BarChart";
import { LineChart } from "./charts/LineChart";
import { TimeRange, TIME_RANGES } from "./traces/constants";

import { useTask } from "@/hooks/useTask";
import { useTaskOverviewMetrics } from "@/hooks/useTaskOverviewMetrics";

type TimeRangeButton = "Hour" | "Day" | "Week" | "Month" | "YTD" | "Year";

// Map UI buttons to API time ranges
const timeRangeMap: Record<TimeRangeButton, TimeRange> = {
  Hour: "1 day", // Closest to 1 hour
  Day: TIME_RANGES["1 day"],
  Week: TIME_RANGES["1 week"],
  Month: TIME_RANGES["1 month"],
  YTD: TIME_RANGES["1 year"], // Approximate as 1 year
  Year: TIME_RANGES["1 year"],
};

const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
};

const formatCurrency = (amount: number): string => {
  return `$${amount.toFixed(2)}`;
};

const formatCostAxisValue = (value: number): string => {
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  if (value >= 1) {
    return `$${value.toFixed(2)}`;
  }
  if (value >= 0.01) {
    return `$${value.toFixed(2)}`;
  }
  if (value >= 0.001) {
    return `$${value.toFixed(3)}`;
  }
  if (value >= 0.0001) {
    return `$${value.toFixed(4)}`;
  }
  if (value === 0) {
    return "$0";
  }
  return `$${value.toExponential(1)}`;
};

const formatPercentValue = (value: number): string => {
  return `${value.toFixed(1)}%`;
};

export const TaskOverview: React.FC = () => {
  const { task } = useTask();
  const [selectedTimeRangeButton, setSelectedTimeRangeButton] = useState<TimeRangeButton>("Week");

  const timeRange = timeRangeMap[selectedTimeRangeButton];

  const { data: metrics, isLoading, error } = useTaskOverviewMetrics({
    taskId: task?.id || "",
    timeRange,
  });

  if (!task) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const timeRanges: TimeRangeButton[] = ["Hour", "Day", "Week", "Month", "YTD", "Year"];

  // Get time range label for display
  const getTimeRangeLabel = (button: TimeRangeButton): string => {
    const labels: Record<TimeRangeButton, string> = {
      Hour: "Day",
      Day: "Day",
      Week: "Week",
      Month: "Month",
      YTD: "YTD",
      Year: "Year",
    };
    return labels[button];
  };

  const displayLabel = getTimeRangeLabel(selectedTimeRangeButton);

  // Determine if we should show time labels (for Hour and Day views)
  const showTimeLabels = selectedTimeRangeButton === "Hour" || selectedTimeRangeButton === "Day";

  // Prepare chart data with timestamps for axis labels
  const tracesChartData = metrics?.timeSeriesData.map((d) => ({ value: d.tracesCount, timestamp: d.timestamp })) || [];
  const tokensChartData = metrics?.timeSeriesData.map((d) => ({ value: d.tokens, timestamp: d.timestamp })) || [];
  const costChartData = metrics?.timeSeriesData.map((d) => ({ value: d.cost, timestamp: d.timestamp })) || [];
  const successRateChartData = metrics?.timeSeriesData.map((d) => ({ value: d.successRate, timestamp: d.timestamp })) || [];

  return (
    <div className="py-6 px-6 bg-gray-50">
      <div className="max-w-[1400px] mx-auto space-y-6">
        {/* Header Section */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Task Overview</h1>
            <p className="text-sm text-gray-500 mt-1">Key performance metrics at a glance</p>
          </div>
          <div className="inline-flex bg-white rounded-lg border border-gray-200 p-1">
            {timeRanges.map((range) => (
              <button
                key={range}
                onClick={() => setSelectedTimeRangeButton(range)}
                className={`px-4 py-1.5 text-sm transition-colors ${
                  selectedTimeRangeButton === range
                    ? "font-semibold text-gray-900"
                    : "font-normal text-gray-500 hover:text-gray-700"
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>

        {/* Show error state */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-800">Failed to load metrics. Please try again.</p>
          </div>
        )}

        {/* Metrics Cards Row */}
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
          {/* Traces Card */}
          <div className="bg-blue-50 rounded-lg p-5 border border-blue-100">
            <div className="flex items-center gap-2 text-blue-600 mb-2">
              <TrendingUpOutlined className="text-lg" />
              <span className="text-sm font-medium">Traces</span>
            </div>
            <div className="text-3xl font-bold text-gray-900">
              {isLoading ? (
                <div className="animate-pulse bg-gray-300 h-9 w-20 rounded"></div>
              ) : (
                formatNumber(metrics?.tracesCount || 0)
              )}
            </div>
            <div className="text-xs text-gray-600 mt-1">{displayLabel} total</div>
          </div>

          {/* Tokens Card */}
          <div className="bg-purple-50 rounded-lg p-5 border border-purple-100">
            <div className="flex items-center gap-2 text-purple-600 mb-2">
              <GeneratingTokensOutlinedIcon className="text-lg" />
              <span className="text-sm font-medium">Tokens</span>
            </div>
            <div className="text-3xl font-bold text-gray-900">
              {isLoading ? (
                <div className="animate-pulse bg-gray-300 h-9 w-20 rounded"></div>
              ) : (
                formatNumber(metrics?.totalTokens || 0)
              )}
            </div>
            <div className="text-xs text-gray-600 mt-1">{displayLabel} total</div>
          </div>

          {/* Cost Card */}
          <div className="bg-amber-50 rounded-lg p-5 border border-amber-100">
            <div className="flex items-center gap-2 text-amber-600 mb-2">
              <TollOutlinedIcon className="text-lg" />
              <span className="text-sm font-medium">Cost</span>
            </div>
            <div className="text-3xl font-bold text-gray-900">
              {isLoading ? (
                <div className="animate-pulse bg-gray-300 h-9 w-20 rounded"></div>
              ) : (
                formatCurrency(metrics?.totalCost || 0)
              )}
            </div>
            <div className="text-xs text-gray-600 mt-1">est. spend</div>
          </div>

          {/* Evals Card */}
          <div className="bg-teal-50 rounded-lg p-5 border border-teal-100">
            <div className="flex items-center gap-2 text-teal-600 mb-2">
              <BalanceOutlined className="text-lg" />
              <span className="text-sm font-medium">Evals</span>
            </div>
            <div className="text-3xl font-bold text-gray-900">
              {isLoading ? (
                <div className="animate-pulse bg-gray-300 h-9 w-20 rounded"></div>
              ) : (
                formatNumber(metrics?.evalsCount || 0)
              )}
            </div>
            <div className="text-xs text-gray-600 mt-1">{displayLabel} total</div>
          </div>

          {/* Success Rate Card */}
          <div className="bg-green-50 rounded-lg p-5 border border-green-100">
            <div className="flex items-center gap-2 text-green-600 mb-2">
              <CheckCircleIcon className="text-lg" />
              <span className="text-sm font-medium">Success Rate</span>
            </div>
            <div className="text-3xl font-bold text-gray-900">
              {isLoading ? (
                <div className="animate-pulse bg-gray-300 h-9 w-20 rounded"></div>
              ) : (
                `${metrics?.successRate.toFixed(1) || 0}%`
              )}
            </div>
            <div className="text-xs text-gray-600 mt-1">avg. rate</div>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid gap-6 grid-cols-1 lg:grid-cols-2">
          {/* Traces Chart */}
          <div className="bg-white rounded-lg shadow border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 text-blue-600">
                <TrendingUpOutlined className="text-lg" />
                <h3 className="text-base font-semibold text-gray-900">Traces</h3>
              </div>
            </div>
            <div className="p-6">
              {isLoading ? (
                <div className="h-64 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <div className="h-64">
                  <LineChart data={tracesChartData} color="#3B82F6" height={256} metricLabel="Traces" showTimeLabels={showTimeLabels} />
                </div>
              )}
            </div>
          </div>

          {/* Tokens Chart */}
          <div className="bg-white rounded-lg shadow border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 text-purple-600">
                <GeneratingTokensOutlinedIcon className="text-lg" />
                <h3 className="text-base font-semibold text-gray-900">Tokens</h3>
              </div>
            </div>
            <div className="p-6">
              {isLoading ? (
                <div className="h-64 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                </div>
              ) : (
                <div className="h-64">
                  <BarChart data={tokensChartData} color="#9333EA" height={256} metricLabel="Tokens" showTimeLabels={showTimeLabels} />
                </div>
              )}
            </div>
          </div>

          {/* Estimated Cost Chart */}
          <div className="bg-white rounded-lg shadow border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 text-amber-600">
                <TollOutlinedIcon className="text-lg" />
                <h3 className="text-base font-semibold text-gray-900">Estimated Cost</h3>
              </div>
            </div>
            <div className="p-6">
              {isLoading ? (
                <div className="h-64 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-600"></div>
                </div>
              ) : (
                <div className="h-64">
                  <LineChart data={costChartData} color="#F59E0B" height={256} formatValue={formatCostAxisValue} metricLabel="Cost" showTimeLabels={showTimeLabels} />
                </div>
              )}
            </div>
          </div>

          {/* Success Rate Chart */}
          <div className="bg-white rounded-lg shadow border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircleIcon className="text-lg" />
                <h3 className="text-base font-semibold text-gray-900">Success Rate</h3>
              </div>
            </div>
            <div className="p-6">
              {isLoading ? (
                <div className="h-64 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
                </div>
              ) : (
                <div className="h-64">
                  <LineChart data={successRateChartData} color="#10B981" height={256} formatValue={formatPercentValue} metricLabel="Success Rate" showTimeLabels={showTimeLabels} />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Bottom Banner */}
        <div className="bg-white rounded-lg border-2 border-dashed border-gray-300 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-medium text-gray-700">Need deeper analysis?</h3>
              <p className="text-sm text-gray-500 mt-1">
                Create custom dashboards with advanced filters, breakdowns, and export options in the Arthur platform.
              </p>
            </div>
            <button
              onClick={() => window.open("https://platform.arthur.ai/signup", "_blank", "noopener,noreferrer")}
              className="flex items-center gap-2 px-5 py-2.5 bg-white text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium whitespace-nowrap"
            >
              <span>Open in Arthur Platform</span>
              <OpenInNewOutlined className="text-base" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
