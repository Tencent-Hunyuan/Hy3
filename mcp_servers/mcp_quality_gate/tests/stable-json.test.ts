import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { describe, it } from 'node:test';

import { stableJsonStringify } from '../src/serialization/stable-json.js';

function hash(value: unknown): string {
  return createHash('sha256').update(stableJsonStringify(value)).digest('hex');
}

describe('stable JSON serialization', () => {
  it('produces the same representation for equivalent object key orders', () => {
    const left = {
      server: { version: '1.0.0', name: 'fixture' },
      tools: [
        {
          name: 'echo',
          input_schema: {
            required: ['text'],
            properties: { text: { description: 'Text.', type: 'string' } },
            type: 'object',
          },
        },
      ],
    };
    const right = {
      tools: [
        {
          input_schema: {
            type: 'object',
            properties: { text: { type: 'string', description: 'Text.' } },
            required: ['text'],
          },
          name: 'echo',
        },
      ],
      server: { name: 'fixture', version: '1.0.0' },
    };

    assert.equal(stableJsonStringify(left), stableJsonStringify(right));
    assert.equal(hash(left), hash(right));
  });

  it('preserves array order because it is contract-significant', () => {
    assert.notEqual(
      stableJsonStringify({ enum: ['first', 'second'] }),
      stableJsonStringify({ enum: ['second', 'first'] }),
    );
  });
});
