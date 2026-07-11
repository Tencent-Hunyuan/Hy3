import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function jsonVersion(path: string): string {
  return JSON.parse(readFileSync(resolve(root, path), "utf-8")).version;
}

describe("version sync", () => {
  it("server.ts version matches package.json", () => {
    const pkg = jsonVersion("package.json");
    const server = readFileSync(resolve(root, "src/server.ts"), "utf-8");
    const match = server.match(/version:\s*"([^"]+)"/);
    expect(match?.[1]).toBe(pkg);
  });

  it("package-lock.json top-level version matches package.json", () => {
    expect(jsonVersion("package-lock.json")).toBe(jsonVersion("package.json"));
  });
});
