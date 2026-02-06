import React, { useState } from "react";

interface DataPoint {
  value: number;
  label?: string;
  timestamp?: string;
}

interface BarChartProps {
  data: DataPoint[];
  color?: string;
  height?: number;
  metricLabel?: string;
  xLabelFormat?: "time" | "date" | "month";
  tickStep?: number;
}

interface TooltipData {
  x: number;
  y: number;
  value: number;
  label: string;
}

const formatYAxisValue = (value: number): string => {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toFixed(0);
};

const formatXAxisLabel = (
  timestamp: string,
  index: number,
  tickStep: number,
  xLabelFormat: "time" | "date" | "month"
): string => {
  const date = new Date(timestamp);

  // Only show labels at the specified tick step
  if (index % tickStep !== 0) {
    return "";
  }

  // Format based on xLabelFormat
  switch (xLabelFormat) {
    case "time":
      return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
    case "date":
      return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    case "month":
      return date.toLocaleDateString("en-US", { month: "short" });
    default:
      return "";
  }
};

export const BarChart: React.FC<BarChartProps> = ({ data, color = "#9333EA", height = 200, metricLabel = "Value", xLabelFormat = "date", tickStep = 1 }) => {
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400 text-sm">
        No data available
      </div>
    );
  }

  const dataMaxValue = Math.max(...data.map((d) => d.value));

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

  // Calculate nice Y-axis ticks
  const yAxisTicks = 5;
  const yAxisValues = Array.from({ length: yAxisTicks }, (_, i) => {
    return (maxValue * i) / (yAxisTicks - 1);
  }).reverse();

  const paddingLeft = 50;
  const paddingRight = 20;
  const paddingTop = 20;
  const paddingBottom = 40;
  const width = 600;
  const chartHeight = height - paddingTop - paddingBottom;
  const chartWidth = width - paddingLeft - paddingRight;

  const barWidth = Math.max(chartWidth / data.length - 4, 8);
  const barSpacing = chartWidth / data.length;

  const handleMouseEnter = (point: DataPoint, x: number, y: number, index: number) => {
    const date = point.timestamp ? new Date(point.timestamp) : null;
    let label = "";
    if (date) {
      // Format tooltip based on xLabelFormat
      if (xLabelFormat === "time") {
        label = date.toLocaleString("en-US", {
          month: "short",
          day: "numeric",
          hour: "numeric",
          minute: "2-digit",
          hour12: true
        });
      } else if (xLabelFormat === "date") {
        label = date.toLocaleDateString("en-US", {
          weekday: "short",
          month: "short",
          day: "numeric"
        });
      } else if (xLabelFormat === "month") {
        label = date.toLocaleDateString("en-US", {
          month: "long",
          year: "numeric"
        });
      }
    }
    setTooltip({ x: x + barWidth / 2, y, value: point.value, label });
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
              {formatYAxisValue(value)}
            </text>
          </g>
        );
      })}

      {/* X-axis labels */}
      {data.map((point, index) => {
        const label = point.timestamp ? formatXAxisLabel(point.timestamp, index, tickStep, xLabelFormat) : "";
        if (!label) return null;

        const x = paddingLeft + index * barSpacing + barSpacing / 2;
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

      {/* Bars */}
      {data.map((point, index) => {
        const x = paddingLeft + index * barSpacing + (barSpacing - barWidth) / 2;
        const barHeight = (point.value / maxValue) * chartHeight;
        const y = paddingTop + chartHeight - barHeight;

        return (
          <rect
            key={index}
            x={x}
            y={y}
            width={barWidth}
            height={barHeight}
            fill={color}
            rx="2"
            className="cursor-pointer transition-opacity hover:opacity-80"
            onMouseEnter={() => handleMouseEnter(point, x, y, index)}
            onMouseLeave={handleMouseLeave}
          />
        );
      })}
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
          <span className="font-semibold text-gray-900 ml-1">{formatYAxisValue(tooltip.value)}</span>
        </div>
      </div>
    )}
  </div>
  );
};
