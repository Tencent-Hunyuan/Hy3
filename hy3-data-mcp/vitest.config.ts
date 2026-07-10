import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: {
      provider: "v8",
      exclude: [
        "scripts/**",
        "tests/**",
        "dist/**",
        "configs/**",
        "sample_data/**",
        "assets/**",
        "**/*.d.ts",
        "**/*.config.*",
      ],
    },
  },
});
