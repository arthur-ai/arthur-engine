import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-proto";
import { resourceFromAttributes } from "@opentelemetry/resources";
import { trace, context } from "@opentelemetry/api";
import { SemanticConventions, OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";

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
    agentSpan.setAttribute(SemanticConventions.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKind.AGENT);
    agentSpan.setAttribute(SemanticConventions.AGENT_NAME, "imageAnalysisAgent");

    // Generate a run ID for this agent invocation
    const runId = crypto.randomUUID();
    agentSpan.setAttribute(SemanticConventions.METADATA, JSON.stringify({
      runId,
      "agent.instructions": "You are a helpful image analysis assistant with vision capabilities."
    }));

    // Set agent input/output at top level
    agentSpan.setAttribute(SemanticConventions.INPUT_VALUE, JSON.stringify(messages));
    agentSpan.setAttribute(SemanticConventions.INPUT_MIME_TYPE, "application/json");

    try {
      // Create child LLM span with the agent span as parent
      const ctx = trace.setSpan(context.active(), agentSpan);

      const llmSpan = tracer.startSpan("gpt-4o", undefined, ctx);

      // Set OpenInference span kind as LLM
      llmSpan.setAttribute(SemanticConventions.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKind.LLM);
      llmSpan.setAttribute(SemanticConventions.LLM_MODEL_NAME, "gpt-4o");
      llmSpan.setAttribute(SemanticConventions.LLM_PROVIDER, "openai");

      // Set LLM input.value and input.mime_type
      llmSpan.setAttribute(SemanticConventions.INPUT_VALUE, JSON.stringify({ messages }));
      llmSpan.setAttribute(SemanticConventions.INPUT_MIME_TYPE, "application/json");

      // Set input messages
      messages.forEach((msg: Message, idx: number) => {
        llmSpan.setAttribute(`${SemanticConventions.LLM_INPUT_MESSAGES}.${idx}.${SemanticConventions.MESSAGE_ROLE}`, msg.role);
        if (typeof msg.content === "string") {
          llmSpan.setAttribute(`${SemanticConventions.LLM_INPUT_MESSAGES}.${idx}.${SemanticConventions.MESSAGE_CONTENT}`, msg.content);
        } else {
          msg.content.forEach((part: MessageContent, partIdx: number) => {
            if (part.type === "text" && part.text) {
              llmSpan.setAttribute(`${SemanticConventions.LLM_INPUT_MESSAGES}.${idx}.${SemanticConventions.MESSAGE_CONTENTS}.${partIdx}.${SemanticConventions.MESSAGE_CONTENT_TYPE}`, "text");
              llmSpan.setAttribute(`${SemanticConventions.LLM_INPUT_MESSAGES}.${idx}.${SemanticConventions.MESSAGE_CONTENTS}.${partIdx}.${SemanticConventions.MESSAGE_CONTENT_TEXT}`, part.text);
            } else if (part.type === "image_url" && part.image_url?.url) {
              llmSpan.setAttribute(`${SemanticConventions.LLM_INPUT_MESSAGES}.${idx}.${SemanticConventions.MESSAGE_CONTENTS}.${partIdx}.${SemanticConventions.MESSAGE_CONTENT_TYPE}`, "image");
              llmSpan.setAttribute(`${SemanticConventions.LLM_INPUT_MESSAGES}.${idx}.${SemanticConventions.MESSAGE_CONTENTS}.${partIdx}.${SemanticConventions.MESSAGE_CONTENT_IMAGE}.${SemanticConventions.IMAGE_URL}`, part.image_url.url);
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
      llmSpan.setAttribute(SemanticConventions.OUTPUT_VALUE, JSON.stringify({ text: response }));
      llmSpan.setAttribute(SemanticConventions.OUTPUT_MIME_TYPE, "application/json");

      // Set output message
      llmSpan.setAttribute(`${SemanticConventions.LLM_OUTPUT_MESSAGES}.0.${SemanticConventions.MESSAGE_ROLE}`, "assistant");
      llmSpan.setAttribute(`${SemanticConventions.LLM_OUTPUT_MESSAGES}.0.${SemanticConventions.MESSAGE_CONTENT}`, response);

      // Set token counts
      if (completion.usage) {
        llmSpan.setAttribute(SemanticConventions.LLM_TOKEN_COUNT_PROMPT, completion.usage.prompt_tokens);
        llmSpan.setAttribute(SemanticConventions.LLM_TOKEN_COUNT_COMPLETION, completion.usage.completion_tokens);
        llmSpan.setAttribute(SemanticConventions.LLM_TOKEN_COUNT_TOTAL, completion.usage.total_tokens);
      }

      llmSpan.end();

      // Set agent output
      agentSpan.setAttribute(SemanticConventions.OUTPUT_VALUE, JSON.stringify({ text: response, files: [] }));
      agentSpan.setAttribute(SemanticConventions.OUTPUT_MIME_TYPE, "application/json");

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
