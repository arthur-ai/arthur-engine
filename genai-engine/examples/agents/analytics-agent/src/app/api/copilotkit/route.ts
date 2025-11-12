import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { MastraAgent } from "@ag-ui/mastra"
import { NextRequest } from "next/server";
import { mastra } from "@/mastra";
import { runWithTelemetryContext } from "@/mastra/observability/telemetry-context";
 
// 1. You can use any service adapter here for multi-agent support.
const serviceAdapter = new ExperimentalEmptyAdapter();

// 2. Build a Next.js API route that handles the CopilotKit runtime requests.
export const POST = async (req: NextRequest) => {
  // Extract telemetry headers from the request
  const userId = req.headers.get('x-user-id');
  const sessionId = req.headers.get('x-session-id');
  
  // Skip logging if both are missing (likely preflight/health check)
  if (userId && sessionId) {
    console.log(`[Telemetry] Request - userId: ${userId}, sessionId: ${sessionId}`);
  }

  // Get agents
  const agents = MastraAgent.getLocalAgents({ mastra });

  // Create the CopilotRuntime instance
  const runtime = new CopilotRuntime({ agents });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });
 
  // Run the entire request handler within telemetry context
  // This makes userId/sessionId available to ArthurExporter via AsyncLocalStorage
  return runWithTelemetryContext(
    { userId: userId || undefined, sessionId: sessionId || undefined },
    () => handleRequest(req)
  );
};