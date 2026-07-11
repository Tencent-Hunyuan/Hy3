import { execSync } from "child_process";
import { readFileSync, renameSync, existsSync, mkdirSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");

const pkg = JSON.parse(readFileSync(resolve(root, "package.json"), "utf-8"));
const tarball = `${pkg.name}-${pkg.version}.tgz`;
const targetDir = resolve(root, "releases");
const target = resolve(targetDir, tarball);

console.log(`Packing ${pkg.name}@${pkg.version}...`);
execSync("npm pack", { cwd: root, stdio: "inherit" });

if (!existsSync(targetDir)) {
  mkdirSync(targetDir, { recursive: true });
}

renameSync(resolve(root, tarball), target);
console.log(`Released: releases/${tarball}`);
