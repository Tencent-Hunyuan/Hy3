import { createHash } from 'node:crypto';

import type { ResolvedTarget } from '../target-registry.js';
import {
  redactSchema,
  redactText,
  redactUnknown,
} from '../security/redaction.js';
import { stableJsonStringify } from '../serialization/stable-json.js';
import {
  inspectOutputSchema,
  type InspectInput,
  type InspectOutput,
} from '../tool-contracts.js';
import { InspectionFailure, type FailureDetails } from './failure.js';
import { BoundedStdioSession } from './process-runner.js';

const REQUESTED_PROTOCOL_VERSION = '2025-11-25';
const TOOL_NAME = /^[A-Za-z0-9_.-]{1,128}$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asRecord(value: unknown): Record<string, unknown> | null {
  const redacted = redactUnknown(value);
  return isRecord(redacted) ? redacted : null;
}

function asSchemaRecord(value: unknown): Record<string, unknown> | null {
  const redacted = redactSchema(value);
  return isRecord(redacted) ? redacted : null;
}

function normalizeServerInfo(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }
  return Object.fromEntries(
    ['name', 'version', 'title']
      .filter((key) => typeof value[key] === 'string')
      .map((key) => [key, redactText(value[key] as string)]),
  );
}

function finding(targetId: string, details: FailureDetails) {
  return {
    rule_id: details.ruleId,
    severity: details.severity,
    source: 'deterministic' as const,
    message: details.message,
    suggestion: details.suggestion,
    target_id: targetId,
    tool_name: null,
    evidence_path: details.evidencePath,
    evidence_excerpt: details.evidenceExcerpt ?? null,
    confidence: null,
  };
}

function normalizeTools(rawTools: unknown[], targetId: string) {
  const findings: InspectOutput['findings'] = [];
  const seen = new Set<string>();
  const tools = rawTools.flatMap((rawTool, index) => {
    if (!isRecord(rawTool) || typeof rawTool.name !== 'string') {
      findings.push(
        finding(targetId, {
          ruleId: 'PROTO-006',
          severity: 'error',
          message: 'tools/list returned a tool without a string name',
          suggestion: 'Return MCP Tool objects with unique string names.',
          evidencePath: `/tools/${index}/name`,
        }),
      );
      return [];
    }
    const visibleName = redactText(rawTool.name);
    if (seen.has(rawTool.name)) {
      findings.push(
        finding(targetId, {
          ruleId: 'PROTO-007',
          severity: 'error',
          message: `duplicate tool name: ${visibleName}`,
          suggestion: 'Expose a unique name for every tool in one server.',
          evidencePath: `/tools/${index}/name`,
          evidenceExcerpt: visibleName,
        }),
      );
    }
    seen.add(rawTool.name);
    if (!TOOL_NAME.test(rawTool.name)) {
      findings.push(
        finding(targetId, {
          ruleId: 'PROTO-008',
          severity: 'warning',
          message: `tool name is outside the interoperability naming policy: ${visibleName}`,
          suggestion: 'Use 1-128 ASCII letters, digits, underscores, hyphens, or dots.',
          evidencePath: `/tools/${index}/name`,
          evidenceExcerpt: visibleName,
        }),
      );
    }
    const inputSchema = asSchemaRecord(rawTool.inputSchema);
    if (inputSchema === null || inputSchema.type !== 'object') {
      findings.push(
        finding(targetId, {
          ruleId: 'SCHEMA-001',
          severity: 'error',
          message: `tool ${visibleName} has no object-typed input schema`,
          suggestion: 'Declare an object inputSchema, even for a tool with no parameters.',
          evidencePath: `/tools/${index}/inputSchema`,
        }),
      );
    }
    return [
      {
        name: visibleName,
        title: typeof rawTool.title === 'string' ? redactText(rawTool.title) : null,
        description:
          typeof rawTool.description === 'string'
            ? redactText(rawTool.description)
            : null,
        input_schema: inputSchema ?? {},
        output_schema: asSchemaRecord(rawTool.outputSchema),
        annotations: asRecord(rawTool.annotations),
      },
    ];
  });

  tools.sort((left, right) =>
    left.name < right.name ? -1 : left.name > right.name ? 1 : 0,
  );
  return { tools, findings };
}

function contentHash(value: unknown): string {
  return createHash('sha256').update(stableJsonStringify(value)).digest('hex');
}

export async function inspectTarget(
  target: ResolvedTarget,
  input: InspectInput,
): Promise<InspectOutput> {
  const startedAt = performance.now();
  const session = new BoundedStdioSession(target, input.timeout_ms);
  const findings: InspectOutput['findings'] = [];
  let protocolVersion: string | null = null;
  let serverInfo: Record<string, unknown> | null = null;
  let tools: InspectOutput['tools'] = [];
  let snapshotHash: string | null = null;

  try {
    await session.start();
    const initializeResult = await session.request('initialize', {
      protocolVersion: REQUESTED_PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: {
        name: 'hy3-mcp-quality-gate-inspector',
        version: '0.1.0',
      },
    });
    if (!isRecord(initializeResult)) {
      throw new InspectionFailure({
        ruleId: 'PROTO-004',
        severity: 'error',
        message: 'initialize result is not an object',
        suggestion: 'Return a valid MCP InitializeResult object.',
        evidencePath: '/responses/initialize/result',
      });
    }
    protocolVersion =
      typeof initializeResult.protocolVersion === 'string'
        ? initializeResult.protocolVersion
        : null;
    serverInfo = normalizeServerInfo(initializeResult.serverInfo);
    if (protocolVersion === null) {
      throw new InspectionFailure({
        ruleId: 'PROTO-004',
        severity: 'error',
        message: 'initialize result omits protocolVersion',
        suggestion: 'Return the negotiated protocol version in InitializeResult.',
        evidencePath: '/responses/initialize/result/protocolVersion',
      });
    }
    if (serverInfo === null) {
      findings.push(
        finding(target.id, {
          ruleId: 'PROTO-005',
          severity: 'warning',
          message: 'initialize result omits valid serverInfo',
          suggestion: 'Return a stable server name and version.',
          evidencePath: '/responses/initialize/result/serverInfo',
        }),
      );
    }

    session.notify('notifications/initialized');
    const listResult = await session.request('tools/list', {});
    if (!isRecord(listResult) || !Array.isArray(listResult.tools)) {
      throw new InspectionFailure({
        ruleId: 'PROTO-006',
        severity: 'error',
        message: 'tools/list result does not contain a tools array',
        suggestion: 'Return an MCP ListToolsResult with a tools array.',
        evidencePath: '/responses/tools~1list/result/tools',
      });
    }
    const normalized = normalizeTools(listResult.tools, target.id);
    tools = normalized.tools;
    findings.push(...normalized.findings);
    snapshotHash = contentHash({ protocolVersion, serverInfo, tools });
  } catch (error: unknown) {
    const failure =
      error instanceof InspectionFailure
        ? error
        : new InspectionFailure({
            ruleId: 'PROTO-004',
            severity: 'error',
            message: 'target inspection failed unexpectedly',
            suggestion: 'Review the target lifecycle and JSON-RPC responses.',
            evidencePath: '/inspection',
          });
    findings.push(finding(target.id, failure.details));
  } finally {
    try {
      await session.close();
    } catch (error: unknown) {
      const failure =
        error instanceof InspectionFailure
          ? error
          : new InspectionFailure({
              ruleId: 'ROBUST-003',
              severity: 'critical',
              message: 'target cleanup failed',
              suggestion: 'Review process-group cleanup for this platform.',
              evidencePath: '/lifecycle/terminate',
            });
      findings.push(finding(target.id, failure.details));
    }
  }

  const hasError = findings.some(
    (item) => item.severity === 'error' || item.severity === 'critical',
  );
  const inspectionComplete = snapshotHash !== null;
  const visibleTools = input.include_schemas
    ? tools
    : tools.map((tool) => ({
        ...tool,
        input_schema: {},
        output_schema: null,
      }));
  return inspectOutputSchema.parse({
    status: hasError || !inspectionComplete ? 'fail' : 'pass',
    target_id: target.id,
    protocol_version: protocolVersion,
    server_info: serverInfo,
    tools: visibleTools,
    snapshot_hash: snapshotHash,
    findings,
    duration_ms: Math.max(0, Math.round(performance.now() - startedAt)),
  });
}
