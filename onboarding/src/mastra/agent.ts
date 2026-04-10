import { Agent } from '@mastra/core/agent';
import { anthropic } from '@ai-sdk/anthropic';
import fs from 'node:fs';
import path from 'node:path';
import {
  readFileTool,
  listDirectoryTool,
  searchPatternTool,
  checkDependenciesTool,
} from './tools/code-analysis.js';

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
1. Call listDirectory first to see all files
2. Call checkDependencies to read manifests (package.json, requirements.txt, pyproject.toml)
3. Call readFile or searchPattern as needed to verify findings

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

export const buzzCodeAnalysisAgent = new Agent({
  id: 'buzz-code-analysis',
  name: 'buzz-code-analysis',
  instructions: INSTRUCTIONS,
  model: anthropic('claude-3-5-haiku-20241022'),
  tools: {
    readFileTool,
    listDirectoryTool,
    searchPatternTool,
    checkDependenciesTool,
  },
});

function extractJSON(text: string): string {
  // Strip markdown code blocks if present
  const blockMatch = text.match(/```(?:json)?\s*([\s\S]+?)```/);
  if (blockMatch) return blockMatch[1].trim();
  // Find raw JSON object
  const jsonMatch = text.match(/\{[\s\S]+\}/);
  if (jsonMatch) return jsonMatch[0];
  return text.trim();
}

/** Fast file-system heuristic — used as fallback when Mastra agent fails */
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
 * Analyze a repository using the Mastra code analysis agent.
 * Falls back to file-system heuristics if the agent call fails.
 */
export async function analyzeRepository(repoPath: string): Promise<CodeAnalysisResult> {
  try {
    const result = await buzzCodeAnalysisAgent.generate([
      {
        role: 'user',
        content: `Analyze the agentic application repository at: ${repoPath}

Use your tools to examine the files and return the JSON assessment.`,
      },
    ]);

    const jsonText = extractJSON(result.text);
    return JSON.parse(jsonText) as CodeAnalysisResult;
  } catch {
    // Silently fall back to heuristics
    return heuristicAnalysis(repoPath);
  }
}
