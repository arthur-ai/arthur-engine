import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { MastraAgent } from "@ag-ui/mastra"
import { NextRequest } from "next/server";
import { mastra, arthurExporter } from "@/mastra";
 
// 1. You can use any service adapter here for multi-agent support.
const serviceAdapter = new ExperimentalEmptyAdapter();

// 2. Build a Next.js API route that handles the CopilotKit runtime requests.
export const POST = async (req: NextRequest) => {
  // Extract user and session IDs from headers
  const userId = req.headers.get('x-user-id');
  const sessionId = req.headers.get('x-session-id');

  // Set request metadata on the Arthur exporter
  if (userId || sessionId) {
    arthurExporter.setRequestMetadata({ 
      userId: userId || undefined, 
      sessionId: sessionId || undefined 
    });
  }

  // 3. Create the CopilotRuntime instance and utilize the Mastra AG-UI
  //    integration to get the remote agents. Cache this for performance.
  const runtime = new CopilotRuntime({
    agents: MastraAgent.getLocalAgents({ mastra }),
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });
 
  return handleRequest(req);
};