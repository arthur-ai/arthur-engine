"use client";

import { useCopilotAction } from "@copilotkit/react-core";
import { CopilotKitCSSProperties, CopilotChat } from "@copilotkit/react-ui";
import { useState } from "react";
import { WeatherCard, SqlCard, SqlResultsCard, GraphCard } from "@/components";

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
      className="h-screen w-screen flex justify-center items-center bg-gray-50"
    >
      <div className="w-full max-w-4xl h-full flex flex-col">
        <CopilotChat
          labels={{
            title: "Data Analyst Assistant",
            initial:
              "👋 Hi, there! I'm a data analyst assistant. I can help you with your data analysis questions.",
          }}
          className="h-full w-full"
        />
      </div>
    </main>
  );
}
