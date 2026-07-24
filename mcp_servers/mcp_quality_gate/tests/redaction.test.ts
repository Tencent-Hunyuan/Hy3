import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  containsCredentialLikeValue,
  isCredentialLikeKey,
  redactSchema,
  redactText,
  redactUnknown,
} from '../src/security/redaction.js';

describe('redaction', () => {
  it('redacts credential-shaped values and user home paths', () => {
    const credential = ['sk', 'abcdefghijklmnop'].join('-');
    const githubCredential = ['ghp', 'a'.repeat(20)].join('_');
    const result = redactText(
      `credential=${credential} github=${githubCredential} path=/Users/example/private/config.json`,
    );

    assert.equal(result.includes(credential), false);
    assert.equal(result.includes(githubCredential), false);
    assert.equal(result.includes('/Users/example'), false);
    assert.match(result, /REDACTED_CREDENTIAL/);
    assert.match(result, /REDACTED_HOME/);
    assert.equal(containsCredentialLikeValue(credential), true);
    assert.equal(isCredentialLikeKey('accessToken'), true);
  });

  it('redacts values under secret-like object keys recursively', () => {
    const result = redactUnknown({
      schema: {
        properties: {
          password: { default: 'synthetic-value' },
          ordinary: { default: 'visible-value' },
        },
      },
    });

    assert.deepEqual(result, {
      schema: {
        properties: {
          password: '[REDACTED_CREDENTIAL]',
          ordinary: { default: 'visible-value' },
        },
      },
    });
  });

  it('preserves credential parameter schemas while redacting their values', () => {
    const result = redactSchema({
      type: 'object',
      properties: {
        api_key: {
          type: 'string',
          description: 'Credential used by the synthetic fixture.',
          default: 'synthetic-value',
          examples: ['first-value', 'second-value'],
        },
      },
      required: ['api_key'],
    });

    assert.deepEqual(result, {
      type: 'object',
      properties: {
        api_key: {
          type: 'string',
          description: 'Credential used by the synthetic fixture.',
          default: '[REDACTED_CREDENTIAL]',
          examples: [
            '[REDACTED_CREDENTIAL_0]',
            '[REDACTED_CREDENTIAL_1]',
          ],
        },
      },
      required: ['api_key'],
    });
  });
});
