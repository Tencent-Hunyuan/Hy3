import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { loadRuntimeConfig } from '../src/config.js';

describe('loadRuntimeConfig', () => {
  it('uses safe local defaults without exposing an API key', () => {
    const config = loadRuntimeConfig({});

    assert.deepEqual(config, {
      hy3: {
        apiKeyPresent: false,
        baseUrl: 'http://127.0.0.1:8000/v1',
        model: 'hy3',
        reasoningEffort: 'high',
        timeoutMs: 60_000,
      },
    });

    assert.deepEqual(
      loadRuntimeConfig({ HY3_API_KEY: '', MCPQ_TARGETS_FILE: '' }),
      config,
    );
  });

  it('reports key presence without retaining the key', () => {
    const config = loadRuntimeConfig({ HY3_API_KEY: 'synthetic-test-value' });

    assert.equal(config.hy3.apiKeyPresent, true);
    assert.doesNotMatch(JSON.stringify(config), /synthetic-test-value/);
  });

  it('accepts a server-level Hy3 reasoning default', () => {
    const config = loadRuntimeConfig({
      HY3_REASONING_EFFORT: 'low',
    });

    assert.equal(config.hy3.reasoningEffort, 'low');
  });

  it('rejects an invalid timeout', () => {
    assert.throws(() => loadRuntimeConfig({ HY3_TIMEOUT_MS: 'later' }));
    assert.throws(() => loadRuntimeConfig({ HY3_TIMEOUT_MS: '300001' }));
  });

  it('rejects unsafe Hy3 base URLs', () => {
    assert.throws(() =>
      loadRuntimeConfig({ HY3_BASE_URL: 'file:///private/model' }),
    );
    assert.throws(() =>
      loadRuntimeConfig({
        HY3_BASE_URL: 'https://user:password@example.invalid/v1',
      }),
    );
    assert.throws(() =>
      loadRuntimeConfig({
        HY3_BASE_URL: 'https://example.invalid/v1?api_key=synthetic',
      }),
    );
  });
});
