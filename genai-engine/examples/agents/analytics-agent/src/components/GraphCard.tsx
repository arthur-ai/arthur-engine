import { GenerateGraphToolResult } from "@/mastra/tools";

// Helper function to check if the result is an error
function isErrorResult(
  result: unknown
): result is { error: true; message: string } {
  if (!result || typeof result !== "object") {
    return false;
  }

  const obj = result as Record<string, unknown>;
  return (
    "error" in obj &&
    obj.error === true &&
    "message" in obj &&
    typeof obj.message === "string"
  );
}

interface GraphCardProps {
  themeColor: string;
  result: GenerateGraphToolResult | null;
  status: "inProgress" | "executing" | "complete";
}

export function GraphCard({ themeColor, result, status }: GraphCardProps) {
  // Handle error state - when result contains an error
  if (status === "complete" && result && isErrorResult(result)) {
    return (
      <div
        className="rounded-xl shadow-xl mt-6 mb-4 max-w-4xl w-full"
        style={{ backgroundColor: "#ef4444" }} // Red background for errors
      >
        <div className="bg-white/20 p-4 w-full">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-xl font-bold text-white">
                Graph Generation Failed
              </h3>
              <p className="text-white/80 text-sm">
                Unable to generate visualization
              </p>
            </div>
            <ErrorIcon />
          </div>
          <div className="bg-white/10 rounded-lg p-3">
            <p className="text-white text-sm">
              <span className="font-semibold">Error:</span> {result.message}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Handle loading states
  if (status !== "complete") {
    return (
      <div
        className="rounded-xl shadow-xl mt-6 mb-4 max-w-4xl w-full"
        style={{ backgroundColor: themeColor }}
      >
        <div className="bg-white/20 p-4 w-full">
          <p className="text-white animate-pulse">Generating graph...</p>
        </div>
      </div>
    );
  }

  // Handle case where status is complete but no result
  if (!result) {
    return (
      <div
        className="rounded-xl shadow-xl mt-6 mb-4 max-w-4xl w-full"
        style={{ backgroundColor: "#ef4444" }} // Red background for errors
      >
        <div className="bg-white/20 p-4 w-full">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-xl font-bold text-white">
                Graph Generation Failed
              </h3>
              <p className="text-white/80 text-sm">
                Unable to generate visualization
              </p>
            </div>
            <ErrorIcon />
          </div>
          <div className="bg-white/10 rounded-lg p-3">
            <p className="text-white text-sm">
              <span className="font-semibold">Error:</span> No result returned
              from the graph generation tool.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{ backgroundColor: themeColor }}
      className="rounded-xl shadow-xl mt-6 mb-4 max-w-4xl w-full"
    >
      <div className="bg-white/20 p-4 w-full">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-xl font-bold text-white">Data Visualization</h3>
            <p className="text-white/80 text-sm">{result.title}</p>
          </div>
          <ChartIcon />
        </div>

        <div className="bg-white/10 rounded-lg p-3 mb-3">
          <p className="text-white text-sm">
            <span className="font-semibold">Description:</span>{" "}
            {result.description}
          </p>
        </div>

        <div className="bg-white rounded-lg p-4 mb-3">
          <h4 className="text-gray-800 font-semibold mb-3 text-center">
            {result.title}
          </h4>
          <div className="h-64 flex items-center justify-center">
            <SimpleChart
              graphType={result.graphType}
              data={result.data}
              xAxis={result.xAxis}
              yAxis={result.yAxis}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

// Chart icon for the graph card
function ChartIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-8 h-8 text-white/80"
    >
      <path d="M3 13h2v8H3v-8zm4-6h2v14H7V7zm4-4h2v18h-2V3zm4 8h2v10h-2V11zm4-4h2v14h-2V7z" />
    </svg>
  );
}

// Error icon for error states
function ErrorIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-8 h-8 text-white/80"
    >
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
    </svg>
  );
}

// Simple SVG-based chart component
function SimpleChart({
  graphType,
  data,
  xAxis,
  yAxis,
}: {
  graphType: string;
  data: Record<string, unknown>[];
  xAxis: string;
  yAxis: string;
}) {
  const width = 400;
  const height = 200;
  const padding = 40;

  if (!data || data.length === 0) {
    return (
      <div className="text-gray-500 text-center">
        No data available for visualization
      </div>
    );
  }

  // Extract values for y axis
  const yValues = data.map((d) => Number(d[yAxis]) || 0);

  const maxY = Math.max(...yValues);
  const minY = Math.min(...yValues);
  const yRange = maxY - minY || 1;

  const chartWidth = width - 2 * padding;
  const chartHeight = height - 2 * padding;

  if (graphType === "bar") {
    const barWidth = (chartWidth / data.length) * 0.8;
    const barSpacing = chartWidth / data.length;

    return (
      <svg
        width={width}
        height={height}
        className="border border-gray-200 rounded"
      >
        {/* Y-axis */}
        <line
          x1={padding}
          y1={padding}
          x2={padding}
          y2={height - padding}
          stroke="#374151"
          strokeWidth="2"
        />
        {/* X-axis */}
        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
          stroke="#374151"
          strokeWidth="2"
        />

        {/* Bars */}
        {data.map((item, index) => {
          const barHeight =
            ((Number(item[yAxis]) - minY) / yRange) * chartHeight;
          const x = padding + index * barSpacing + (barSpacing - barWidth) / 2;
          const y = height - padding - barHeight;

          return (
            <g key={index}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                fill="#3B82F6"
                className="hover:fill-blue-600 transition-colors"
              />
              <text
                x={x + barWidth / 2}
                y={height - padding + 15}
                textAnchor="middle"
                className="text-xs fill-gray-600"
                transform={`rotate(-45 ${x + barWidth / 2} ${height - padding + 15})`}
              >
                {String(item[xAxis]).substring(0, 10)}
              </text>
            </g>
          );
        })}
      </svg>
    );
  }

  if (graphType === "line") {
    const pointSpacing = chartWidth / (data.length - 1);
    const points = data
      .map((item, index) => {
        const x = padding + index * pointSpacing;
        const y =
          height -
          padding -
          ((Number(item[yAxis]) - minY) / yRange) * chartHeight;
        return `${x},${y}`;
      })
      .join(" ");

    return (
      <svg
        width={width}
        height={height}
        className="border border-gray-200 rounded"
      >
        {/* Y-axis */}
        <line
          x1={padding}
          y1={padding}
          x2={padding}
          y2={height - padding}
          stroke="#374151"
          strokeWidth="2"
        />
        {/* X-axis */}
        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
          stroke="#374151"
          strokeWidth="2"
        />

        {/* Line */}
        <polyline
          points={points}
          fill="none"
          stroke="#3B82F6"
          strokeWidth="3"
        />

        {/* Points */}
        {data.map((item, index) => {
          const x = padding + index * pointSpacing;
          const y =
            height -
            padding -
            ((Number(item[yAxis]) - minY) / yRange) * chartHeight;

          return (
            <g key={index}>
              <circle cx={x} cy={y} r="4" fill="#3B82F6" />
              <text
                x={x}
                y={height - padding + 15}
                textAnchor="middle"
                className="text-xs fill-gray-600"
                transform={`rotate(-45 ${x} ${height - padding + 15})`}
              >
                {String(item[xAxis]).substring(0, 10)}
              </text>
            </g>
          );
        })}
      </svg>
    );
  }

  if (graphType === "pie") {
    const total = yValues.reduce((sum, val) => sum + val, 0);
    let currentAngle = 0;
    const radius = Math.min(chartWidth, chartHeight) / 2 - 20;
    const centerX = width / 2;
    const centerY = height / 2;

    const colors = [
      "#3B82F6",
      "#EF4444",
      "#10B981",
      "#F59E0B",
      "#8B5CF6",
      "#EC4899",
    ];

    return (
      <svg
        width={width}
        height={height}
        className="border border-gray-200 rounded"
      >
        {data.map((item, index) => {
          const angle = (Number(item[yAxis]) / total) * 360;
          const startAngle = currentAngle;
          const endAngle = currentAngle + angle;

          const x1 =
            centerX + radius * Math.cos(((startAngle - 90) * Math.PI) / 180);
          const y1 =
            centerY + radius * Math.sin(((startAngle - 90) * Math.PI) / 180);
          const x2 =
            centerX + radius * Math.cos(((endAngle - 90) * Math.PI) / 180);
          const y2 =
            centerY + radius * Math.sin(((endAngle - 90) * Math.PI) / 180);

          const largeArcFlag = angle > 180 ? 1 : 0;
          const pathData = [
            `M ${centerX} ${centerY}`,
            `L ${x1} ${y1}`,
            `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2}`,
            "Z",
          ].join(" ");

          currentAngle += angle;

          return (
            <g key={index}>
              <path
                d={pathData}
                fill={colors[index % colors.length]}
                className="hover:opacity-80 transition-opacity"
              />
              <text
                x={
                  centerX +
                  (radius + 20) *
                    Math.cos(((startAngle + angle / 2 - 90) * Math.PI) / 180)
                }
                y={
                  centerY +
                  (radius + 20) *
                    Math.sin(((startAngle + angle / 2 - 90) * Math.PI) / 180)
                }
                textAnchor="middle"
                className="text-xs fill-gray-700"
              >
                {String(item[xAxis]).substring(0, 8)}
              </text>
            </g>
          );
        })}
      </svg>
    );
  }

  // Default fallback
  return (
    <div className="text-gray-500 text-center">
      Chart type &ldquo;{graphType}&rdquo; not yet implemented
    </div>
  );
}
