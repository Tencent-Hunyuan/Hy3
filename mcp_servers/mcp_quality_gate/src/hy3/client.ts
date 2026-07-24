import { performance } from 'node:perf_hooks';

import { z } from 'zod';

import type { ReasoningEffort } from '../tool-contracts.js';
import { Hy3ReviewError } from './errors.js';

const MAX_RESPONSE_BYTES = 256 * 1024;

const completionResponseSchema = z.object({
  choices: z
    .array(
      z.object({
        message: z.object({
          content: z.string().min(1),
        }),
      }),
    )
    .min(1),
  usage: z
    .object({
      prompt_tokens: z.number().int().nonnegative().optional(),
      completion_tokens: z.number().int().nonnegative().optional(),
      total_tokens: z.number().int().nonnegative().optional(),
    })
    .optional(),
});

export type Hy3Message = {
  role: 'system' | 'user';
  content: string;
};

export type Hy3Usage = {
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
};

export type Hy3Completion = {
  content: string;
  model: string;
  latencyMs: number;
  usage: Hy3Usage | null;
};

export interface Hy3Completer {
  complete(
    messages: readonly Hy3Message[],
    reasoningEffort: ReasoningEffort,
  ): Promise<Hy3Completion>;
}

export type Hy3ClientConfig = {
  apiKey: string;
  baseUrl: string;
  model: string;
  timeoutMs: number;
};

function completionUrl(baseUrl: string): URL {
  let parsed: URL;
  try {
    parsed = new URL(baseUrl);
  } catch {
    throw new Hy3ReviewError('invalid_configuration');
  }
  if (
    (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') ||
    parsed.username !== '' ||
    parsed.password !== '' ||
    parsed.search !== '' ||
    parsed.hash !== ''
  ) {
    throw new Hy3ReviewError('invalid_configuration');
  }
  parsed.search = '';
  parsed.hash = '';
  const normalizedPath = parsed.pathname.replace(/\/+$/, '');
  parsed.pathname = normalizedPath.endsWith('/chat/completions')
    ? normalizedPath
    : `${normalizedPath}/chat/completions`;
  return parsed;
}

async function cancelQuietly(body: ReadableStream<Uint8Array> | null): Promise<void> {
  try {
    await body?.cancel();
  } catch {
    // Provider error bodies are intentionally discarded.
  }
}

async function readBoundedResponse(response: Response): Promise<string> {
  const declaredLength = Number(response.headers.get('content-length'));
  if (
    Number.isFinite(declaredLength) &&
    declaredLength > MAX_RESPONSE_BYTES
  ) {
    await cancelQuietly(response.body);
    throw new Hy3ReviewError('response_too_large');
  }
  if (response.body === null) {
    throw new Hy3ReviewError('invalid_response');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let bytes = 0;
  let text = '';
  try {
    while (true) {
      const next = await reader.read();
      if (next.done) {
        break;
      }
      bytes += next.value.byteLength;
      if (bytes > MAX_RESPONSE_BYTES) {
        try {
          await reader.cancel();
        } catch {
          // The bounded public error below remains authoritative.
        }
        throw new Hy3ReviewError('response_too_large');
      }
      text += decoder.decode(next.value, { stream: true });
    }
    text += decoder.decode();
    return text;
  } finally {
    reader.releaseLock();
  }
}

export class Hy3ChatClient implements Hy3Completer {
  readonly #apiKey: string;
  readonly #endpoint: URL;
  readonly #model: string;
  readonly #timeoutMs: number;
  readonly #fetch: typeof fetch;

  constructor(
    config: Hy3ClientConfig,
    fetchImplementation: typeof fetch = fetch,
  ) {
    if (
      config.apiKey.length === 0 ||
      config.model.length === 0 ||
      !Number.isInteger(config.timeoutMs) ||
      config.timeoutMs <= 0
    ) {
      throw new Hy3ReviewError('invalid_configuration');
    }
    this.#apiKey = config.apiKey;
    this.#endpoint = completionUrl(config.baseUrl);
    this.#model = config.model;
    this.#timeoutMs = config.timeoutMs;
    this.#fetch = fetchImplementation;
  }

  async complete(
    messages: readonly Hy3Message[],
    reasoningEffort: ReasoningEffort,
  ): Promise<Hy3Completion> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.#timeoutMs);
    const startedAt = performance.now();
    let response: Response;
    try {
      response = await this.#fetch(this.#endpoint, {
        method: 'POST',
        headers: {
          authorization: `Bearer ${this.#apiKey}`,
          'content-type': 'application/json',
        },
        body: JSON.stringify({
          model: this.#model,
          messages,
          temperature: 0.2,
          top_p: 1,
          max_tokens: 4096,
          stream: false,
          chat_template_kwargs: {
            reasoning_effort: reasoningEffort,
          },
        }),
        signal: controller.signal,
      });
    } catch {
      clearTimeout(timeout);
      throw new Hy3ReviewError(
        controller.signal.aborted ? 'timeout' : 'network_error',
      );
    }

    try {
      if (!response.ok) {
        await cancelQuietly(response.body);
        throw new Hy3ReviewError('http_error');
      }

      let raw: unknown;
      try {
        raw = JSON.parse(await readBoundedResponse(response)) as unknown;
      } catch (error: unknown) {
        if (error instanceof Hy3ReviewError) {
          throw error;
        }
        throw new Hy3ReviewError(
          controller.signal.aborted ? 'timeout' : 'invalid_response',
        );
      }
      const parsed = completionResponseSchema.safeParse(raw);
      if (!parsed.success) {
        throw new Hy3ReviewError('invalid_response');
      }
      const usage = parsed.data.usage;
      return {
        content: parsed.data.choices[0]?.message.content ?? '',
        model: this.#model,
        latencyMs: Math.max(0, Math.round(performance.now() - startedAt)),
        usage:
          usage === undefined
            ? null
            : {
                prompt_tokens: usage.prompt_tokens ?? null,
                completion_tokens: usage.completion_tokens ?? null,
                total_tokens: usage.total_tokens ?? null,
              },
      };
    } catch (error: unknown) {
      if (error instanceof Hy3ReviewError) {
        throw error;
      }
      throw new Hy3ReviewError(
        controller.signal.aborted ? 'timeout' : 'invalid_response',
      );
    } finally {
      clearTimeout(timeout);
    }
  }
}
