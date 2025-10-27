import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import importPlugin from "eslint-plugin-import";
import pluginQuery from "@tanstack/eslint-plugin-query";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
  globalIgnores(["dist", ".pnp.*", ".yarn"]),
  ...pluginQuery.configs["flat/recommended"],
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs["recommended-latest"],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      import: importPlugin,
    },
    rules: {
      "react-refresh/only-export-components": "off",
      "import/order": [
        "error",
        {
          groups: [
            "builtin", // Node built-in modules
            "external", // npm packages
            "internal", // Internal modules (if you have any)
            "parent", // Parent directory imports
            "sibling", // Same directory imports
            "index", // Index file imports
          ],
          "newlines-between": "always",
          alphabetize: {
            order: "asc",
            caseInsensitive: true,
          },
        },
      ],
    },
  },
]);
