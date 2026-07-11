import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: {
      provider: "v8",
      exclude: [
        "scripts/**",
        "tests/**",
        "dist/**",
        "sample_data/**",
        "assets/**",
        "src/index.ts",
        "src/server.ts",
        "src/cli/index.ts",
        "src/cli/init.ts",
        "**/*.d.ts",
        "**/*.config.*",
      ],
    },
  },
});
