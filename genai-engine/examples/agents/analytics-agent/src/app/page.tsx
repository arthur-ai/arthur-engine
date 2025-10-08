"use client";

import { useCoAgent, useCopilotAction } from "@copilotkit/react-core";
import { CopilotKitCSSProperties, CopilotSidebar } from "@copilotkit/react-ui";
import { useState } from "react";
import { AgentState as AgentStateSchema } from "@/mastra/agents";
import { z } from "zod";
import {
  WeatherToolResult,
  TextToSqlToolResult,
  ExecuteSqlToolResult,
  GenerateGraphToolResult,
} from "@/mastra/tools";
import Prism from "prismjs";
import "prismjs/components/prism-sql";
import "prismjs/themes/prism-tomorrow.css";

type AgentState = z.infer<typeof AgentStateSchema>;

export default function CopilotKitPage() {
  const [themeColor, setThemeColor] = useState("#6366f1");

  // 🪁 Frontend Actions: https://docs.copilotkit.ai/guides/frontend-actions
  useCopilotAction({
    name: "setThemeColor",
    parameters: [
      {
        name: "themeColor",
        description: "The theme color to set. Make sure to pick nice colors.",
        required: true,
      },
    ],
    handler({ themeColor }) {
      setThemeColor(themeColor);
    },
  });

  //🪁 Generative UI: https://docs.copilotkit.ai/coagents/generative-ui
  useCopilotAction({
    name: "weatherTool",
    description: "Get the weather for a given location.",
    available: "frontend",
    parameters: [{ name: "location", type: "string", required: true }],
    render: ({ args, result, status }) => {
      return (
        <WeatherCard
          location={args.location}
          themeColor={themeColor}
          result={result}
          status={status}
        />
      );
    },
  });

  useCopilotAction({
    name: "textToSqlTool",
    description:
      "Convert natural language queries into PostgreSQL SQL statements.",
    available: "frontend",
    parameters: [{ name: "userQuery", type: "string", required: true }],
    render: ({ args, result, status }) => {
      return (
        <SqlCard
          userQuery={args.userQuery}
          themeColor={themeColor}
          result={result}
          status={status}
        />
      );
    },
  });

  useCopilotAction({
    name: "executeSqlTool",
    description: "Execute a PostgreSQL SQL query and return mock data results.",
    available: "frontend",
    parameters: [{ name: "sqlQuery", type: "string", required: true }],
    render: ({ result, status }) => {
      return (
        <SqlResultsCard
          themeColor={themeColor}
          result={result}
          status={status}
        />
      );
    },
  });

  useCopilotAction({
    name: "generateGraphTool",
    description: "Generate a graph visualization from SQL query results.",
    available: "frontend",
    parameters: [
      { name: "sqlResults", type: "object[]", required: true },
      { name: "sqlQuery", type: "string", required: true },
    ],
    render: ({ result, status }) => {
      return (
        <GraphCard themeColor={themeColor} result={result} status={status} />
      );
    },
  });

  useCopilotAction({
    name: "updateWorkingMemory",
    available: "frontend",
    render: ({ args }) => {
      return (
        <div
          style={{ backgroundColor: themeColor }}
          className="rounded-2xl max-w-md w-full text-white p-4"
        >
          <p>✨ Memory updated</p>
          <details className="mt-2">
            <summary className="cursor-pointer text-white">See updates</summary>
            <pre
              style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}
              className="overflow-x-auto text-sm bg-white/20 p-4 rounded-lg mt-2"
            >
              {JSON.stringify(args, null, 2)}
            </pre>
          </details>
        </div>
      );
    },
  });

  return (
    <main
      style={
        { "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties
      }
    >
      <YourMainContent themeColor={themeColor} />
      <CopilotSidebar
        clickOutsideToClose={false}
        defaultOpen={true}
        labels={{
          title: "Popup Assistant",
          initial:
            "👋 Hi, there! I'm a data analyst assistant. I can help you with your data analysis questions.",
        }}
      />
    </main>
  );
}

function YourMainContent({ themeColor }: { themeColor: string }) {
  // 🪁 Shared State: https://docs.copilotkit.ai/coagents/shared-state
  const { state, setState } = useCoAgent<AgentState>({
    name: "dataAnalystAgent",
    initialState: {
      proverbs: [
        "CopilotKit may be new, but its the best thing since sliced bread.",
      ],
    },
  });

  return (
    <div
      style={{ backgroundColor: themeColor }}
      className="h-screen w-screen flex justify-center items-center flex-col transition-colors duration-300"
    >
      <div className="bg-white/20 backdrop-blur-md p-8 rounded-2xl shadow-xl max-w-2xl w-full">
        <h1 className="text-4xl font-bold text-white mb-2 text-center">
          Proverbs
        </h1>
        <p className="text-gray-200 text-center italic mb-6">
          This is a demonstrative page, but it could be anything you want! 🪁
        </p>
        <hr className="border-white/20 my-6" />
        <div className="flex flex-col gap-3">
          {state.proverbs?.map((proverb, index) => (
            <div
              key={index}
              className="bg-white/15 p-4 rounded-xl text-white relative group hover:bg-white/20 transition-all"
            >
              <p className="pr-8">{proverb}</p>
              <button
                onClick={() =>
                  setState({
                    ...state,
                    proverbs: state.proverbs?.filter((_, i) => i !== index),
                  })
                }
                className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 transition-opacity 
                  bg-red-500 hover:bg-red-600 text-white rounded-full h-6 w-6 flex items-center justify-center"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
        {state.proverbs?.length === 0 && (
          <p className="text-center text-white/80 italic my-8">
            No proverbs yet. Ask the assistant to add some!
          </p>
        )}
      </div>
    </div>
  );
}

// Weather card component where the location and themeColor are based on what the agent
// sets via tool calls.
function WeatherCard({
  location,
  themeColor,
  result,
  status,
}: {
  location?: string;
  themeColor: string;
  result: WeatherToolResult;
  status: "inProgress" | "executing" | "complete";
}) {
  if (status !== "complete") {
    return (
      <div
        className="rounded-xl shadow-xl mt-6 mb-4 max-w-md w-full"
        style={{ backgroundColor: themeColor }}
      >
        <div className="bg-white/20 p-4 w-full">
          <p className="text-white animate-pulse">
            Loading weather for {location}...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{ backgroundColor: themeColor }}
      className="rounded-xl shadow-xl mt-6 mb-4 max-w-md w-full"
    >
      <div className="bg-white/20 p-4 w-full">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-white capitalize">
              {location}
            </h3>
            <p className="text-white">Current Weather</p>
          </div>
          <WeatherIcon conditions={result.conditions} />
        </div>

        <div className="mt-4 flex items-end justify-between">
          <div className="text-3xl font-bold text-white">
            <span className="">{result.temperature}° C</span>
            <span className="text-sm text-white/50">
              {" / "}
              {((result.temperature * 9) / 5 + 32).toFixed(1)}° F
            </span>
          </div>
          <div className="text-sm text-white">{result.conditions}</div>
        </div>

        <div className="mt-4 pt-4 border-t border-white">
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-white text-xs">Humidity</p>
              <p className="text-white font-medium">{result.humidity}%</p>
            </div>
            <div>
              <p className="text-white text-xs">Wind</p>
              <p className="text-white font-medium">{result.windSpeed} mph</p>
            </div>
            <div>
              <p className="text-white text-xs">Feels Like</p>
              <p className="text-white font-medium">{result.feelsLike}°</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function WeatherIcon({ conditions }: { conditions: string }) {
  if (!conditions) return null;

  if (
    conditions.toLowerCase().includes("clear") ||
    conditions.toLowerCase().includes("sunny")
  ) {
    return <SunIcon />;
  }

  if (
    conditions.toLowerCase().includes("rain") ||
    conditions.toLowerCase().includes("drizzle") ||
    conditions.toLowerCase().includes("snow") ||
    conditions.toLowerCase().includes("thunderstorm")
  ) {
    return <RainIcon />;
  }

  if (
    conditions.toLowerCase().includes("fog") ||
    conditions.toLowerCase().includes("cloud") ||
    conditions.toLowerCase().includes("overcast")
  ) {
    return <CloudIcon />;
  }

  return <CloudIcon />;
}

// Simple sun icon for the weather card
function SunIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-14 h-14 text-yellow-200"
    >
      <circle cx="12" cy="12" r="5" />
      <path
        d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
        strokeWidth="2"
        stroke="currentColor"
      />
    </svg>
  );
}

function RainIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-14 h-14 text-blue-200"
    >
      {/* Cloud */}
      <path
        d="M7 15a4 4 0 0 1 0-8 5 5 0 0 1 10 0 4 4 0 0 1 0 8H7z"
        fill="currentColor"
        opacity="0.8"
      />
      {/* Rain drops */}
      <path
        d="M8 18l2 4M12 18l2 4M16 18l2 4"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}

function CloudIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-14 h-14 text-gray-200"
    >
      <path
        d="M7 15a4 4 0 0 1 0-8 5 5 0 0 1 10 0 4 4 0 0 1 0 8H7z"
        fill="currentColor"
      />
    </svg>
  );
}

// SQL card component for displaying generated SQL with syntax highlighting
function SqlCard({
  userQuery,
  themeColor,
  result,
  status,
}: {
  userQuery?: string;
  themeColor: string;
  result: TextToSqlToolResult;
  status: "inProgress" | "executing" | "complete";
}) {
  if (status !== "complete") {
    return (
      <div
        className="rounded-xl shadow-xl mt-6 mb-4 max-w-2xl w-full"
        style={{ backgroundColor: themeColor }}
      >
        <div className="bg-white/20 p-4 w-full">
          <p className="text-white animate-pulse">
            Generating SQL for: &ldquo;{userQuery}&rdquo;...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{ backgroundColor: themeColor }}
      className="rounded-xl shadow-xl mt-6 mb-4 max-w-2xl w-full"
    >
      <div className="bg-white/20 p-4 w-full">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-xl font-bold text-white">
              Generated SQL Query
            </h3>
            <p className="text-white/80 text-sm">
              Query: &ldquo;{userQuery}&rdquo;
            </p>
          </div>
          <DatabaseIcon />
        </div>

        <div className="bg-gray-900 rounded-lg p-4 mb-3">
          <pre className="text-sm whitespace-pre-wrap overflow-x-auto">
            <code
              className="language-sql"
              dangerouslySetInnerHTML={{
                __html: Prism.highlight(
                  result.sqlQuery,
                  Prism.languages.sql,
                  "sql"
                ),
              }}
            />
          </pre>
        </div>

        <div className="bg-white/10 rounded-lg p-3">
          <p className="text-white text-sm">
            <span className="font-semibold">Explanation:</span>{" "}
            {result.explanation}
          </p>
        </div>
      </div>
    </div>
  );
}

// Database icon for the SQL card
function DatabaseIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-8 h-8 text-white/80"
    >
      <path d="M12 2C6.48 2 2 3.79 2 6v12c0 2.21 4.48 4 10 4s10-1.79 10-4V6c0-2.21-4.48-4-10-4zM4 6c0-.55 2.4-2 8-2s8 1.45 8 2v2c0 .55-2.4 2-8 2s-8-1.45-8-2V6zm0 4c0-.55 2.4-2 8-2s8 1.45 8 2v2c0 .55-2.4 2-8 2s-8-1.45-8-2v-2zm0 4c0-.55 2.4-2 8-2s8 1.45 8 2v2c0 .55-2.4 2-8 2s-8-1.45-8-2v-2z" />
    </svg>
  );
}

// SQL Results card component for displaying query execution results
function SqlResultsCard({
  themeColor,
  result,
  status,
}: {
  themeColor: string;
  result: ExecuteSqlToolResult;
  status: "inProgress" | "executing" | "complete";
}) {
  if (status !== "complete") {
    return (
      <div
        className="rounded-xl shadow-xl mt-6 mb-4 max-w-4xl w-full"
        style={{ backgroundColor: themeColor }}
      >
        <div className="bg-white/20 p-4 w-full">
          <p className="text-white animate-pulse">Executing SQL query...</p>
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
            <h3 className="text-xl font-bold text-white">SQL Query Results</h3>
            <p className="text-white/80 text-sm">Query executed successfully</p>
          </div>
          <DatabaseIcon />
        </div>

        <div className="bg-gray-900 rounded-lg p-4 mb-3">
          <pre className="text-sm whitespace-pre-wrap overflow-x-auto">
            <code
              className="language-sql"
              dangerouslySetInnerHTML={{
                __html: Prism.highlight(
                  result.query,
                  Prism.languages.sql,
                  "sql"
                ),
              }}
            />
          </pre>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-3">
          <div className="bg-white/10 rounded-lg p-3 text-center">
            <p className="text-white text-sm">Rows Returned</p>
            <p className="text-white font-bold text-lg">{result.rowCount}</p>
          </div>
          <div className="bg-white/10 rounded-lg p-3 text-center">
            <p className="text-white text-sm">Execution Time</p>
            <p className="text-white font-bold text-lg">
              {result.executionTime}ms
            </p>
          </div>
          <div className="bg-white/10 rounded-lg p-3 text-center">
            <p className="text-white text-sm">Status</p>
            <p className="text-green-400 font-bold text-lg">✓ Success</p>
          </div>
        </div>

        {result.data && result.data.length > 0 && (
          <div className="bg-white/10 rounded-lg p-3">
            <h4 className="text-white font-semibold mb-2">Query Results:</h4>
            <div className="bg-gray-900 rounded overflow-hidden max-h-64 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-800 sticky top-0">
                  <tr>
                    {Object.keys(result.data[0]).map((column, index) => (
                      <th
                        key={index}
                        className="px-3 py-2 text-left text-blue-300 font-semibold border-b border-gray-700"
                      >
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.data.map((row, rowIndex) => (
                    <tr
                      key={rowIndex}
                      className={`${
                        rowIndex % 2 === 0 ? "bg-gray-900" : "bg-gray-850"
                      } hover:bg-gray-700 transition-colors`}
                    >
                      {Object.values(row).map((value, colIndex) => (
                        <td
                          key={colIndex}
                          className="px-3 py-2 text-white border-b border-gray-700"
                        >
                          {typeof value === "object" && value !== null
                            ? JSON.stringify(value)
                            : String(value)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Graph card component for displaying chart visualizations
function GraphCard({
  themeColor,
  result,
  status,
}: {
  themeColor: string;
  result: GenerateGraphToolResult;
  status: "inProgress" | "executing" | "complete";
}) {
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
