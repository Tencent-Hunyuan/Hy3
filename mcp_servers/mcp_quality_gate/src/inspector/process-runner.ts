import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process';
import { StringDecoder } from 'node:string_decoder';

import type { ResolvedTarget } from '../target-registry.js';
import { redactText } from '../security/redaction.js';
import { InspectionFailure } from './failure.js';

type JsonRpcId = number | string;

type PendingRequest = {
  method: string;
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  timer: NodeJS.Timeout;
};

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export class BoundedStdioSession {
  readonly #target: ResolvedTarget;
  readonly #effectiveTimeoutMs: number;
  readonly #pending = new Map<JsonRpcId, PendingRequest>();
  readonly #decoder = new StringDecoder('utf8');
  #child: ChildProcessWithoutNullStreams | undefined;
  #nextId = 1;
  #stdoutBytes = 0;
  #stderrBytes = 0;
  #stdoutBuffer = '';
  #stderrBuffer = '';
  #terminalFailure: InspectionFailure | undefined;
  #totalTimer: NodeJS.Timeout | undefined;
  #closing = false;
  #exitPromise: Promise<void> | undefined;

  constructor(target: ResolvedTarget, requestedTimeoutMs?: number) {
    this.#target = target;
    this.#effectiveTimeoutMs = Math.min(
      requestedTimeoutMs ?? target.limits.total_timeout_ms,
      target.limits.total_timeout_ms,
    );
  }

  get stderrExcerpt(): string | null {
    const trimmed = this.#stderrBuffer.trim();
    return trimmed.length === 0 ? null : redactText(trimmed.slice(0, 2000));
  }

  async start(): Promise<void> {
    const child = spawn(this.#target.command, [...this.#target.args], {
      cwd: this.#target.cwd,
      env: this.#target.environment,
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: false,
      detached: process.platform !== 'win32',
      windowsHide: true,
    });
    this.#child = child;
    this.#exitPromise = new Promise((resolveExit) => {
      child.once('exit', () => {
        resolveExit();
      });
    });

    child.stdout.on('data', (chunk: Buffer) => this.#acceptStdout(chunk));
    child.stderr.on('data', (chunk: Buffer) => this.#acceptStderr(chunk));
    child.stdin.on('error', () => {
      this.#fail(
        new InspectionFailure({
          ruleId: 'PROTO-001',
          severity: 'critical',
          message: 'target process input stream failed',
          suggestion: 'Ensure the target keeps stdin open for the inspection session.',
          evidencePath: '/lifecycle/stdin',
        }),
      );
    });
    child.once('error', () => {
      this.#fail(
        new InspectionFailure({
          ruleId: 'PROTO-001',
          severity: 'critical',
          message: 'target process failed to start',
          suggestion: 'Verify the configured executable, arguments, cwd, and permissions.',
          evidencePath: '/lifecycle/spawn',
        }),
      );
    });
    child.once('exit', (code, signal) => {
      if (!this.#closing && this.#terminalFailure === undefined) {
        this.#fail(
          new InspectionFailure({
            ruleId: 'ROBUST-004',
            severity: 'warning',
            message: `target exited before inspection completed (code=${String(code)}, signal=${String(signal)})`,
            suggestion: 'Keep the stdio server alive until its input stream closes.',
            evidencePath: '/lifecycle/exit',
          }),
        );
      }
    });

    await new Promise<void>((resolveSpawn, rejectSpawn) => {
      const timer = setTimeout(() => {
        rejectSpawn(
          new InspectionFailure({
            ruleId: 'PROTO-001',
            severity: 'critical',
            message: 'target process did not start before the deadline',
            suggestion: 'Reduce startup work or increase the bounded registry startup timeout.',
            evidencePath: '/lifecycle/spawn',
          }),
        );
      }, Math.min(this.#target.limits.startup_timeout_ms, this.#effectiveTimeoutMs));
      child.once('spawn', () => {
        clearTimeout(timer);
        resolveSpawn();
      });
      child.once('error', () => {
        clearTimeout(timer);
        rejectSpawn(
          new InspectionFailure({
            ruleId: 'PROTO-001',
            severity: 'critical',
            message: 'target process failed to start',
            suggestion: 'Verify the configured executable, arguments, cwd, and permissions.',
            evidencePath: '/lifecycle/spawn',
          }),
        );
      });
    });

    this.#totalTimer = setTimeout(() => {
      this.#fail(
        new InspectionFailure({
          ruleId: 'ROBUST-001',
          severity: 'error',
          message: 'target exceeded the total inspection lifetime',
          suggestion: 'Bound initialization and discovery work or use a stricter target configuration.',
          evidencePath: '/limits/total_timeout_ms',
          evidenceExcerpt: String(this.#effectiveTimeoutMs),
        }),
      );
    }, this.#effectiveTimeoutMs);
  }

  async request(method: string, params: Record<string, unknown>): Promise<unknown> {
    this.#throwTerminalFailure();
    const child = this.#requireChild();
    const id = this.#nextId++;
    const requestTimeoutMs = Math.min(
      this.#target.limits.request_timeout_ms,
      this.#effectiveTimeoutMs,
    );

    const response = new Promise<unknown>((resolveResponse, rejectResponse) => {
      const timer = setTimeout(() => {
        this.#pending.delete(id);
        rejectResponse(
          new InspectionFailure({
            ruleId: method === 'initialize' ? 'PROTO-004' : 'PROTO-006',
            severity: 'error',
            message: `${method} did not respond before the deadline`,
            suggestion: 'Ensure the target reads newline-delimited JSON-RPC and responds promptly.',
            evidencePath: `/requests/${method}/timeout`,
            evidenceExcerpt: String(requestTimeoutMs),
          }),
        );
      }, requestTimeoutMs);
      this.#pending.set(id, {
        method,
        resolve: resolveResponse,
        reject: rejectResponse,
        timer,
      });
    });

    child.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', id, method, params })}\n`);
    return response;
  }

  notify(method: string, params: Record<string, unknown> = {}): void {
    this.#throwTerminalFailure();
    this.#requireChild().stdin.write(
      `${JSON.stringify({ jsonrpc: '2.0', method, params })}\n`,
    );
  }

  async close(): Promise<void> {
    this.#closing = true;
    if (this.#totalTimer !== undefined) {
      clearTimeout(this.#totalTimer);
    }
    for (const pending of this.#pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(new Error('inspection session closed'));
    }
    this.#pending.clear();

    const child = this.#child;
    if (
      child === undefined ||
      child.pid === undefined ||
      child.exitCode !== null ||
      child.signalCode !== null
    ) {
      return;
    }
    child.stdin.end();
    await Promise.race([this.#exitPromise ?? Promise.resolve(), delay(200)]);
    if (child.exitCode === null && child.signalCode === null) {
      this.#killTree('SIGTERM');
      await Promise.race([this.#exitPromise ?? Promise.resolve(), delay(500)]);
    }
    if (child.exitCode === null && child.signalCode === null) {
      this.#killTree('SIGKILL');
      await Promise.race([this.#exitPromise ?? Promise.resolve(), delay(1000)]);
    }
    if (child.exitCode === null && child.signalCode === null) {
      throw new InspectionFailure({
        ruleId: 'ROBUST-003',
        severity: 'critical',
        message: 'target process could not be terminated after inspection',
        suggestion: 'Review platform process-group handling before inspecting this target.',
        evidencePath: '/lifecycle/terminate',
      });
    }
  }

  #acceptStdout(chunk: Buffer): void {
    this.#stdoutBytes += chunk.byteLength;
    if (this.#stdoutBytes > this.#target.limits.max_stdout_bytes) {
      this.#fail(
        new InspectionFailure({
          ruleId: 'ROBUST-002',
          severity: 'error',
          message: 'target stdout exceeded its configured byte limit',
          suggestion: 'Bound protocol output and move diagnostics to stderr.',
          evidencePath: '/limits/max_stdout_bytes',
          evidenceExcerpt: String(this.#target.limits.max_stdout_bytes),
        }),
      );
      return;
    }

    this.#stdoutBuffer += this.#decoder.write(chunk);
    let newline = this.#stdoutBuffer.indexOf('\n');
    while (newline >= 0) {
      const line = this.#stdoutBuffer.slice(0, newline).replace(/\r$/, '');
      this.#stdoutBuffer = this.#stdoutBuffer.slice(newline + 1);
      if (line.length > 0) {
        this.#acceptLine(line);
      }
      newline = this.#stdoutBuffer.indexOf('\n');
    }
  }

  #acceptStderr(chunk: Buffer): void {
    this.#stderrBytes += chunk.byteLength;
    if (this.#stderrBytes > this.#target.limits.max_stderr_bytes) {
      this.#fail(
        new InspectionFailure({
          ruleId: 'ROBUST-002',
          severity: 'error',
          message: 'target stderr exceeded its configured byte limit',
          suggestion: 'Bound diagnostic output emitted during initialization and discovery.',
          evidencePath: '/limits/max_stderr_bytes',
          evidenceExcerpt: String(this.#target.limits.max_stderr_bytes),
        }),
      );
      return;
    }
    if (this.#stderrBuffer.length < 2000) {
      this.#stderrBuffer += chunk.toString('utf8').slice(0, 2000 - this.#stderrBuffer.length);
    }
  }

  #acceptLine(line: string): void {
    let message: unknown;
    try {
      message = JSON.parse(line) as unknown;
    } catch {
      const looksLikeJson = /^[{[]/.test(line.trimStart());
      this.#fail(
        new InspectionFailure({
          ruleId: looksLikeJson ? 'PROTO-003' : 'PROTO-002',
          severity: looksLikeJson ? 'critical' : 'error',
          message: looksLikeJson
            ? 'target stdout contains malformed JSON-RPC data'
            : 'target stdout contains non-protocol log output',
          suggestion: 'Emit only newline-delimited JSON-RPC on stdout and move logs to stderr.',
          evidencePath: `/stdout/bytes/${Math.max(0, this.#stdoutBytes - Buffer.byteLength(line))}`,
          evidenceExcerpt: redactText(line.slice(0, 200)),
        }),
      );
      return;
    }
    if (!isRecord(message) || message.jsonrpc !== '2.0') {
      this.#fail(
        new InspectionFailure({
          ruleId: 'PROTO-003',
          severity: 'critical',
          message: 'target stdout message is not a JSON-RPC 2.0 object',
          suggestion: 'Return JSON-RPC 2.0 responses with matching request IDs.',
          evidencePath: '/stdout/message',
          evidenceExcerpt: redactText(line.slice(0, 200)),
        }),
      );
      return;
    }
    const id = message.id;
    if (typeof id !== 'number' && typeof id !== 'string') {
      return;
    }
    const pending = this.#pending.get(id);
    if (pending === undefined) {
      return;
    }
    clearTimeout(pending.timer);
    this.#pending.delete(id);
    if (isRecord(message.error)) {
      pending.reject(
        new InspectionFailure({
          ruleId: pending.method === 'initialize' ? 'PROTO-004' : 'PROTO-006',
          severity: 'error',
          message: `target returned a JSON-RPC error for ${pending.method}`,
          suggestion: 'Return a successful protocol response for inspection requests.',
          evidencePath: `/responses/${pending.method.replace('/', '~1')}/error`,
          ...(typeof message.error.code === 'number'
            ? { evidenceExcerpt: String(message.error.code) }
            : {}),
        }),
      );
      return;
    }
    pending.resolve(message.result);
  }

  #fail(failure: InspectionFailure): void {
    if (this.#terminalFailure !== undefined) {
      return;
    }
    this.#terminalFailure = failure;
    for (const pending of this.#pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(failure);
    }
    this.#pending.clear();
    this.#killTree('SIGTERM');
  }

  #killTree(signal: NodeJS.Signals): void {
    const child = this.#child;
    if (child === undefined || child.pid === undefined) {
      return;
    }
    try {
      if (process.platform === 'win32') {
        child.kill(signal);
      } else {
        process.kill(-child.pid, signal);
      }
    } catch {
      // The process may already have exited; close() verifies the final state.
    }
  }

  #throwTerminalFailure(): void {
    if (this.#terminalFailure !== undefined) {
      throw this.#terminalFailure;
    }
  }

  #requireChild(): ChildProcessWithoutNullStreams {
    if (this.#child === undefined) {
      throw new Error('target session has not started');
    }
    return this.#child;
  }
}
