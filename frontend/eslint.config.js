import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  // contracts.ts is generated from bluewatch/models.py; lint its consumers, not the generator output.
  { ignores: ["dist/**", "node_modules/**", "src/contracts.ts"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  reactHooks.configs.flat.recommended,
  { languageOptions: { globals: { ...globals.browser } } },
);
