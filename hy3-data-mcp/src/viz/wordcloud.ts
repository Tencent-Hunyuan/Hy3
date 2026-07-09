import { getTheme } from "./themes.js";
import type { Theme } from "./themes.js";

export interface Word {
  word: string;
  weight: number;
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
  const sorted = [...words].sort((a, b) => b.weight - a.weight).slice(0, 80);
  const maxWeight = Math.max(...sorted.map((w) => w.weight), 1);
  const placed: Array<{
    word: string;
    x: number;
    y: number;
    size: number;
    color: string;
    rotate: number;
    bbox: { x: number; y: number; w: number; h: number };
  }> = [];

  const theme = getTheme(themeName, fontFamily, overrides);
  const palette = theme.palette;

  function checkCollision(
    x: number,
    y: number,
    size: number,
    word: string,
    rotate: number
  ): boolean {
    const w = word.length * size * 0.6;
    const h = size * 1.2;
    const rad = (rotate * Math.PI) / 180;
    const cos = Math.abs(Math.cos(rad));
    const sin = Math.abs(Math.sin(rad));
    const bboxW = w * cos + h * sin;
    const bboxH = w * sin + h * cos;
    const bbox = {
      x: x - bboxW / 2,
      y: y - bboxH / 2,
      w: bboxW,
      h: bboxH,
    };

    for (const p of placed) {
      if (
        bbox.x < p.bbox.x + p.bbox.w &&
        bbox.x + bbox.w > p.bbox.x &&
        bbox.y < p.bbox.y + p.bbox.h &&
        bbox.y + bbox.h > p.bbox.y
      ) {
        return true;
      }
    }
    return false;
  }

  function tryPlace(word: string, weight: number, index: number) {
    const size = 14 + (weight / maxWeight) * 56;
    const color = palette[index % palette.length];
    const rotate = Math.random() > 0.7 ? (Math.random() - 0.5) * 60 : 0;

    const centerX = width / 2;
    const centerY = height / 2;

    // Try center first
    if (!checkCollision(centerX, centerY, size, word, rotate)) {
      const w = word.length * size * 0.6;
      const h = size * 1.2;
      const rad = (rotate * Math.PI) / 180;
      const cos = Math.abs(Math.cos(rad));
      const sin = Math.abs(Math.sin(rad));
      placed.push({
        word,
        x: centerX,
        y: centerY,
        size,
        color,
        rotate,
        bbox: {
          x: centerX - (w * cos + h * sin) / 2,
          y: centerY - (w * sin + h * cos) / 2,
          w: w * cos + h * sin,
          h: w * sin + h * cos,
        },
      });
      return;
    }

    // Spiral search
    let angle = 0;
    let radius = 10;
    const step = 5;
    const maxRadius = Math.min(width, height) / 2 - 50;

    while (radius < maxRadius) {
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      if (x > 50 && x < width - 50 && y > 50 && y < height - 50) {
        if (!checkCollision(x, y, size, word, rotate)) {
          const w = word.length * size * 0.6;
          const h = size * 1.2;
          const rad = (rotate * Math.PI) / 180;
          const cos = Math.abs(Math.cos(rad));
          const sin = Math.abs(Math.sin(rad));
          placed.push({
            word,
            x,
            y,
            size,
            color,
            rotate,
            bbox: {
              x: x - (w * cos + h * sin) / 2,
              y: y - (w * sin + h * cos) / 2,
              w: w * cos + h * sin,
              h: w * sin + h * cos,
            },
          });
          return;
        }
      }
      angle += 0.5;
      radius += step * 0.02;
    }
  }

  sorted.forEach((w, i) => tryPlace(w.word, w.weight, i));

  const textElements = placed
    .map(
      (p) =>
        `<text x="${p.x.toFixed(1)}" y="${p.y.toFixed(1)}" font-size="${p.size.toFixed(
          1
        )}" fill="${p.color}" font-family="${theme.fontFamily}" text-anchor="middle" dominant-baseline="middle" transform="rotate(${p.rotate.toFixed(
          1
        )} ${p.x.toFixed(1)} ${p.y.toFixed(1)})">${escapeHtml(p.word)}</text>`
    )
    .join("\n");

  return `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="${theme.backgroundColor}"/>
  <text x="${width / 2}" y="36" font-size="20" font-weight="bold" text-anchor="middle" fill="${theme.textColor}" font-family="${theme.fontFamily}">${escapeHtml(
    title
  )}</text>
  ${textElements}
</svg>`;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
