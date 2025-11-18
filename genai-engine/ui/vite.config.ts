import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import type { PluginOption } from "vite";

const injectMeticulousRecordingScript = (mode: string, recordingToken: string | undefined): PluginOption => ({
  name: "inject-meticulous-script",
  transformIndexHtml(html) {
    if (mode === "production") {
      return html.replace(/<script\s+id="meticulous"><\/script>/, "");
    }

    if (!recordingToken) {
      console.warn("METICULOUS_RECORDING_TOKEN not set. Meticulous recording will be disabled.");
      return html.replace(/<script\s+id="meticulous"><\/script>/, "");
    }

    // Inject conditional loader: only loads Meticulous on the target hostname
    const meticulousScript = `<script id="meticulous">
      (function() {
        if (window.location.hostname === "engine.development.arthur.ai") {
          var script = document.createElement('script');
          script.setAttribute('data-recording-token', '${recordingToken}');
          script.setAttribute('data-is-production-environment', 'false');
          script.src = 'https://snippet.meticulous.ai/v1/meticulous.js';
          document.head.appendChild(script);
        }
      })();
    </script>`;

    return html.replace(/<script\s+id="meticulous"><\/script>/, meticulousScript);
  },
});

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const recordingToken = env.METICULOUS_RECORDING_TOKEN;

  return {
    plugins: [injectMeticulousRecordingScript(mode, recordingToken), react(), tailwindcss()],
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
