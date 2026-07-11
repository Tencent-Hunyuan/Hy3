import { readFileSync, writeFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");

const newVersion = process.argv[2];
if (!newVersion || !/^\d+\.\d+\.\d+/.test(newVersion)) {
  console.error("Usage: node scripts/bump-version.mjs <x.x.x>");
  process.exit(1);
}

function updateJson(path, version) {
  const file = resolve(root, path);
  const content = JSON.parse(readFileSync(file, "utf-8"));
  content.version = version;
  writeFileSync(file, JSON.stringify(content, null, 2) + "\n");
  console.log(`Updated ${path} → ${version}`);
}

function updateServerTs(version) {
  const file = resolve(root, "src/server.ts");
  let content = readFileSync(file, "utf-8");
  content = content.replace(/version:\s*"[^"]+"/, `version: "${version}"`);
  writeFileSync(file, content);
  console.log(`Updated src/server.ts → ${version}`);
}

function updateReadme(path, version) {
  const file = resolve(root, path);
  let content = readFileSync(file, "utf-8");
  content = content.replace(/hy3-data-mcp-\d+\.\d+\.\d+\.tgz/g, `hy3-data-mcp-${version}.tgz`);
  writeFileSync(file, content);
  console.log(`Updated ${path} install examples → ${version}`);
}

updateJson("package.json", newVersion);
updateJson("package-lock.json", newVersion);
updateServerTs(newVersion);
updateReadme("README.md", newVersion);
updateReadme("README_CN.md", newVersion);

console.log(`\nVersion bumped to ${newVersion}. Run "npm install && npm run build && npm test && npm run pack:release" to finish.`);
