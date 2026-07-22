#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const repositoryRoot = path.resolve(root, '..', '..');
const guides = [
  'aider.md',
  'cline.md',
  'codex-cli.md',
  'continue.md',
  'dify.md',
  'roo-code.md',
  'kilo-code.md',
  'opencode.md',
  'codebuddy-code.md'
];
const requiredPatterns = new Map([
  ['tested snapshot', /tested .*snapshot/i],
  ['base URL or endpoint', /base url|endpoint/i],
  ['model', /\bmodel\b/i],
  ['authentication', /api key|authentication|secret/i],
  ['protocol', /protocol|chat completions|responses api/i],
  ['first chat', /^## first chat\s*$/im],
  ['real task', /^## real task demo\s*$/im],
  ['screenshots', /^## screenshots \/ gifs?\s*$/im],
  ['troubleshooting', /^## troubleshooting\s*$/im]
]);
const errors = [];
let checkedLinks = 0;

for (const guideName of guides) {
  const guidePath = path.join(root, guideName);
  if (!fs.existsSync(guidePath)) {
    errors.push(`missing guide: ${guideName}`);
    continue;
  }
  const text = fs.readFileSync(guidePath, 'utf8');
  for (const [label, pattern] of requiredPatterns) {
    if (!pattern.test(text)) errors.push(`${guideName}: missing required field/section: ${label}`);
  }
}

const markdownFiles = fs.readdirSync(root)
  .filter((name) => name.endsWith('.md'))
  .sort();

for (const documentName of markdownFiles) {
  const documentPath = path.join(root, documentName);
  const text = fs.readFileSync(documentPath, 'utf8');
  for (const match of text.matchAll(/!?\[[^\]]*\]\(([^)]+)\)/g)) {
    const rawTarget = match[1].trim().split(/\s+/, 1)[0].replace(/^<|>$/g, '');
    if (!rawTarget || /^(?:https?:\/\/|mailto:|#)/.test(rawTarget)) continue;
    checkedLinks += 1;
    const relative = decodeURIComponent(rawTarget.split('#', 1)[0]);
    const resolved = path.resolve(path.dirname(documentPath), relative);
    if (path.relative(repositoryRoot, resolved).startsWith('..')) {
      errors.push(`${documentName}: local link escapes repository scope: ${rawTarget}`);
    } else if (!fs.existsSync(resolved)) {
      errors.push(`${documentName}: missing local link target: ${rawTarget}`);
    }
  }

  for (const match of text.matchAll(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g)) {
    if (/versioned/i.test(match[1]) && /\/(?:blob|raw)\/main\//.test(match[2])) {
      errors.push(`${documentName}: mutable main link is mislabeled versioned: ${match[2]}`);
    }
  }
}

const index = fs.readFileSync(path.join(root, 'README.md'), 'utf8');
for (const required of [
  '## Part A: integration verification matrix',
  '## Part B: Codex + Hy3 evidence-grounded spec diff reviewer',
  'npm run demo:offline',
  'npm run review:staged',
  'npm run check',
  'OFFLINE / FAKE'
]) {
  if (!index.includes(required)) errors.push(`README.md: missing Part A/B index marker: ${required}`);
}

if (errors.length > 0) {
  process.stderr.write(`Integration documentation checks failed (${errors.length}):\n`);
  for (const error of errors) process.stderr.write(`- ${error}\n`);
  process.exitCode = 1;
} else {
  process.stdout.write(
    `Integration documentation checks passed: ${guides.length} guides, ${markdownFiles.length} Markdown files, ${checkedLinks} local targets.\n`
  );
}
