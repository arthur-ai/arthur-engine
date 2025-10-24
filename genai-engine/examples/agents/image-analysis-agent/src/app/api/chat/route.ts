import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-proto";
import { resourceFromAttributes } from "@opentelemetry/resources";
import { trace, context } from "@opentelemetry/api";

interface Message {
  role: string;
  content: string | MessageContent[];
}

interface MessageContent {
  type: string;
  text?: string;
  image_url?: { url: string };
}

// Initialize OpenTelemetry with Arthur endpoint
const exporter = new OTLPTraceExporter({
  url: `${process.env.ARTHUR_BASE_URL}/v1/traces`,
  headers: {
    Authorization: `Bearer ${process.env.ARTHUR_API_KEY}`,
  },
});

const provider = new NodeTracerProvider({
  resource: resourceFromAttributes({
    "service.name": "image-analysis-agent",
    "arthur.task": process.env.ARTHUR_TASK_ID!,
  }),
  spanProcessors: [new BatchSpanProcessor(exporter)],
});

// Don't register to avoid Next.js auto-instrumentation creating extra spans
// provider.register();
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { messages } = body;

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json(
        { error: "Messages array is required" },
        { status: 400 }
      );
    }

    const tracer = provider.getTracer("image-analysis-agent-chat");

    // Create parent AGENT span
    const agentSpan = tracer.startSpan("imageAnalysisAgent");

    // Set OpenInference span kind as AGENT
    agentSpan.setAttribute("openinference.span.kind", "AGENT");
    agentSpan.setAttribute("agent.name", "imageAnalysisAgent");

    // Generate a run ID for this agent invocation
    const runId = crypto.randomUUID();
    const metadata = {
      runId,
      "agent.instructions": "You are a helpful image analysis assistant with vision capabilities. You can analyze images, photos, screenshots, charts, graphs, and data visualizations.",
    };
    agentSpan.setAttribute("metadata", JSON.stringify(metadata));

    // Set agent input/output at top level
    agentSpan.setAttribute("input.value", JSON.stringify(messages));
    agentSpan.setAttribute("input.mime_type", "application/json");

    try {
      // Create child LLM span with the agent span as parent
      const ctx = trace.setSpan(context.active(), agentSpan);

      const llmSpan = tracer.startSpan("gpt-4o", undefined, ctx);

      // Set OpenInference span kind as LLM
      llmSpan.setAttribute("openinference.span.kind", "LLM");
      llmSpan.setAttribute("llm.model_name", "gpt-4o");
      llmSpan.setAttribute("llm.provider", "openai");

      // Set LLM input.value and input.mime_type
      llmSpan.setAttribute("input.value", JSON.stringify({ messages }));
      llmSpan.setAttribute("input.mime_type", "application/json");

      // Set input messages
      messages.forEach((msg: Message, idx: number) => {
        llmSpan.setAttribute(`llm.input_messages.${idx}.message.role`, msg.role);
        if (typeof msg.content === "string") {
          // Text-only message uses message.content (singular)
          llmSpan.setAttribute(`llm.input_messages.${idx}.message.content`, msg.content);
        } else if (Array.isArray(msg.content)) {
          // Multimodal message uses message.contents (plural) - flatten the array
          msg.content.forEach((part: MessageContent, partIdx: number) => {
            if (part.type === "text") {
              llmSpan.setAttribute(`llm.input_messages.${idx}.message.contents.${partIdx}.text.text`, part.text);
            } else if (part.type === "image_url") {
              llmSpan.setAttribute(`llm.input_messages.${idx}.message.contents.${partIdx}.image.image.url`, part.image_url.url);
            }
          });
        }
      });

      const completion = await openai.chat.completions.create({
        model: "gpt-4o",
        messages: messages,
      });

      const response = completion.choices[0]?.message?.content || "";

      // Set LLM output.value and output.mime_type
      llmSpan.setAttribute("output.value", JSON.stringify({ text: response }));
      llmSpan.setAttribute("output.mime_type", "application/json");

      // Set output message
      llmSpan.setAttribute("llm.output_messages.0.message.role", "assistant");
      llmSpan.setAttribute("llm.output_messages.0.message.content", response);

      // Set token counts
      if (completion.usage) {
        llmSpan.setAttribute("llm.token_count.prompt", completion.usage.prompt_tokens);
        llmSpan.setAttribute("llm.token_count.completion", completion.usage.completion_tokens);
        llmSpan.setAttribute("llm.token_count.total", completion.usage.total_tokens);
      }

      llmSpan.end();

      // Set agent output
      agentSpan.setAttribute("output.value", JSON.stringify({ text: response, files: [] }));
      agentSpan.setAttribute("output.mime_type", "application/json");

      agentSpan.end();

      // Force flush to ensure spans are sent before response
      await provider.forceFlush();

      return NextResponse.json({ response });
    } catch (error) {
      agentSpan.recordException(error as Error);
      agentSpan.end();
      throw error;
    }
  } catch (error) {
    console.error("Chat API error:", error);
    return NextResponse.json(
      { error: "Internal server error", details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}
