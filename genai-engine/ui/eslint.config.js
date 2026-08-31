import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import importPlugin from "eslint-plugin-import-x";
import pluginQuery from "@tanstack/eslint-plugin-query";
import { defineConfig, globalIgnores } from "eslint/config";
import prettier from "eslint-config-prettier";

export default defineConfig([
  globalIgnores(["dist", ".pnp.*", ".yarn"]),
  ...pluginQuery.configs["flat/recommended"],
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, tseslint.configs.recommended, reactRefresh.configs.vite, prettier],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "import-x": importPlugin,
      // eslint-plugin-react-hooks v7 moved its flat configs under `configs.flat`, so
      // `configs["recommended-latest"]` is now an eslintrc-style config that flat config
      // rejects. Register the plugin directly instead.
      "react-hooks": reactHooks,
    },
    rules: {
      // v7's recommended set additionally turns on the React Compiler rules; keep
      // enforcing the two hook rules this project already linted with and adopt the rest
      // as a separate change.
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "react-refresh/only-export-components": "off",
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
      "import-x/order": [
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
