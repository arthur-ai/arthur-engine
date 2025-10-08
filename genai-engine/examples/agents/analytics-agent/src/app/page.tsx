"use client";

import { useCoAgent, useCopilotAction } from "@copilotkit/react-core";
import { CopilotKitCSSProperties, CopilotSidebar } from "@copilotkit/react-ui";
import { useState } from "react";
import { AgentState as AgentStateSchema } from "@/mastra/agents";
import { z } from "zod";
import { WeatherCard, SqlCard, SqlResultsCard, GraphCard } from "@/components";

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
