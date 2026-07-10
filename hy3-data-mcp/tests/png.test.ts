import { describe, it, expect } from "vitest";
import { svgToPng } from "../src/viz/png.js";

describe("svgToPng", () => {
  it("converts an SVG string to a PNG buffer", async () => {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="#ff0000"/></svg>`;
    const png = await svgToPng(svg, 100, 100);
    expect(png).toBeInstanceOf(Buffer);
    expect(png.length).toBeGreaterThan(0);
    // PNG magic bytes
    expect(png[0]).toBe(0x89);
    expect(png.toString("ascii", 1, 4)).toBe("PNG");
  });
});
