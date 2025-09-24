import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
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
  base: "./",
});
