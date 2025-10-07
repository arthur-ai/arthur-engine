"use client";

import { useCoAgent, useCopilotAction } from "@copilotkit/react-core";
import { CopilotKitCSSProperties, CopilotSidebar } from "@copilotkit/react-ui";
import { useState } from "react";
import { AgentState as AgentStateSchema } from "@/mastra/agents";
import { z } from "zod";
import { WeatherToolResult } from "@/mastra/tools";

type AgentState = z.infer<typeof AgentStateSchema>;

export default function CopilotKitPage() {
  const [themeColor, setThemeColor] = useState("#6366f1");

  // 🪁 Frontend Actions: https://docs.copilotkit.ai/guides/frontend-actions
  useCopilotAction({
    name: "setThemeColor",
    parameters: [{
      name: "themeColor",
      description: "The theme color to set. Make sure to pick nice colors.",
      required: true, 
    }],
    handler({ themeColor }) {
      setThemeColor(themeColor);
    },
  });

  return (
    <main style={{ "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties}>
      <YourMainContent themeColor={themeColor} />
      <CopilotSidebar
        clickOutsideToClose={false}
        defaultOpen={true}
        labels={{
          title: "Popup Assistant",
          initial: "👋 Hi, there! You're chatting with an agent. This agent comes with a few tools to get you started.\n\nFor example you can try:\n- **Frontend Tools**: \"Set the theme to orange\"\n- **Shared State**: \"Write a proverb about AI\"\n- **Generative UI**: \"Get the weather in SF\"\n\nAs you interact with the agent, you'll see the UI update in real-time to reflect the agent's **state**, **tool calls**, and **progress**."
        }}
      />
    </main>
  );
}

function YourMainContent({ themeColor }: { themeColor: string }) {
  // 🪁 Shared State: https://docs.copilotkit.ai/coagents/shared-state
  const {state, setState} = useCoAgent<AgentState>({
    name: "weatherAgent",
    initialState: {
      proverbs: [
        "CopilotKit may be new, but its the best thing since sliced bread.",
      ],
    },
  })

  //🪁 Generative UI: https://docs.copilotkit.ai/coagents/generative-ui
  useCopilotAction({
    name: "weatherTool",
    description: "Get the weather for a given location.",
    available: "frontend",
    parameters: [
      { name: "location", type: "string", required: true },
    ],
    render: ({ args, result, status }) => {
      return <WeatherCard 
        location={args.location} 
        themeColor={themeColor} 
        result={result} 
        status={status}
      />
    },
  });

  useCopilotAction({
    name: "updateWorkingMemory",
    available: "frontend",
    render: ({ args }) => {
      return <div style={{ backgroundColor: themeColor }} className="rounded-2xl max-w-md w-full text-white p-4">
        <p>✨ Memory updated</p>
        <details className="mt-2">
          <summary className="cursor-pointer text-white">See updates</summary>
          <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }} className="overflow-x-auto text-sm bg-white/20 p-4 rounded-lg mt-2">
            {JSON.stringify(args, null, 2)}
          </pre>
        </details>
      </div>
    },
  });

  return (
    <div
      style={{ backgroundColor: themeColor }}
      className="h-screen w-screen flex justify-center items-center flex-col transition-colors duration-300"
    >
      <div className="bg-white/20 backdrop-blur-md p-8 rounded-2xl shadow-xl max-w-2xl w-full">
        <h1 className="text-4xl font-bold text-white mb-2 text-center">Proverbs</h1>
        <p className="text-gray-200 text-center italic mb-6">This is a demonstrative page, but it could be anything you want! 🪁</p>
        <hr className="border-white/20 my-6" />
        <div className="flex flex-col gap-3">
          {state.proverbs?.map((proverb, index) => (
            <div 
              key={index} 
              className="bg-white/15 p-4 rounded-xl text-white relative group hover:bg-white/20 transition-all"
            >
              <p className="pr-8">{proverb}</p>
              <button 
                onClick={() => setState({
                  ...state,
                  proverbs: state.proverbs?.filter((_, i) => i !== index),
                })}
                className="absolute right-3 top-3 opacity-0 group-hover:opacity-100 transition-opacity 
                  bg-red-500 hover:bg-red-600 text-white rounded-full h-6 w-6 flex items-center justify-center"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
        {state.proverbs?.length === 0 && <p className="text-center text-white/80 italic my-8">
          No proverbs yet. Ask the assistant to add some!
        </p>}
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
  status 
}: { 
  location?: string, 
  themeColor: string, 
  result: WeatherToolResult, 
  status: "inProgress" | "executing" | "complete" 
}) {
  if (status !== "complete") {
    return (
      <div 
        className="rounded-xl shadow-xl mt-6 mb-4 max-w-md w-full"
        style={{ backgroundColor: themeColor }}
      >
        <div className="bg-white/20 p-4 w-full">
          <p className="text-white animate-pulse">Loading weather for {location}...</p>
        </div>
      </div>
    )
  }

  return (
    <div
      style={{ backgroundColor: themeColor }}
      className="rounded-xl shadow-xl mt-6 mb-4 max-w-md w-full"
    >
      <div className="bg-white/20 p-4 w-full">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-white capitalize">{location}</h3>
            <p className="text-white">Current Weather</p>
          </div>
          <WeatherIcon conditions={result.conditions} />         
        </div>
        
        <div className="mt-4 flex items-end justify-between">
          <div className="text-3xl font-bold text-white">
            <span className="">
              {result.temperature}° C
            </span>
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
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-14 h-14 text-yellow-200">
      <circle cx="12" cy="12" r="5" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" strokeWidth="2" stroke="currentColor" />
    </svg>
  );
}

function RainIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-14 h-14 text-blue-200">
      {/* Cloud */}
      <path d="M7 15a4 4 0 0 1 0-8 5 5 0 0 1 10 0 4 4 0 0 1 0 8H7z" fill="currentColor" opacity="0.8"/>
      {/* Rain drops */}
      <path d="M8 18l2 4M12 18l2 4M16 18l2 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" fill="none"/>
    </svg>
  );
}

function CloudIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-14 h-14 text-gray-200">
      <path d="M7 15a4 4 0 0 1 0-8 5 5 0 0 1 10 0 4 4 0 0 1 0 8H7z" fill="currentColor"/>
    </svg>
  );
}
