import React, { useState } from "react";

interface DataPoint {
  value: number;
  label?: string;
  timestamp?: string;
}

interface LineChartProps {
  data: DataPoint[];
  color?: string;
  height?: number;
  formatValue?: (value: number) => string;
  metricLabel?: string;
  showTimeLabels?: boolean;
}

interface TooltipData {
  x: number;
  y: number;
  value: number;
  label: string;
}

const defaultFormatYAxisValue = (value: number): string => {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  if (value >= 1) {
    return value.toFixed(0);
  }
  // For decimal values less than 1
  return value.toFixed(2);
};

const formatXAxisLabel = (timestamp: string, index: number, total: number, showTimeLabels: boolean): string => {
  const date = new Date(timestamp);

  // For hour/day views, show time labels
  if (showTimeLabels) {
    // Show every other label for better readability
    if (index % 2 === 0 || index === total - 1) {
      return date.toLocaleTimeString("en-US", { hour: "numeric", hour12: true });
    }
    return "";
  }

  // Show day of week for very small datasets
  if (total <= 7) {
    return date.toLocaleDateString("en-US", { weekday: "short" });
  }

  // For small datasets (less than 15 points), show all labels
  if (total <= 15) {
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  // For larger datasets, show labels at intervals
  const interval = Math.ceil(total / 7); // Show approximately 7 labels
  if (index % interval === 0 || index === total - 1) {
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  return "";
};

export const LineChart: React.FC<LineChartProps> = ({
  data,
  color = "#3B82F6",
  height = 200,
  formatValue = defaultFormatYAxisValue,
  metricLabel = "Value",
  showTimeLabels = false
}) => {
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400 text-sm">
        No data available
      </div>
    );
  }

  const dataMaxValue = Math.max(...data.map((d) => d.value));
  const dataMinValue = Math.min(...data.map((d) => d.value));

  // Calculate a nice max value for the Y-axis
  const calculateNiceMax = (value: number): number => {
    if (value === 0) return 10;

    const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
    const normalized = value / magnitude;

    let niceValue;
    if (normalized <= 1) niceValue = 1;
    else if (normalized <= 2) niceValue = 2;
    else if (normalized <= 5) niceValue = 5;
    else niceValue = 10;

    return niceValue * magnitude;
  };

  const maxValue = calculateNiceMax(dataMaxValue);
  const minValue = Math.min(dataMinValue, 0);
  const range = maxValue - minValue || 1;

  // Calculate nice Y-axis ticks
  const yAxisTicks = 5;
  const yAxisValues = Array.from({ length: yAxisTicks }, (_, i) => {
    return minValue + (range * i) / (yAxisTicks - 1);
  }).reverse();

  const paddingLeft = 50;
  const paddingRight = 20;
  const paddingTop = 20;
  const paddingBottom = 40;
  const width = 600;
  const chartHeight = height - paddingTop - paddingBottom;
  const chartWidth = width - paddingLeft - paddingRight;

  // Calculate points for the line
  const points = data.map((point, index) => {
    const x = paddingLeft + (data.length === 1 ? chartWidth / 2 : (index / (data.length - 1)) * chartWidth);
    const y = paddingTop + chartHeight - ((point.value - minValue) / range) * chartHeight;
    return { x, y };
  });

  // Create path for the line
  const linePath = points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");

  // Create path for the area under the line
  const areaPath =
    linePath +
    ` L ${points[points.length - 1].x} ${height - paddingBottom} L ${points[0].x} ${height - paddingBottom} Z`;

  const handleMouseEnter = (point: DataPoint, x: number, y: number, index: number) => {
    const date = point.timestamp ? new Date(point.timestamp) : null;
    let label = "";
    if (date) {
      if (showTimeLabels) {
        label = date.toLocaleString("en-US", {
          month: "short",
          day: "numeric",
          hour: "numeric",
          hour12: true
        });
      } else {
        label = date.toLocaleDateString("en-US", { weekday: "short" });
      }
    }
    setTooltip({ x, y, value: point.value, label });
  };

  const handleMouseLeave = () => {
    setTooltip(null);
  };

  return (
    <div className="relative w-full h-full">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
        {/* Y-axis grid lines and labels */}
      {yAxisValues.map((value, index) => {
        const y = paddingTop + (index * chartHeight) / (yAxisTicks - 1);
        return (
          <g key={`y-${index}`}>
            {/* Grid line */}
            <line
              x1={paddingLeft}
              y1={y}
              x2={width - paddingRight}
              y2={y}
              stroke="#E5E7EB"
              strokeWidth="1"
            />
            {/* Y-axis label */}
            <text
              x={paddingLeft - 10}
              y={y + 4}
              textAnchor="end"
              fill="#6B7280"
              fontSize="11"
              fontFamily="system-ui, -apple-system, sans-serif"
            >
              {formatValue(value)}
            </text>
          </g>
        );
      })}

      {/* X-axis labels */}
      {data.map((point, index) => {
        const label = point.timestamp ? formatXAxisLabel(point.timestamp, index, data.length, showTimeLabels) : "";
        if (!label) return null;

        const x = paddingLeft + (data.length === 1 ? chartWidth / 2 : (index / (data.length - 1)) * chartWidth);
        return (
          <text
            key={`x-${index}`}
            x={x}
            y={height - paddingBottom + 20}
            textAnchor="middle"
            fill="#6B7280"
            fontSize="11"
            fontFamily="system-ui, -apple-system, sans-serif"
          >
            {label}
          </text>
        );
      })}

      {/* X-axis line */}
      <line
        x1={paddingLeft}
        y1={height - paddingBottom}
        x2={width - paddingRight}
        y2={height - paddingBottom}
        stroke="#E5E7EB"
        strokeWidth="1"
      />

      {/* Y-axis line */}
      <line
        x1={paddingLeft}
        y1={paddingTop}
        x2={paddingLeft}
        y2={height - paddingBottom}
        stroke="#E5E7EB"
        strokeWidth="1"
      />

      {/* Area under the line */}
      <path d={areaPath} fill={color} fillOpacity="0.1" />

      {/* Line */}
      <path d={linePath} stroke={color} strokeWidth="2" fill="none" />

      {/* Data points */}
      {points.map((point, index) => (
        <g key={index}>
          <circle
            cx={point.x}
            cy={point.y}
            r="3"
            fill={color}
            className="transition-all"
          />
          <circle
            cx={point.x}
            cy={point.y}
            r="8"
            fill="transparent"
            className="cursor-pointer"
            onMouseEnter={() => handleMouseEnter(data[index], point.x, point.y, index)}
            onMouseLeave={handleMouseLeave}
          />
        </g>
      ))}
    </svg>

    {/* Tooltip */}
    {tooltip && (
      <div
        className="absolute bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 pointer-events-none z-10 whitespace-nowrap"
        style={{
          left: `${(tooltip.x / width) * 100}%`,
          top: `${(tooltip.y / height) * 100}%`,
          transform: "translate(-50%, -120%)",
        }}
      >
        <div className="text-xs font-medium text-gray-900 mb-0.5">{tooltip.label}</div>
        <div className="text-sm">
          <span className="font-semibold" style={{ color }}>{metricLabel}:</span>
          <span className="font-semibold text-gray-900 ml-1">{formatValue(tooltip.value)}</span>
        </div>
      </div>
    )}
  </div>
  );
};
