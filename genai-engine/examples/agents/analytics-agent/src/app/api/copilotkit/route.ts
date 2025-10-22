import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { MastraAgent } from "@ag-ui/mastra"
import { NextRequest } from "next/server";
import { mastra, ContextAwareMastraAgent } from "@/mastra";
 
// 1. You can use any service adapter here for multi-agent support.
const serviceAdapter = new ExperimentalEmptyAdapter();

// 2. Build a Next.js API route that handles the CopilotKit runtime requests.
export const POST = async (req: NextRequest) => {
  // Extract user and session IDs from headers
  const userId = req.headers.get('x-user-id');
  const sessionId = req.headers.get('x-session-id');

  // Create context-aware agents that will automatically set OpenTelemetry context
  const contextAwareAgents = Object.fromEntries(
    Object.entries(MastraAgent.getLocalAgents({ mastra })).map(([key, agent]) => [
      key,
      new ContextAwareMastraAgent({
        agent: (agent as any).agent, // Extract the underlying Mastra agent
        resourceId: (agent as any).resourceId,
        runtimeContext: (agent as any).runtimeContext,
        userId: userId || undefined,
        sessionId: sessionId || undefined,
      })
    ])
  );

  // 3. Create the CopilotRuntime instance with context-aware agents
  const runtime = new CopilotRuntime({
    agents: contextAwareAgents,
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });
 
  return handleRequest(req);
};