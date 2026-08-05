import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import type { PluginOption } from "vite";
import { nodePolyfills } from "vite-plugin-node-polyfills";

const injectMeticulousRecordingScript = (mode: string, recordingToken: string | undefined): PluginOption => ({
  name: "inject-meticulous-script",
  transformIndexHtml(html) {
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
          script.setAttribute('data-is-production-environment', '${mode === "production"}');
          script.src = 'https://snippet.meticulous.ai/v1/meticulous.js';
          document.head.appendChild(script);
        }
      })();
    </script>`;

    return html.replace(/<script\s+id="meticulous"><\/script>/, meticulousScript);
  },
});

// Chains @arthur/shared-components' shipped .js.map files into our build output
const chainSharedComponentsSourcemaps = (): PluginOption => ({
  name: "chain-shared-components-sourcemaps",
  apply: "build",
  load(id) {
    const cleanId = id.split("?")[0];
    if (!cleanId.includes("@arthur/shared-components/dist") || !cleanId.endsWith(".js")) return null;
    const code = fs.readFileSync(cleanId, "utf8");
    const match = code.match(/\/\/# sourceMappingURL=([^\s'"]+)\s*$/);
    if (!match || match[1].startsWith("data:")) return null;
    const mapPath = path.resolve(path.dirname(cleanId), match[1]);
    if (!fs.existsSync(mapPath)) return null;
    return { code, map: JSON.parse(fs.readFileSync(mapPath, "utf8")) };
  },
});

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const recordingToken = env.METICULOUS_RECORDING_TOKEN;
  const amplitudeApiKey = env.AMPLITUDE_API_KEY;
  const recaptchaSiteKey = env.RECAPTCHA_ENTERPRISE_SITE_KEY;
  // Opt-in (used by the Meticulous CI build); keep off by default so published images ship no sources
  const generateSourcemaps = env.GENERATE_SOURCEMAPS === "true";

  return {
    plugins: [
      injectMeticulousRecordingScript(mode, recordingToken),
      ...(generateSourcemaps ? [chainSharedComponentsSourcemaps()] : []),
      react(),
      tailwindcss(),
      nodePolyfills(),
    ],
    define: {
      // Map AMPLITUDE_API_KEY from .env.local to VITE_AMPLITUDE_TOKEN for client-side access
      "import.meta.env.VITE_AMPLITUDE_TOKEN": JSON.stringify(amplitudeApiKey || ""),
      // Map RECAPTCHA_ENTERPRISE_SITE_KEY to a VITE_-prefixed var for client-side access
      "import.meta.env.VITE_RECAPTCHA_ENTERPRISE_SITE_KEY": JSON.stringify(recaptchaSiteKey || ""),
    },
    server: {
      port: parseInt(env.GENAI_UI_PORT || "3000", 10),
      host: true, // Allow external connections
    },
    resolve: {
      dedupe: [
        "react",
        "react-dom",
        "@mui/material",
        "@mui/system",
        "@emotion/react",
        "@emotion/styled",
        "material-react-table",
        "@tanstack/react-table",
        "@tanstack/react-query",
      ],
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
        "@tanstack/react-form": fileURLToPath(new URL("./node_modules/@tanstack/react-form", import.meta.url)),
      },
    },
    build: {
      outDir: "dist",
      assetsDir: "assets",
      sourcemap: generateSourcemaps,
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
