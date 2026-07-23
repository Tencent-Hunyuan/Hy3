import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { Hy3ChatClient } from '../src/hy3/client.js';
import { Hy3ReviewError } from '../src/hy3/errors.js';

function client(
  fetchImplementation: typeof fetch,
  overrides: Partial<ConstructorParameters<typeof Hy3ChatClient>[0]> = {},
): Hy3ChatClient {
  return new Hy3ChatClient(
    {
      apiKey: 'synthetic-api-value',
      baseUrl: 'http://127.0.0.1:8000/v1',
      model: 'hy3-test',
      timeoutMs: 1000,
      ...overrides,
    },
    fetchImplementation,
  );
}

describe('Hy3ChatClient', () => {
  it('calls the OpenAI-compatible endpoint without exposing hidden reasoning', async () => {
    let capturedUrl = '';
    let capturedAuthorization = '';
    let capturedBody: Record<string, unknown> | undefined;
    const fetchImplementation = (async (
      input: string | URL | Request,
      init?: RequestInit,
    ) => {
      capturedUrl = String(input);
      capturedAuthorization =
        new Headers(init?.headers).get('authorization') ?? '';
      capturedBody = JSON.parse(String(init?.body)) as Record<
        string,
        unknown
      >;
      return new Response(
        JSON.stringify({
          choices: [
            {
              message: {
                content: '{"findings":[],"summary":"No findings."}',
                reasoning_content: 'internal reasoning must not be returned',
              },
            },
          ],
          usage: {
            prompt_tokens: 10,
            completion_tokens: 5,
            total_tokens: 15,
          },
        }),
        { status: 200 },
      );
    }) as typeof fetch;

    const result = await client(fetchImplementation).complete(
      [{ role: 'user', content: 'Synthetic request.' }],
      'low',
    );

    assert.equal(capturedUrl, 'http://127.0.0.1:8000/v1/chat/completions');
    assert.equal(capturedAuthorization, 'Bearer synthetic-api-value');
    assert.equal(capturedBody?.model, 'hy3-test');
    assert.deepEqual(capturedBody?.chat_template_kwargs, {
      reasoning_effort: 'low',
    });
    assert.equal(result.model, 'hy3-test');
    assert.equal(result.usage?.total_tokens, 15);
    assert.doesNotMatch(JSON.stringify(result), /internal reasoning/);
    assert.doesNotMatch(JSON.stringify(result), /synthetic-api-value/);
  });

  it('returns a sanitized error for HTTP failures', async () => {
    const credentialValue = 'synthetic-api-value';
    const fetchImplementation = (async () =>
      new Response(`provider echoed ${credentialValue}`, {
        status: 401,
      })) as typeof fetch;

    await assert.rejects(
      client(fetchImplementation).complete(
        [{ role: 'user', content: 'Synthetic request.' }],
        'no_think',
      ),
      (error: unknown) => {
        assert.ok(error instanceof Hy3ReviewError);
        assert.equal(error.code, 'http_error');
        assert.doesNotMatch(error.message, new RegExp(credentialValue));
        return true;
      },
    );
  });

  it('enforces the request setup timeout', async () => {
    const fetchImplementation = ((
      _input: string | URL | Request,
      init?: RequestInit,
    ) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new Error('synthetic abort')),
        );
      })) as typeof fetch;

    await assert.rejects(
      client(fetchImplementation, { timeoutMs: 10 }).complete(
        [{ role: 'user', content: 'Synthetic request.' }],
        'high',
      ),
      (error: unknown) =>
        error instanceof Hy3ReviewError && error.code === 'timeout',
    );
  });

  it('keeps the deadline active while reading the response body', async () => {
    const fetchImplementation = (async (
      _input: string | URL | Request,
      init?: RequestInit,
    ) =>
      new Response(
        new ReadableStream({
          start(controller) {
            init?.signal?.addEventListener('abort', () => {
              controller.error(new Error('synthetic body abort'));
            });
          },
        }),
        { status: 200 },
      )) as typeof fetch;

    await assert.rejects(
      client(fetchImplementation, { timeoutMs: 10 }).complete(
        [{ role: 'user', content: 'Synthetic request.' }],
        'high',
      ),
      (error: unknown) =>
        error instanceof Hy3ReviewError && error.code === 'timeout',
    );
  });

  it('rejects oversized and malformed provider responses', async () => {
    const oversized = (async () =>
      new Response('x', {
        status: 200,
        headers: { 'content-length': String(256 * 1024 + 1) },
      })) as typeof fetch;
    const malformed = (async () =>
      new Response('not-json', { status: 200 })) as typeof fetch;

    await assert.rejects(
      client(oversized).complete(
        [{ role: 'user', content: 'Synthetic request.' }],
        'high',
      ),
      (error: unknown) =>
        error instanceof Hy3ReviewError &&
        error.code === 'response_too_large',
    );
    await assert.rejects(
      client(malformed).complete(
        [{ role: 'user', content: 'Synthetic request.' }],
        'high',
      ),
      (error: unknown) =>
        error instanceof Hy3ReviewError &&
        error.code === 'invalid_response',
    );
  });

  it('rejects endpoint URLs containing credentials or query state', () => {
    assert.throws(
      () =>
        client((async () => new Response()) as typeof fetch, {
          baseUrl: 'https://user:password@example.invalid/v1',
        }),
      (error: unknown) =>
        error instanceof Hy3ReviewError &&
        error.code === 'invalid_configuration',
    );
    assert.throws(
      () =>
        client((async () => new Response()) as typeof fetch, {
          baseUrl: 'https://example.invalid/v1?tenant=unexpected',
        }),
      (error: unknown) =>
        error instanceof Hy3ReviewError &&
        error.code === 'invalid_configuration',
    );
  });
});
