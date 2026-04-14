import { query } from '@anthropic-ai/claude-agent-sdk';

export interface EvalRecommendation {
  slug: string;
  displayName: string;
  rationale: string;
  instructions: string;
}

export interface EvalRecommendations {
  recommendations: EvalRecommendation[];
}

const INSTRUCTIONS = `You are an Arthur GenAI Engine eval analyst. Given a sample trace from a user's
agentic application (input prompts + model outputs) and their framework info, recommend 2-4
continuous eval configurations that provide the most meaningful quality monitoring.

Each eval uses a Jinja2 template where {{ input }} is the user's prompt and {{ output }} is the
model's response. Instructions must end with a clear scoring directive asking the evaluator LLM
to return a JSON object with "score" (0.0-1.0, where 1.0 = fully passes) and "reason" (brief explanation).

IMPORTANT — Hallucination / Faithfulness evals:
Only recommend a hallucination or faithfulness eval if the prompt explicitly states
"Retrieval context available: YES" AND the trace includes reference material (retrieved
documents, ground truth passages, or source context) that the model output should be faithful to.
If the trace only shows a user input and a model response with no reference material, do NOT
recommend hallucination or faithfulness evals — they cannot be evaluated correctly without a
reference context to compare against.

Consider these common eval types and adapt them to the application's context:
- Relevance: does the output address what the input asked?
- Faithfulness / Hallucination: does the output contain unsupported claims? (ONLY if retrieval context is available)
- Toxicity: does the output contain harmful or offensive content?
- Conciseness: is the output appropriately concise?
- Task completion: did the agent accomplish what was asked?

Choose evals that fit the actual use case evident from the trace. For example:
- Customer support apps → relevance, tone, task completion
- RAG / Q&A apps → faithfulness, relevance (only when retrieval context is confirmed present)
- Code assistants → correctness, clarity
- General chat → relevance, toxicity

Return ONLY a raw JSON object with no markdown fences, no preamble, no explanation:
{
  "recommendations": [
    {
      "slug": "kebab-case-slug",
      "displayName": "Human Readable Name",
      "rationale": "One sentence explaining why this eval matters for this application",
      "instructions": "Evaluate the following LLM interaction...\n\nInput: {{ input }}\nOutput: {{ output }}\n\nReturn a JSON object: {\"score\": <0.0-1.0>, \"reason\": \"<brief explanation>\"}"
    }
  ]
}`;

function extractJSON(text: string): string {
  const blockMatch = text.match(/```(?:json)?\s*([\s\S]+?)```/);
  if (blockMatch) return blockMatch[1].trim();
  const jsonMatch = text.match(/\{[\s\S]+\}/);
  if (jsonMatch) return jsonMatch[0];
  return text.trim();
}

export type RecommendEvalsResult =
  | { ok: true; recommendations: EvalRecommendations }
  | { ok: false; reason: string };

export async function recommendEvals(
  traceContent: string,
  spanName: string,
  framework: string | null,
  language: string,
  modelProvider: string,
  hasRetrievalContext: boolean,
): Promise<RecommendEvalsResult> {
  const frameworkNote = framework
    ? `Framework: ${framework} (${language})`
    : `Language: ${language}`;

  const prompt = `Analyze this trace and recommend the most impactful continuous evals:

${frameworkNote}
Eval model provider available: ${modelProvider}
Span name: ${spanName}
Retrieval context available: ${hasRetrievalContext ? 'YES' : 'NO'}

Trace content:
${traceContent}`;

  try {
    const stream = query({
      prompt,
      options: {
        allowedTools: [],
        systemPrompt: INSTRUCTIONS,
        maxTurns: 1,
      },
    });

    let fullOutput = '';
    for await (const message of stream) {
      if (message.type === 'assistant') {
        const content = (message as { type: 'assistant'; message: { content: Array<{ type: string; text?: string }> } }).message?.content ?? [];
        for (const block of content) {
          if (block.type === 'text' && block.text) {
            fullOutput += block.text;
          }
        }
      }
    }

    const jsonText = extractJSON(fullOutput);
    const parsed = JSON.parse(jsonText) as EvalRecommendations;

    if (!Array.isArray(parsed.recommendations) || parsed.recommendations.length === 0) {
      return { ok: false, reason: 'Claude returned no eval recommendations for this trace.' };
    }

    return { ok: true, recommendations: parsed };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return { ok: false, reason: `Claude API error: ${message}` };
  }
}
