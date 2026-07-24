#!/usr/bin/env node

import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

import {
  evaluationManifestSchema,
  evaluationReportSchema,
  runEvaluation,
} from './evaluate.js';

async function readJson(path: string): Promise<unknown> {
  return JSON.parse(await readFile(path, 'utf8')) as unknown;
}

async function main(): Promise<void> {
  const packageRoot = process.cwd();
  const manifestPath = resolve(
    packageRoot,
    'evaluation/manifest.json',
  );
  const manifest = evaluationManifestSchema.parse(
    await readJson(manifestPath),
  );
  const report = await runEvaluation(packageRoot, manifest);
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);

  if (!report.passed) {
    process.stderr.write(
      'evaluation metrics did not satisfy committed minimums\n',
    );
    process.exitCode = 1;
    return;
  }
  if (process.argv.includes('--no-baseline')) {
    return;
  }

  const baseline = evaluationReportSchema.parse(
    await readJson(resolve(packageRoot, manifest.baseline_file)),
  );
  if (JSON.stringify(report) !== JSON.stringify(baseline)) {
    process.stderr.write(
      'evaluation report differs from the committed baseline\n',
    );
    process.exitCode = 1;
  }
}

main().catch(() => {
  process.stderr.write('evaluation could not be completed\n');
  process.exitCode = 1;
});
