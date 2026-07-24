const CREDENTIAL_KEY =
  /(?:^|[_-])(?:api[_-]?key|auth|credential|password|private[_-]?key|secret|token)(?:$|[_-])/i;
const CREDENTIAL_VALUE =
  /(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|(?:bearer|token)\s+[A-Za-z0-9._~+\/-]{12,})/gi;
const PRIVATE_KEY_BLOCK =
  /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/gi;
const HOME_PATH = /(?:\/Users\/|\/home\/)[^/\s"']+/g;
const WINDOWS_HOME_PATH = /[A-Za-z]:\\Users\\[^\\\s"']+/g;

const MAX_REDACTION_DEPTH = 32;

export function isCredentialLikeKey(key: string): boolean {
  const normalized = key.replace(/([a-z0-9])([A-Z])/g, '$1_$2');
  return CREDENTIAL_KEY.test(normalized);
}

export function containsCredentialLikeValue(value: string): boolean {
  CREDENTIAL_VALUE.lastIndex = 0;
  PRIVATE_KEY_BLOCK.lastIndex = 0;
  return CREDENTIAL_VALUE.test(value) || PRIVATE_KEY_BLOCK.test(value);
}

export function redactText(value: string): string {
  CREDENTIAL_VALUE.lastIndex = 0;
  PRIVATE_KEY_BLOCK.lastIndex = 0;
  return value
    .replace(PRIVATE_KEY_BLOCK, '[REDACTED_PRIVATE_KEY]')
    .replace(CREDENTIAL_VALUE, '[REDACTED_CREDENTIAL]')
    .replace(HOME_PATH, '[REDACTED_HOME]')
    .replace(WINDOWS_HOME_PATH, '[REDACTED_HOME]');
}

export function redactUnknown(value: unknown, depth = 0): unknown {
  if (depth >= MAX_REDACTION_DEPTH) {
    return '[REDACTED_DEPTH_LIMIT]';
  }
  if (typeof value === 'string') {
    return redactText(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => redactUnknown(item, depth + 1));
  }
  if (typeof value === 'object' && value !== null) {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        isCredentialLikeKey(key)
          ? '[REDACTED_CREDENTIAL]'
          : redactUnknown(item, depth + 1),
      ]),
    );
  }
  return value;
}

const SENSITIVE_SCHEMA_VALUE_KEYS = new Set([
  'const',
  'default',
  'enum',
  'example',
  'examples',
]);

export function redactSchema(
  value: unknown,
  sensitiveParameter = false,
  depth = 0,
): unknown {
  if (depth >= MAX_REDACTION_DEPTH) {
    return '[REDACTED_DEPTH_LIMIT]';
  }
  if (typeof value === 'string') {
    return redactText(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) =>
      redactSchema(item, sensitiveParameter, depth + 1),
    );
  }
  if (typeof value !== 'object' || value === null) {
    return value;
  }

  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => {
      if (sensitiveParameter && SENSITIVE_SCHEMA_VALUE_KEYS.has(key)) {
        return [
          key,
          Array.isArray(item)
            ? item.map((_, index) => `[REDACTED_CREDENTIAL_${index}]`)
            : '[REDACTED_CREDENTIAL]',
        ];
      }
      if (key === 'properties' && typeof item === 'object' && item !== null) {
        return [
          key,
          Object.fromEntries(
            Object.entries(item).map(([propertyName, propertySchema]) => [
              propertyName,
              redactSchema(
                propertySchema,
                isCredentialLikeKey(propertyName),
                depth + 2,
              ),
            ]),
          ),
        ];
      }
      return [key, redactSchema(item, sensitiveParameter, depth + 1)];
    }),
  );
}
