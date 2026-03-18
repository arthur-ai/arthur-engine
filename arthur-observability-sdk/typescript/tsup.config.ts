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
    "@arizeai/openinference-instrumentation-bedrock",
    "@arizeai/openinference-instrumentation-bedrock-agent-runtime",
    "@arizeai/openinference-instrumentation-beeai",
    "@arizeai/openinference-instrumentation-mcp",
    "@mastra/core",
    "@mastra/core/ai-tracing",
  ],
});
