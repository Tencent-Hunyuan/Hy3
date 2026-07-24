import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const width = 840;
const height = 480;
const scale = 2;
const left = 38;
const top = 34;
const lineHeight = 22;
const clearCode = 4;
const endCode = 5;
const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const outputPath = resolve(packageRoot, 'assets/client-demo.gif');
const palette = [
  [11, 16, 32],
  [139, 155, 180],
  [88, 214, 141],
  [97, 218, 251],
];

const font = {
  ' ': ['00000', '00000', '00000', '00000', '00000', '00000', '00000'],
  A: ['01110', '10001', '10001', '11111', '10001', '10001', '10001'],
  B: ['11110', '10001', '10001', '11110', '10001', '10001', '11110'],
  C: ['01111', '10000', '10000', '10000', '10000', '10000', '01111'],
  D: ['11110', '10001', '10001', '10001', '10001', '10001', '11110'],
  E: ['11111', '10000', '10000', '11110', '10000', '10000', '11111'],
  F: ['11111', '10000', '10000', '11110', '10000', '10000', '10000'],
  G: ['01111', '10000', '10000', '10111', '10001', '10001', '01111'],
  H: ['10001', '10001', '10001', '11111', '10001', '10001', '10001'],
  I: ['11111', '00100', '00100', '00100', '00100', '00100', '11111'],
  J: ['00111', '00010', '00010', '00010', '10010', '10010', '01100'],
  K: ['10001', '10010', '10100', '11000', '10100', '10010', '10001'],
  L: ['10000', '10000', '10000', '10000', '10000', '10000', '11111'],
  M: ['10001', '11011', '10101', '10101', '10001', '10001', '10001'],
  N: ['10001', '11001', '10101', '10011', '10001', '10001', '10001'],
  O: ['01110', '10001', '10001', '10001', '10001', '10001', '01110'],
  P: ['11110', '10001', '10001', '11110', '10000', '10000', '10000'],
  Q: ['01110', '10001', '10001', '10001', '10101', '10010', '01101'],
  R: ['11110', '10001', '10001', '11110', '10100', '10010', '10001'],
  S: ['01111', '10000', '10000', '01110', '00001', '00001', '11110'],
  T: ['11111', '00100', '00100', '00100', '00100', '00100', '00100'],
  U: ['10001', '10001', '10001', '10001', '10001', '10001', '01110'],
  V: ['10001', '10001', '10001', '10001', '10001', '01010', '00100'],
  W: ['10001', '10001', '10001', '10101', '10101', '10101', '01010'],
  X: ['10001', '10001', '01010', '00100', '01010', '10001', '10001'],
  Y: ['10001', '10001', '01010', '00100', '00100', '00100', '00100'],
  Z: ['11111', '00001', '00010', '00100', '01000', '10000', '11111'],
  0: ['01110', '10001', '10011', '10101', '11001', '10001', '01110'],
  1: ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
  2: ['01110', '10001', '00001', '00010', '00100', '01000', '11111'],
  3: ['11110', '00001', '00001', '01110', '00001', '00001', '11110'],
  4: ['00010', '00110', '01010', '10010', '11111', '00010', '00010'],
  5: ['11111', '10000', '10000', '11110', '00001', '00001', '11110'],
  6: ['01110', '10000', '10000', '11110', '10001', '10001', '01110'],
  7: ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
  8: ['01110', '10001', '10001', '01110', '10001', '10001', '01110'],
  9: ['01110', '10001', '10001', '01111', '00001', '00001', '01110'],
  '-': ['00000', '00000', '00000', '11111', '00000', '00000', '00000'],
  '_': ['00000', '00000', '00000', '00000', '00000', '00000', '11111'],
  '.': ['00000', '00000', '00000', '00000', '00000', '00110', '00110'],
  ':': ['00000', '00110', '00110', '00000', '00110', '00110', '00000'],
  '/': ['00001', '00010', '00010', '00100', '01000', '01000', '10000'],
  '(': ['00010', '00100', '01000', '01000', '01000', '00100', '00010'],
  ')': ['01000', '00100', '00010', '00010', '00010', '00100', '01000'],
  '=': ['00000', '11111', '00000', '11111', '00000', '00000', '00000'],
  '+': ['00000', '00100', '00100', '11111', '00100', '00100', '00000'],
  '$': ['00100', '01111', '10100', '01110', '00101', '11110', '00100'],
  '>': ['10000', '01000', '00100', '00010', '00100', '01000', '10000'],
};

const frames = [
  {
    delay: 130,
    lines: [
      ['HY3 MCP QUALITY GATE', 3],
      ['STAGE 8 CLIENT VERIFICATION', 2],
      ['', 1],
      ['REAL CLIENT OUTPUT, SANITIZED', 1],
      ['SYNTHETIC FIXTURES ONLY', 1],
      ['', 1],
      ['CURSOR + CODEBUDDY + CLEAN TARBALL', 3],
      ['NO CREDENTIALS. NO PERSONAL PATHS.', 2],
    ],
  },
  {
    delay: 160,
    lines: [
      ['$ AGENT MCP LIST', 3],
      ['', 1],
      ['HY3-MCP-QUALITY-GATE: READY', 2],
      ['', 1],
      ['$ AGENT MCP LIST-TOOLS HY3-MCP-QUALITY-GATE', 3],
      ['', 1],
      ['TOOLS FOR HY3-MCP-QUALITY-GATE (4):', 1],
      ['- MCPQ_AUDIT_CONTRACTS', 2],
      ['- MCPQ_COMPARE_CONTRACTS', 2],
      ['- MCPQ_GENERATE_PROBE_SUITE', 2],
      ['- MCPQ_INSPECT_SERVER', 2],
    ],
  },
  {
    delay: 170,
    lines: [
      ['CURSOR ARGUMENT SURFACE', 3],
      ['', 1],
      ['MCPQ_COMPARE_CONTRACTS (', 2],
      ['  BASELINE_TARGET_ID,', 1],
      ['  CURRENT_TARGET_ID,', 1],
      ['  INCLUDE_NON_BREAKING,', 1],
      ['  REASONING_EFFORT,', 1],
      ['  INCLUDE_HY3', 1],
      [')', 2],
      ['', 1],
      ['CLIENT-DISCOVERED SCHEMA: PASS', 3],
    ],
  },
  {
    delay: 170,
    lines: [
      ['$ CODEBUDDY MCP GET HY3-MCP-QUALITY-GATE', 3],
      ['', 1],
      ['SCOPE: PROJECT', 1],
      ['STATUS: CONNECTED', 2],
      ['TYPE: STDIO', 1],
      ['COMMAND: NODE', 1],
      ['', 1],
      ['PROJECT CONFIG: .MCP.JSON', 3],
      ['HEALTH CHECK: PASS', 2],
    ],
  },
  {
    delay: 190,
    lines: [
      ['REAL READ-ONLY FIXTURE CALLS', 3],
      ['', 1],
      ['CURSOR: PASS', 2],
      ['CODEBUDDY: PASS', 2],
      ['', 1],
      ['  TOOL: MCPQ_INSPECT_SERVER', 1],
      ['  TARGET_ID: FIXTURE-GOOD', 1],
      ['  STATUS: PASS', 2],
      ['  TOOLS: FIXTURE_ECHO, FIXTURE_SUM', 2],
      ['', 1],
      ['EXPLICIT APPROVAL. ONE CALL PER CLIENT.', 3],
    ],
  },
  {
    delay: 260,
    lines: [
      ['DELIVERY EVIDENCE', 3],
      ['', 1],
      ['CURSOR READY + 4 TOOLS', 2],
      ['CODEBUDDY PROJECT + CONNECTED', 2],
      ['BOTH CLIENT FIXTURE CALLS PASS', 2],
      ['CLEAN INSTALL + FIXTURE CALL PASS', 2],
      ['85 / 85 TESTS PASS', 2],
      ['10 / 10 EVALUATION CASES PASS', 2],
      ['', 1],
      ['HY3 MCP QUALITY GATE', 3],
    ],
  },
];

function drawCharacter(pixels, character, x, y, color) {
  const glyph = font[character.toUpperCase()] ?? font[' '];
  for (const [rowIndex, row] of glyph.entries()) {
    for (const [columnIndex, value] of [...row].entries()) {
      if (value !== '1') {
        continue;
      }
      for (let dy = 0; dy < scale; dy += 1) {
        for (let dx = 0; dx < scale; dx += 1) {
          const targetX = x + columnIndex * scale + dx;
          const targetY = y + rowIndex * scale + dy;
          if (targetX < width && targetY < height) {
            pixels[targetY * width + targetX] = color;
          }
        }
      }
    }
  }
}

function drawText(pixels, text, x, y, color) {
  let cursor = x;
  for (const character of text) {
    drawCharacter(pixels, character, cursor, y, color);
    cursor += 6 * scale;
  }
}

function framePixels(frame) {
  const pixels = Buffer.alloc(width * height);
  frame.lines.forEach(([line, color], index) => {
    drawText(pixels, line, left, top + index * lineHeight, color);
  });
  return pixels;
}

function lzwBlocks(pixels) {
  const bytes = [];
  let accumulator = 0;
  let bitCount = 0;
  const emit = (code) => {
    accumulator |= code << bitCount;
    bitCount += 3;
    while (bitCount >= 8) {
      bytes.push(accumulator & 0xff);
      accumulator >>= 8;
      bitCount -= 8;
    }
  };

  for (const pixel of pixels) {
    emit(clearCode);
    emit(pixel);
  }
  emit(endCode);
  if (bitCount > 0) {
    bytes.push(accumulator & 0xff);
  }

  const blocks = [2];
  for (let offset = 0; offset < bytes.length; offset += 255) {
    const block = bytes.slice(offset, offset + 255);
    blocks.push(block.length, ...block);
  }
  blocks.push(0);
  return blocks;
}

function word(value) {
  return [value & 0xff, (value >> 8) & 0xff];
}

function ascii(value) {
  return [...Buffer.from(value, 'ascii')];
}

const comment = ascii('SANITIZED STAGE 8 CLIENT VERIFICATION');
const gif = [
  ...ascii('GIF89a'),
  ...word(width),
  ...word(height),
  0xf1,
  0,
  0,
  ...palette.flat(),
  0x21,
  0xff,
  0x0b,
  ...ascii('NETSCAPE2.0'),
  0x03,
  0x01,
  0x00,
  0x00,
  0x00,
  0x21,
  0xfe,
  comment.length,
  ...comment,
  0x00,
];

for (const frame of frames) {
  const imageData = lzwBlocks(framePixels(frame));
  gif.push(
    0x21,
    0xf9,
    0x04,
    0x04,
    ...word(frame.delay),
    0x00,
    0x00,
    0x2c,
    0x00,
    0x00,
    0x00,
    0x00,
    ...word(width),
    ...word(height),
    0x00,
  );
  for (let offset = 0; offset < imageData.length; offset += 8192) {
    gif.push(...imageData.slice(offset, offset + 8192));
  }
}
gif.push(0x3b);

await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, Buffer.from(gif));
process.stdout.write(`wrote assets/client-demo.gif (${gif.length} bytes)\n`);
