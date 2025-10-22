import { context } from "@opentelemetry/api";
import { setAttributes, setSession } from "@arizeai/openinference-core";
import { Observable } from "rxjs";
import type { RunAgentInput, BaseEvent } from "@ag-ui/client";
import { MastraAgent } from "@ag-ui/mastra";
import type { MastraAgentConfig } from "@ag-ui/mastra";

/**
 * Context-aware MastraAgent that automatically sets OpenTelemetry context
 * for user and session attributes to prevent race conditions in tracing.
 */
export class ContextAwareMastraAgent extends MastraAgent {
  private userId?: string;
  private sessionId?: string;

  constructor(config: MastraAgentConfig & { userId?: string; sessionId?: string }) {
    super(config);
    this.userId = config.userId;
    this.sessionId = config.sessionId;
  }

  run(input: RunAgentInput): Observable<BaseEvent> {
    // Use the user/session IDs from constructor if available
    const userId = this.userId;
    const sessionId = this.sessionId;
    
    // If we have context, wrap the execution in OpenTelemetry context
    if (userId || sessionId) {
      const contextAttributes: Record<string, string> = {};
      
      if (userId) {
        contextAttributes["user.id"] = userId;
      }
      
      // Set up the context with attributes and session
      const contextWithAttributes = context.with(
        setAttributes(
          setSession(context.active(), { sessionId: sessionId || "default" }),
          contextAttributes
        ),
        () => {
          // Call the parent's run method within this context
          return super.run(input);
        }
      );
      
      return contextWithAttributes;
    }
    
    // No context, just run normally
    return super.run(input);
  }
}
