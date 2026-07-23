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
  });

  it('reports key presence without retaining the key', () => {
    const config = loadRuntimeConfig({ HY3_API_KEY: 'synthetic-test-value' });

    assert.equal(config.hy3.apiKeyPresent, true);
    assert.doesNotMatch(JSON.stringify(config), /synthetic-test-value/);
  });

  it('rejects an invalid timeout', () => {
    assert.throws(() => loadRuntimeConfig({ HY3_TIMEOUT_MS: 'later' }));
  });
});
