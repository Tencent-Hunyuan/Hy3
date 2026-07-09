import OpenAI from "openai";

export interface Hy3Config {
  apiKey: string;
  baseURL: string;
  model: string;
}

export function loadConfig(): Hy3Config {
  const apiKey = process.env.HY3_API_KEY;
  if (!apiKey) {
    throw new Error(
      "Missing HY3_API_KEY environment variable. Please set it before starting the server."
    );
  }
  return {
    apiKey,
    baseURL: process.env.HY3_BASE_URL || "https://tokenhub.tencentmaas.com/v1",
    model: process.env.HY3_MODEL || "hy3-preview",
  };
}

export class Hy3Client {
  private client: OpenAI;
  private model: string;

  constructor(config: Hy3Config) {
    this.client = new OpenAI({
      apiKey: config.apiKey,
      baseURL: config.baseURL,
    });
    this.model = config.model;
  }

  async chat(
    messages: OpenAI.Chat.ChatCompletionMessageParam[],
    options?: Partial<Omit<OpenAI.Chat.ChatCompletionCreateParams, "stream" | "model" | "messages">>
  ): Promise<string> {
    const response = await this.client.chat.completions.create({
      model: this.model,
      messages,
      temperature: 0.7,
      stream: false,
      ...options,
    });
    return response.choices[0]?.message?.content?.trim() || "";
  }
}
