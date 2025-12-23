#!/usr/bin/env node

/**
 * Loader script to ensure environment variables are loaded
 * before running the test harness
 */

const { config } = require("dotenv");
const path = require("path");
const { spawn } = require("child_process");

// Load .env from the project root
const envPath = path.resolve(__dirname, "../.env");
const result = config({ path: envPath });

if (result.error) {
  console.error("Error loading .env file:", result.error);
  console.error("Attempted path:", envPath);
  process.exit(1);
}

// Verify critical environment variables are loaded
const requiredEnvVars = [
  "OPENAI_API_KEY",
  "ARTHUR_BASE_URL",
  "ARTHUR_API_KEY",
  "ARTHUR_TASK_ID",
  "TAVILY_API_KEY",
  "GITHUB_TOKEN",
];

const missingVars = requiredEnvVars.filter((varName) => !process.env[varName]);
if (missingVars.length > 0) {
  console.error("Missing required environment variables:", missingVars.join(", "));
  console.error("Please ensure your .env file contains all required variables.");
  process.exit(1);
}

console.log("Environment variables loaded successfully");
console.log(`Found .env at: ${envPath}\n`);

// Now run the actual test harness with tsx
const tsxPath = path.resolve(__dirname, "../node_modules/.bin/tsx");
const testHarnessPath = path.resolve(__dirname, "test-harness.ts");

const child = spawn(tsxPath, [testHarnessPath], {
  stdio: "inherit",
  env: process.env,
});

child.on("exit", (code) => {
  process.exit(code || 0);
});
