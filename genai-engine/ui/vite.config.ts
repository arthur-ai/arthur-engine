import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import type { PluginOption } from "vite";


const injectMeticulousRecordingScript = (
  mode: string,
  recordingToken: string | undefined
): PluginOption => ({
  name: "inject-meticulous-script",
  transformIndexHtml(html) {
    if (mode === "production") {
      return html.replace(/<script\s+id="meticulous"><\/script>/, "");
    }

    if (!recordingToken) {
      console.warn(
        "METICULOUS_RECORDING_TOKEN not set. Meticulous recording will be disabled."
      );
      return html.replace(/<script\s+id="meticulous"><\/script>/, "");
    }

    const meticulousScript = `<script
      id="meticulous"
      data-recording-token="${recordingToken}"
      data-is-production-environment="false"
      src="https://snippet.meticulous.ai/v1/meticulous.js"
    ></script>`;

    return html.replace(
      /<script\s+id="meticulous"><\/script>/,
      meticulousScript
    );
  },
});

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const recordingToken = env.METICULOUS_RECORDING_TOKEN;

  return {
    plugins: [
      injectMeticulousRecordingScript(mode, recordingToken),
      react(),
      tailwindcss(),
    ],
    server: {
      port: 3000,
      host: true, // Allow external connections
    },
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    build: {
      outDir: "dist",
      assetsDir: "assets",
      // Ensure all routes are handled by index.html for SPA routing
      rollupOptions: {
        output: {
          manualChunks: undefined,
        },
      },
    },
    // Configure for SPA routing
    base: "/",
  };
});
