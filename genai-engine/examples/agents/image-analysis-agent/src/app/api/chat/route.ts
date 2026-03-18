import { NextRequest, NextResponse } from "next/server";
import { Arthur } from "@arthur-ai/observability-sdk";
import OpenAI from "openai";

const arthur = new Arthur({
  apiKey: process.env.ARTHUR_API_KEY,
  baseUrl: process.env.ARTHUR_BASE_URL,
  serviceName: "image-analysis-agent",
  taskId: process.env.ARTHUR_TASK_ID,
});
arthur.instrumentOpenAI();

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

    const completion = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: messages,
    });

    const response = completion.choices[0]?.message?.content || "";

    return NextResponse.json({ response });
  } catch (error) {
    console.error("Chat API error:", error);
    return NextResponse.json(
      { error: "Internal server error", details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  }
}
