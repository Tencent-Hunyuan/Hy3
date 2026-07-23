export type Hy3ReviewErrorCode =
  | 'context_too_large'
  | 'http_error'
  | 'invalid_configuration'
  | 'invalid_output'
  | 'invalid_response'
  | 'network_error'
  | 'response_too_large'
  | 'secret_detected'
  | 'timeout';

export class Hy3ReviewError extends Error {
  readonly code: Hy3ReviewErrorCode;

  constructor(code: Hy3ReviewErrorCode) {
    super(`Hy3 semantic review failed with code: ${code}`);
    this.name = 'Hy3ReviewError';
    this.code = code;
  }
}
