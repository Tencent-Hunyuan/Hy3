import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { loadConfig, Hy3Client } from "../src/client.js";

vi.mock("openai", () => {
  return {
    default: class MockOpenAI {
      chat = {
        completions: {
          create: vi.fn().mockResolvedValue({
            choices: [{ message: { content: "  mocked hy3 response  " } }],
          }),
        },
      };
    },
  };
});

describe("loadConfig", () => {
  const originalKey = process.env.HY3_API_KEY;
  const originalBase = process.env.HY3_BASE_URL;
  const originalModel = process.env.HY3_MODEL;

  beforeEach(() => {
    process.env.HY3_API_KEY = "test-key";
    delete process.env.HY3_BASE_URL;
    delete process.env.HY3_MODEL;
  });

  afterEach(() => {
    process.env.HY3_API_KEY = originalKey;
    process.env.HY3_BASE_URL = originalBase;
    process.env.HY3_MODEL = originalModel;
  });

  it("loads config from environment variables with defaults", () => {
    const config = loadConfig();
    expect(config.apiKey).toBe("test-key");
    expect(config.baseURL).toBe("https://tokenhub.tencentmaas.com/v1");
    expect(config.model).toBe("hy3-preview");
  });

  it("throws when HY3_API_KEY is missing", () => {
    delete process.env.HY3_API_KEY;
    expect(() => loadConfig()).toThrow("Missing HY3_API_KEY");
  });
});

describe("Hy3Client", () => {
  it("returns trimmed response content", async () => {
    const client = new Hy3Client({
      apiKey: "test-key",
      baseURL: "https://tokenhub.tencentmaas.com/v1",
      model: "hy3-preview",
    });
    const response = await client.chat([
      { role: "user", content: "hello" },
    ]);
    expect(response).toBe("mocked hy3 response");
  });
});
