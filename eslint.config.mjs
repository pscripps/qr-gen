import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["vendor/**", "node_modules/**", "QR-generator.html"] },
  ...tseslint.configs.recommended,
  {
    files: ["web/**/*.ts"],
    rules: {
      "no-empty": "error",
      "no-magic-numbers": [
        "error",
        { ignore: [-1, 0, 1, 2], ignoreArrayIndexes: true },
      ],
      "no-restricted-syntax": [
        "error",
        {
          selector:
            "MemberExpression[object.name='process'][property.name='env']",
          message: "Pass validated settings from config.ts.",
        },
      ],
    },
  },
  { files: ["web/config.ts"], rules: { "no-magic-numbers": "off" } },
);
