import { Agent } from '@mastra/core/agent';
import { anthropic } from '@ai-sdk/anthropic';

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

Consider these common eval types and adapt them to the application's context:
- Relevance: does the output address what the input asked?
- Faithfulness / Hallucination: does the output contain unsupported claims?
- Toxicity: does the output contain harmful or offensive content?
- Conciseness: is the output appropriately concise?
- Task completion: did the agent accomplish what was asked?

Choose evals that fit the actual use case evident from the trace. For example:
- Customer support apps → relevance, tone, task completion
- RAG / Q&A apps → faithfulness, relevance
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

const buzzEvalRecommenderAgent = new Agent({
  id: 'buzz-eval-recommender',
  name: 'buzz-eval-recommender',
  instructions: INSTRUCTIONS,
  model: anthropic('claude-3-5-haiku-20241022'),
});

function extractJSON(text: string): string {
  const blockMatch = text.match(/```(?:json)?\s*([\s\S]+?)```/);
  if (blockMatch) return blockMatch[1].trim();
  const jsonMatch = text.match(/\{[\s\S]+\}/);
  if (jsonMatch) return jsonMatch[0];
  return text.trim();
}

export async function recommendEvals(
  traceContent: string,
  spanName: string,
  framework: string | null,
  language: string,
  modelProvider: string,
): Promise<EvalRecommendations | null> {
  if (!process.env.ANTHROPIC_API_KEY) return null;

  const frameworkNote = framework
    ? `Framework: ${framework} (${language})`
    : `Language: ${language}`;

  const prompt = `Analyze this trace and recommend the most impactful continuous evals:

${frameworkNote}
Eval model provider available: ${modelProvider}
Span name: ${spanName}

Trace content:
${traceContent}`;

  try {
    const result = await buzzEvalRecommenderAgent.generate([
      { role: 'user', content: prompt },
    ]);

    const jsonText = extractJSON(result.text);
    const parsed = JSON.parse(jsonText) as EvalRecommendations;

    if (!Array.isArray(parsed.recommendations) || parsed.recommendations.length === 0) {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
}
