"use client";

import { useCopilotAction, useCopilotChat } from "@copilotkit/react-core";
import { CopilotKitCSSProperties, CopilotChat } from "@copilotkit/react-ui";
import { useState } from "react";
import { WeatherCard, SqlCard, SqlResultsCard, GraphCard, useTelemetry } from "@/components";


export default function CopilotKitPage() {
  const [themeColor, setThemeColor] = useState("#6366f1");
  const { reset } = useCopilotChat();
  const { newSession } = useTelemetry();

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
      className="h-screen w-screen bg-gray-50"
    >
      {/* App Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm"
                style={{ backgroundColor: themeColor }}
              >
                DA
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  Inventory Data Analyst Agent
                </h1>
                <p className="text-sm text-gray-500">
                  AI-powered analytics and insights
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => {
                  reset();
                  newSession();
                }}
                className="px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors duration-200 hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                style={{ backgroundColor: themeColor }}
                title="Start a new conversation thread"
              >
                New Thread
              </button>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-sm text-gray-600">Online</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="h-[calc(100vh-80px)] flex justify-center items-center">
        <div className="w-full max-w-6xl h-full flex flex-col">
          <CopilotChat
            labels={{
              title: "Data Analyst Assistant",
              initial:
                "👋 Hi, there! I'm a data analyst assistant. I can help you with your data analysis questions.",
            }}
            className="h-full w-full"
          />
        </div>
      </div>
    </main>
  );
}
