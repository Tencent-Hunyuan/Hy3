import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { describe, it } from 'node:test';

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

import { Hy3ChatClient } from '../src/hy3/client.js';
import { Hy3ProbeGenerator } from '../src/hy3/probe-generator.js';
import { Hy3SemanticReviewer } from '../src/hy3/reviewer.js';
import { createServer } from '../src/server.js';
import { TargetRegistry } from '../src/target-registry.js';
import { createToolHandlers } from '../src/tools/inspection-handler.js';

const serverEntry = resolve(process.cwd(), 'dist/src/index.js');
const exampleRegistry = resolve(process.cwd(), 'examples/targets.example.json');

describe('stdio server', () => {
  it('initializes and exposes exactly the four planned tools', async () => {
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntry],
      stderr: 'pipe',
    });

    try {
      await client.connect(transport);
      const { tools } = await client.listTools();

      assert.deepEqual(
        tools.map((tool) => tool.name).sort(),
        [
          'mcpq_audit_contracts',
          'mcpq_compare_contracts',
          'mcpq_generate_probe_suite',
          'mcpq_inspect_server',
        ],
      );
      for (const tool of tools) {
        assert.ok((tool.description?.length ?? 0) > 60);
        assert.equal(tool.inputSchema.type, 'object');
        assert.equal(tool.outputSchema?.type, 'object');
        assert.equal(tool.annotations?.readOnlyHint, true);
      }
    } finally {
      await client.close();
    }
  });

  it('returns a controlled error for an unknown comparison target', async () => {
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntry],
      stderr: 'pipe',
    });

    try {
      await client.connect(transport);
      const result = await client.callTool({
        name: 'mcpq_compare_contracts',
        arguments: {
          baseline_target_id: 'fixture-good',
          current_target_id: 'fixture-current',
        },
      });

      assert.equal(result.isError, true);
    } finally {
      await client.close();
    }
  });

  it('publishes comparison arguments at the JSON Schema top level', async () => {
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntry],
      stderr: 'pipe',
    });

    try {
      await client.connect(transport);
      const { tools } = await client.listTools();
      const comparison = tools.find(
        (tool) => tool.name === 'mcpq_compare_contracts',
      );

      assert.ok(comparison);
      assert.equal(comparison.inputSchema.type, 'object');
      assert.deepEqual(comparison.inputSchema.required, [
        'baseline_target_id',
        'current_target_id',
      ]);
      assert.ok(
        comparison.inputSchema.properties &&
          'baseline_target_id' in comparison.inputSchema.properties &&
          'current_target_id' in comparison.inputSchema.properties,
      );
    } finally {
      await client.close();
    }
  });

  it('rejects a comparison of the same registered target', async () => {
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntry],
      env: { MCPQ_TARGETS_FILE: exampleRegistry },
      stderr: 'pipe',
    });

    try {
      await client.connect(transport);
      const result = await client.callTool({
        name: 'mcpq_compare_contracts',
        arguments: {
          baseline_target_id: 'fixture-good',
          current_target_id: 'fixture-good',
          include_hy3: false,
        },
      });

      assert.equal(result.isError, true);
      assert.ok(Array.isArray(result.content));
      const firstContent = result.content[0] as
        | { type?: unknown; text?: unknown }
        | undefined;
      assert.equal(firstContent?.type, 'text');
      assert.match(String(firstContent?.text), /must differ/);
    } finally {
      await client.close();
    }
  });

  it('calls the working inspector through the complete MCP stdio chain', async () => {
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntry],
      env: { MCPQ_TARGETS_FILE: exampleRegistry },
      stderr: 'pipe',
    });

    try {
      await client.connect(transport);
      const good = await client.callTool({
        name: 'mcpq_inspect_server',
        arguments: { target_id: 'fixture-good' },
      });
      const polluted = await client.callTool({
        name: 'mcpq_inspect_server',
        arguments: { target_id: 'fixture-stdout-pollution' },
      });
      const goodContent = good.structuredContent as
        | { status: string; tools: Array<{ name: string }> }
        | undefined;
      const pollutedContent = polluted.structuredContent as
        | { status: string; findings: Array<{ rule_id: string }> }
        | undefined;

      assert.equal(good.isError, undefined);
      assert.ok(goodContent);
      assert.equal(goodContent.status, 'pass');
      assert.deepEqual(
        goodContent.tools.map((tool) => tool.name),
        ['fixture_echo', 'fixture_sum'],
      );
      assert.ok(pollutedContent);
      assert.equal(pollutedContent.status, 'fail');
      assert.ok(
        pollutedContent.findings.some((item) => item.rule_id === 'PROTO-002'),
      );
    } finally {
      await client.close();
    }
  });

  it('calls the deterministic audit through the complete MCP stdio chain', async () => {
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntry],
      env: { MCPQ_TARGETS_FILE: exampleRegistry },
      stderr: 'pipe',
    });

    try {
      await client.connect(transport);
      const good = await client.callTool({
        name: 'mcpq_audit_contracts',
        arguments: {
          target_id: 'fixture-good',
          include_hy3: false,
        },
      });
      const bad = await client.callTool({
        name: 'mcpq_audit_contracts',
        arguments: {
          target_id: 'fixture-audit-bad',
          include_hy3: false,
        },
      });
      const goodContent = good.structuredContent as
        | {
            status: string;
            scorecard: { overall: number };
            catalog_version: string;
          }
        | undefined;
      const badContent = bad.structuredContent as
        | {
            status: string;
            scorecard: { overall: number };
            deterministic_findings: Array<{ rule_id: string }>;
          }
        | undefined;

      assert.equal(good.isError, undefined);
      assert.ok(goodContent);
      assert.equal(goodContent.status, 'pass');
      assert.equal(goodContent.scorecard.overall, 100);
      assert.equal(goodContent.catalog_version, '1.0.0');
      assert.equal(bad.isError, undefined);
      assert.ok(badContent);
      assert.equal(badContent.status, 'fail');
      assert.ok(badContent.scorecard.overall < 100);
      assert.ok(
        badContent.deterministic_findings.some(
          (finding) => finding.rule_id === 'SAFETY-001',
        ),
      );
    } finally {
      await client.close();
    }
  });

  it('calls deterministic comparison through the complete MCP stdio chain', async () => {
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [serverEntry],
      env: { MCPQ_TARGETS_FILE: exampleRegistry },
      stderr: 'pipe',
    });

    try {
      await client.connect(transport);
      const result = await client.callTool({
        name: 'mcpq_compare_contracts',
        arguments: {
          baseline_target_id: 'fixture-compat-baseline',
          current_target_id: 'fixture-compat-breaking',
          include_hy3: false,
        },
      });
      const content = result.structuredContent as
        | {
            status: string;
            changes: Array<{ rule_id: string }>;
            findings: Array<{ rule_id: string; source: string }>;
          }
        | undefined;

      assert.equal(result.isError, undefined);
      assert.ok(content);
      assert.equal(content.status, 'breaking');
      assert.ok(
        content.changes.some(
          (change) => change.rule_id === 'COMPAT-003',
        ),
      );
      assert.ok(
        content.findings.every(
          (finding) => finding.source === 'deterministic',
        ),
      );
    } finally {
      await client.close();
    }
  });

  it('calls Hy3 through the complete MCP audit chain', async () => {
    let authorization = '';
    let requestBody: Record<string, unknown> | undefined;
    const fetchImplementation = (async (
      _input: string | URL | Request,
      init?: RequestInit,
    ) => {
      authorization =
        new Headers(init?.headers).get('authorization') ?? '';
      requestBody = JSON.parse(String(init?.body)) as Record<
        string,
        unknown
      >;
      return new Response(
        JSON.stringify({
          choices: [
            {
              message: {
                content: JSON.stringify({
                  findings: [
                    {
                      rule_id: 'DOC-003',
                      message:
                        'The synthetic echo description leaves the output identity slightly ambiguous.',
                      suggestion:
                        'Clarify that the returned text is exactly the provided input text.',
                      tool_name: 'fixture_echo',
                      evidence_path: '/tools/0/description',
                      confidence: 0.8,
                    },
                  ],
                  summary:
                    'One evidence-backed semantic issue was identified.',
                }),
                reasoning_content:
                  'This internal field must never reach the MCP result.',
              },
            },
          ],
          usage: {
            prompt_tokens: 40,
            completion_tokens: 20,
            total_tokens: 60,
          },
        }),
        { status: 200 },
      );
    }) as typeof fetch;
    const registry = await TargetRegistry.load(exampleRegistry);
    const reviewer = new Hy3SemanticReviewer(
      new Hy3ChatClient(
        {
          apiKey: 'synthetic-e2e-value',
          baseUrl: 'http://127.0.0.1:8000/v1',
          model: 'hy3-e2e',
          timeoutMs: 5000,
        },
        fetchImplementation,
      ),
      'low',
    );
    const qualityGate = createServer(
      createToolHandlers(registry, { semanticReviewer: reviewer }),
    );
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const [clientTransport, serverTransport] =
      InMemoryTransport.createLinkedPair();

    try {
      await qualityGate.connect(serverTransport);
      await client.connect(clientTransport);
      const result = await client.callTool({
        name: 'mcpq_audit_contracts',
        arguments: {
          target_id: 'fixture-good',
          include_hy3: true,
        },
      });
      const content = result.structuredContent as
        | {
            status: string;
            scorecard: { overall: number; hy3_reviewed: boolean };
            hy3_findings: Array<{
              rule_id: string;
              source: string;
              confidence: number;
            }>;
            model_metadata: {
              model: string;
              reasoning_effort: string;
              attempts: number;
            } | null;
          }
        | undefined;

      assert.equal(result.isError, undefined);
      assert.ok(content);
      assert.equal(content.status, 'pass');
      assert.equal(content.scorecard.overall, 100);
      assert.equal(content.scorecard.hy3_reviewed, true);
      assert.equal(content.hy3_findings[0]?.rule_id, 'DOC-003');
      assert.equal(content.hy3_findings[0]?.source, 'hy3');
      assert.equal(content.hy3_findings[0]?.confidence, 0.8);
      assert.equal(content.model_metadata?.model, 'hy3-e2e');
      assert.equal(content.model_metadata?.reasoning_effort, 'low');
      assert.equal(content.model_metadata?.attempts, 1);
      assert.equal(authorization, 'Bearer synthetic-e2e-value');
      assert.deepEqual(requestBody?.chat_template_kwargs, {
        reasoning_effort: 'low',
      });
      assert.doesNotMatch(
        JSON.stringify(content),
        /internal field must never reach/,
      );
      assert.doesNotMatch(
        JSON.stringify(content),
        /synthetic-e2e-value/,
      );
    } finally {
      await client.close();
      await qualityGate.close();
    }
  });

  it('generates validated inert probes through the complete MCP chain', async () => {
    let requestBody: Record<string, unknown> | undefined;
    const fetchImplementation = (async (
      _input: string | URL | Request,
      init?: RequestInit,
    ) => {
      requestBody = JSON.parse(String(init?.body)) as Record<
        string,
        unknown
      >;
      return new Response(
        JSON.stringify({
          choices: [
            {
              message: {
                content: JSON.stringify({
                  cases: [
                    {
                      category: 'normal',
                      purpose:
                        'Verify an ordinary harmless synthetic echo operation.',
                      arguments: { text: 'synthetic hello' },
                      expected_outcome: 'success',
                      safety_note:
                        'This case contains inert synthetic data only.',
                      evidence_path:
                        '/input_schema/properties/text',
                    },
                  ],
                }),
                reasoning_content:
                  'This internal field must never reach the MCP result.',
              },
            },
          ],
        }),
        { status: 200 },
      );
    }) as typeof fetch;
    const registry = await TargetRegistry.load(exampleRegistry);
    const probeGenerator = new Hy3ProbeGenerator(
      new Hy3ChatClient(
        {
          apiKey: 'synthetic-probe-e2e-value',
          baseUrl: 'http://127.0.0.1:8000/v1',
          model: 'hy3-probe-e2e',
          timeoutMs: 5000,
        },
        fetchImplementation,
      ),
      'low',
    );
    const qualityGate = createServer(
      createToolHandlers(registry, { probeGenerator }),
    );
    const client = new Client({ name: 'quality-gate-test', version: '0.1.0' });
    const [clientTransport, serverTransport] =
      InMemoryTransport.createLinkedPair();

    try {
      await qualityGate.connect(serverTransport);
      await client.connect(clientTransport);
      const result = await client.callTool({
        name: 'mcpq_generate_probe_suite',
        arguments: {
          target_id: 'fixture-good',
          tool_name: 'fixture_echo',
          profile: 'normal',
          max_cases: 3,
        },
      });
      const content = result.structuredContent as
        | {
            status: string;
            cases: Array<{
              id: string;
              evidence_path: string;
            }>;
            model_metadata: { reasoning_effort: string };
          }
        | undefined;

      assert.equal(result.isError, undefined);
      assert.ok(content);
      assert.equal(content.status, 'complete');
      assert.equal(content.cases.length, 1);
      assert.match(content.cases[0]?.id ?? '', /^probe-[a-f0-9]{16}$/);
      assert.equal(
        content.cases[0]?.evidence_path,
        '/tools/0/input_schema/properties/text',
      );
      assert.equal(content.model_metadata.reasoning_effort, 'low');
      assert.deepEqual(requestBody?.chat_template_kwargs, {
        reasoning_effort: 'low',
      });
      assert.doesNotMatch(
        JSON.stringify(content),
        /internal field must never reach/,
      );
    } finally {
      await client.close();
      await qualityGate.close();
    }
  });
});
