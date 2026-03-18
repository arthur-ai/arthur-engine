import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts", "src/mastra/index.ts"],
  format: ["cjs", "esm"],
  dts: true,
  sourcemap: true,
  clean: true,
  outDir: "dist",
  external: [
    "@arizeai/openinference-instrumentation-openai",
    "@arizeai/openinference-instrumentation-anthropic",
    "@arizeai/openinference-instrumentation-langchain",
    "@arizeai/openinference-instrumentation-claude-agent-sdk",
    "@arizeai/openinference-instrumentation-vercel-ai",
    "@arizeai/openinference-instrumentation-groq",
    "@arizeai/openinference-instrumentation-mistralai",
    "@arizeai/openinference-instrumentation-bee-agent",
    "@mastra/core",
    "@mastra/core/ai-tracing",
  ],
});
