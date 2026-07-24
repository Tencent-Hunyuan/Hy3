import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { describe, it } from 'node:test';

import {
  evaluationManifestSchema,
  evaluationReportSchema,
  runEvaluation,
} from '../src/evaluation/evaluate.js';

const packageRoot = process.cwd();

async function readJson(path: string): Promise<unknown> {
  return JSON.parse(await readFile(path, 'utf8')) as unknown;
}

describe('evaluation suite', () => {
  it('reproduces the committed Stage 7 baseline without a live Hy3 key', async () => {
    const manifest = evaluationManifestSchema.parse(
      await readJson(resolve(packageRoot, 'evaluation/manifest.json')),
    );
    const baseline = evaluationReportSchema.parse(
      await readJson(resolve(packageRoot, manifest.baseline_file)),
    );

    const report = await runEvaluation(packageRoot, manifest);

    assert.deepEqual(report, baseline);
    assert.equal(report.case_count, 10);
    assert.equal(report.metrics.status_accuracy, 1);
    assert.equal(report.metrics.exact_rule_set_accuracy, 1);
    assert.equal(report.metrics.rule_precision, 1);
    assert.equal(report.metrics.rule_recall, 1);
    assert.equal(report.metrics.rule_f1, 1);
    assert.equal(report.metrics.probe_policy_accuracy, 1);
    assert.equal(report.metrics.true_positive_rules, 24);
    assert.equal(report.metrics.false_positive_rules, 0);
    assert.equal(report.metrics.false_negative_rules, 0);
    assert.equal(report.passed, true);
  });

  it('rejects path traversal and duplicate evaluation case IDs', async () => {
    const raw = (await readJson(
      resolve(packageRoot, 'evaluation/manifest.json'),
    )) as Record<string, unknown>;
    assert.throws(() =>
      evaluationManifestSchema.parse({
        ...raw,
        targets_file: '../private-targets.json',
      }),
    );

    const cases = raw.cases;
    assert.ok(Array.isArray(cases));
    const first = cases[0];
    assert.ok(first);
    assert.throws(() =>
      evaluationManifestSchema.parse({
        ...raw,
        cases: [first, first],
      }),
    );
  });
});
