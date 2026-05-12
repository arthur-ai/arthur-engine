import { query } from '@anthropic-ai/claude-agent-sdk';
import fs from 'node:fs';
import path from 'node:path';

export interface CodeAnalysisResult {
  language: 'python' | 'typescript' | 'javascript' | 'other';
  framework: 'mastra' | 'langchain' | 'openai' | 'anthropic' | 'crewai' | 'autogen' | 'other' | null;
  isInstrumented: boolean;
  instrumentationType: 'arthur-sdk' | 'mastra-arthur-exporter' | 'openinference' | null;
  entryPoint: string | null;
  details: string;
}

const INSTRUCTIONS = `You are Buzz's code analysis module. Your job is to analyze an agentic application's
repository and return a structured JSON assessment.

Always use your tools to examine the repository before drawing conclusions:
1. Call Glob first to see all files
2. Call Read to read manifests (package.json, requirements.txt, pyproject.toml)
3. Call Grep or Read as needed to verify findings

Return ONLY a JSON object with this exact structure (no markdown, no explanation, just raw JSON):
{
  "language": "python" | "typescript" | "javascript" | "other",
  "framework": "mastra" | "langchain" | "openai" | "anthropic" | "crewai" | "autogen" | "other" | null,
  "isInstrumented": boolean,
  "instrumentationType": "arthur-sdk" | "mastra-arthur-exporter" | "openinference" | null,
  "entryPoint": "<relative path to main entry file>" | null,
  "details": "<one sentence summary>"
}

Detection rules:
- language: "python" if requirements.txt or pyproject.toml exists
- language: "typescript" if tsconfig.json or .ts files exist
- language: "javascript" if package.json exists but no tsconfig.json
- framework: "mastra" if @mastra/core or mastra in package.json dependencies
- framework: "langchain" if langchain or langchain-* in dependencies
- framework: "openai" if openai in dependencies and no higher-level framework detected
- isInstrumented: true if arthur_observability_sdk in Python deps
  OR ArthurExporter imported in TS files
  OR @opentelemetry/exporter-trace-otlp-proto configured with Arthur URL
- instrumentationType: "arthur-sdk" for Python SDK, "mastra-arthur-exporter" for Mastra, "openinference" for OTel/OpenInference`;

function extractJSON(text: string): string {
  // Strip markdown code blocks if present
  const blockMatch = text.match(/```(?:json)?\s*([\s\S]+?)```/);
  if (blockMatch) return blockMatch[1].trim();
  // Find raw JSON object
  const jsonMatch = text.match(/\{[\s\S]+\}/);
  if (jsonMatch) return jsonMatch[0];
  return text.trim();
}

/** Fast file-system heuristic — used as fallback when Claude agent fails */
function heuristicAnalysis(repoPath: string): CodeAnalysisResult {
  const hasPyproject = fs.existsSync(path.join(repoPath, 'pyproject.toml'));
  const hasRequirements = fs.existsSync(path.join(repoPath, 'requirements.txt'));
  const hasTsconfig = fs.existsSync(path.join(repoPath, 'tsconfig.json'));
  const hasPackageJson = fs.existsSync(path.join(repoPath, 'package.json'));

  let language: CodeAnalysisResult['language'] = 'other';
  if (hasPyproject || hasRequirements) language = 'python';
  else if (hasTsconfig) language = 'typescript';
  else if (hasPackageJson) language = 'javascript';

  let framework: CodeAnalysisResult['framework'] = null;
  let isInstrumented = false;
  let instrumentationType: CodeAnalysisResult['instrumentationType'] = null;

  if (hasPackageJson) {
    try {
      const pkg = JSON.parse(fs.readFileSync(path.join(repoPath, 'package.json'), 'utf-8')) as {
        dependencies?: Record<string, string>;
        devDependencies?: Record<string, string>;
      };
      const deps = { ...(pkg.dependencies ?? {}), ...(pkg.devDependencies ?? {}) };
      if ('@mastra/core' in deps || 'mastra' in deps) framework = 'mastra';
      else if ('langchain' in deps || '@langchain/core' in deps) framework = 'langchain';
      else if ('openai' in deps) framework = 'openai';
      else if ('@anthropic-ai/sdk' in deps) framework = 'anthropic';

      if ('@arizeai/openinference-core' in deps || 'openinference-instrumentation' in deps) {
        isInstrumented = true;
        instrumentationType = 'openinference';
      }
    } catch { /* ignore */ }
  }

  if (hasRequirements) {
    try {
      const req = fs.readFileSync(path.join(repoPath, 'requirements.txt'), 'utf-8');
      if (req.includes('arthur-observability-sdk')) {
        isInstrumented = true;
        instrumentationType = 'arthur-sdk';
      }
      if (!framework) {
        if (req.includes('langchain')) framework = 'langchain';
        else if (req.includes('openai')) framework = 'openai';
        else if (req.includes('anthropic')) framework = 'anthropic';
      }
    } catch { /* ignore */ }
  }

  if (hasPyproject) {
    try {
      const toml = fs.readFileSync(path.join(repoPath, 'pyproject.toml'), 'utf-8');
      if (toml.includes('arthur-observability-sdk')) {
        isInstrumented = true;
        instrumentationType = 'arthur-sdk';
      }
      if (!framework) {
        if (toml.includes('langchain')) framework = 'langchain';
        else if (toml.includes('openai')) framework = 'openai';
      }
    } catch { /* ignore */ }
  }

  return {
    language,
    framework,
    isInstrumented,
    instrumentationType,
    entryPoint: null,
    details: `Heuristic detection: ${language} app${framework ? ` (${framework})` : ''}`,
  };
}

/**
 * Analyze a repository using the Claude Code SSO session.
 * Falls back to file-system heuristics if the agent call fails.
 */
export async function analyzeRepository(repoPath: string): Promise<CodeAnalysisResult> {
  try {
    const stream = query({
      prompt: `Analyze the agentic application repository at: ${repoPath}\n\nUse your tools to examine the files and return the JSON assessment.`,
      options: {
        cwd: repoPath,
        allowedTools: ['Read', 'Glob', 'Grep'],
        systemPrompt: INSTRUCTIONS,
        maxTurns: 3,
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

    return JSON.parse(extractJSON(fullOutput)) as CodeAnalysisResult;
  } catch {
    return heuristicAnalysis(repoPath);
  }
}
