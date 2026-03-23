import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { MastraAgent } from "@/app/lib/ag-ui/mastra";
import { NextRequest } from "next/server";
import { mastra } from "@/mastra";
import { RuntimeContext } from "@mastra/core/runtime-context";

// 1. You can use any service adapter here for multi-agent support.
const serviceAdapter = new ExperimentalEmptyAdapter();

// 2. Build a Next.js API route that handles the CopilotKit runtime requests.
export const POST = async (req: NextRequest) => {
  // Extract telemetry headers from the request
  const userId = req.headers.get('x-user-id');
  const sessionId = req.headers.get('x-session-id');
  
  // Create a RuntimeContext with telemetry data
  const runtimeContext = new RuntimeContext();
  runtimeContext.set("telemetry", { userId, sessionId });
  
  // 3. Create the CopilotRuntime instance and utilize the Mastra AG-UI
  //    integration to get the remote agents. Cache this for performance.
  const runtime = new CopilotRuntime({
    agents: MastraAgent.getLocalAgents({ mastra, runtimeContext }),
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
