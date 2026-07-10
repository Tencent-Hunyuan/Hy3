import { createCanvas } from "@napi-rs/canvas";
import createWordCloudFactory from "node-rs-wordcloud";
import { getTheme } from "./themes.js";
import type { Theme } from "./themes.js";

export interface Word {
  word: string;
  weight: number;
}

// node-rs-wordcloud expects a createCanvas that tolerates missing dimensions
// during its feature-detection probe.
const WordCloud = createWordCloudFactory((width, height) =>
  createCanvas(width ?? 1, height ?? 1)
);

function buildColorizer(
  list: Array<[string, number]>,
  theme: Theme
): (word: string) => string {
  const colorMap = new Map(
    list.map(([word], index) => [word, theme.palette[index % theme.palette.length]])
  );
  return (word: string) => colorMap.get(word) ?? theme.palette[0];
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function renderWordcloudSvg(
  words: Word[],
  title: string,
  width = 800,
  height = 500,
  themeName?: string,
  fontFamily?: string,
  overrides?: Partial<Omit<Theme, "name">>
): string {
  const theme = getTheme(themeName, fontFamily, overrides);
  const titleSpace = 60;
  const cloudWidth = width;
  const cloudHeight = Math.max(120, height - titleSpace);

  const list = words.map((w): [string, number] => [w.word, w.weight]);
  const colorizer = buildColorizer(list, theme);

  const canvas = createCanvas(cloudWidth, cloudHeight);
  WordCloud(canvas, {
    list,
    fontFamily: theme.fontFamily,
    color: (word) => colorizer(word),
    backgroundColor: theme.backgroundColor,
    gridSize: 8,
    sizeRange: [16, Math.min(80, Math.floor(cloudHeight / 4))],
    rotateRatio: 0.3,
    shape: "circle",
    ellipticity: 0.85,
    drawOutOfBound: false,
    shrinkToFit: true,
    shuffle: true,
  }).draw();

  const pngBuffer = canvas.toBuffer("image/png");
  const base64 = Buffer.from(pngBuffer).toString("base64");

  return `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="${theme.backgroundColor}"/>
  <text x="${width / 2}" y="36" font-size="20" font-weight="bold" text-anchor="middle" fill="${theme.textColor}" font-family="${theme.fontFamily}">${escapeHtml(title)}</text>
  <image x="0" y="${titleSpace}" width="${cloudWidth}" height="${cloudHeight}" href="data:image/png;base64,${base64}"/>
</svg>`;
}

export function renderWordcloudHtml(
  words: Word[],
  title: string,
  width = 800,
  height = 500,
  themeName?: string,
  fontFamily?: string,
  overrides?: Partial<Omit<Theme, "name">>
): string {
  const theme = getTheme(themeName, fontFamily, overrides);
  const svg = renderWordcloudSvg(words, title, width, height, themeName, fontFamily, overrides);
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)}</title>
  <style>
    body { margin: 0; padding: 24px; background: ${theme.backgroundColor}; color: ${theme.textColor}; font-family: ${theme.fontFamily}; text-align: center; }
    .container { display: inline-block; }
  </style>
</head>
<body>
  <div class="container">${svg}</div>
</body>
</html>`;
}
