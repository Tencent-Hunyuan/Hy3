import { readFile, readdir } from 'node:fs/promises';
import { extname, join, relative } from 'node:path';

const root = new URL('..', import.meta.url);
const includedExtensions = new Set(['.json', '.js', '.md', '.mjs', '.ts']);
const ignoredDirectories = new Set(['coverage', 'dist', 'node_modules']);
const problems = [];

async function visit(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) {
      continue;
    }
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      await visit(path);
      continue;
    }
    if (!entry.isFile() || !includedExtensions.has(extname(entry.name))) {
      continue;
    }
    const content = await readFile(path, 'utf8');
    const displayPath = relative(root.pathname, path);
    for (const [index, line] of content.split('\n').entries()) {
      if (/[ \t]+$/.test(line)) {
        problems.push(`${displayPath}:${index + 1}: trailing whitespace`);
      }
      if (extname(entry.name) === '.ts' && /\bconsole\.log\s*\(/.test(line)) {
        problems.push(`${displayPath}:${index + 1}: console.log can corrupt stdio`);
      }
    }
    if (content.includes('\r')) {
      problems.push(`${displayPath}: CRLF is not allowed`);
    }
    if (/sk-[A-Za-z0-9]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY/.test(content)) {
      problems.push(`${displayPath}: credential-like value detected`);
    }
  }
}

await visit(root.pathname);
if (problems.length > 0) {
  console.error(problems.join('\n'));
  process.exitCode = 1;
} else {
  console.error('lint: clean');
}
