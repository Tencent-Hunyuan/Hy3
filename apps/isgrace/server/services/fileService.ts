import fs from 'fs-extra';
import * as path from 'path';
import * as crypto from 'crypto';
import { getMaterialsDir } from './configService';
import { parsePDF, parseDOCX, parseTXT } from './fileParser';
import { fetchUrl } from './urlFetcher';
import type { Material, MaterialType } from '../../src/types';

function detectMaterialType(filename: string): MaterialType {
  const lower = filename.toLowerCase();
  if (lower.includes('syllabus') || lower.includes('outline') || lower.includes('schedule')) return 'syllabus';
  if (lower.includes('exam') || lower.includes('quiz') || lower.includes('test') || lower.includes('midterm') || lower.includes('final')) return 'exam';
  if (lower.includes('guide') || lower.includes('tutorial') || lower.includes('cheatsheet') || lower.includes('cheat')) return 'guide';
  if (lower.includes('textbook') || lower.includes('chapter') || lower.includes('lecture') || lower.includes('slides')) return 'textbook';
  return 'textbook'; // default assumption
}

function getTier(type: MaterialType): 1 | 2 | 3 {
  if (type === 'guide') return 1;
  if (type === 'textbook') return 2;
  return 3;
}

export async function uploadMaterial(sourcePath: string, originalName: string): Promise<Material> {
  const materialsDir = getMaterialsDir();
  await fs.ensureDir(materialsDir);

  const type = detectMaterialType(originalName);
  const ext = path.extname(originalName);
  const id = `mat_${crypto.randomBytes(4).toString('hex')}`;
  const destName = `${type}_${id}${ext}`;
  const destPath = path.join(materialsDir, destName);

  await fs.copy(sourcePath, destPath);
  const stats = await fs.stat(destPath);

  // Save metadata
  const metaPath = path.join(materialsDir, 'metadata.json');
  let metadata: Material[] = [];
  if (await fs.pathExists(metaPath)) {
    metadata = await fs.readJson(metaPath);
  }

  // Load content immediately so the AI can read it
  const content = await readMaterialContent(destPath);

  const material: Material = {
    id,
    name: originalName,
    type,
    path: destPath,
    uploadedAt: new Date().toISOString(),
    size: stats.size,
    tier: getTier(type),
    content,
  };

  // Save metadata without content (keeps metadata.json small)
  metadata.push({ ...material, content: undefined });
  await fs.writeJson(metaPath, metadata, { spaces: 2 });

  return material;
}

export async function readMaterialContent(filePath: string): Promise<string> {
  const ext = path.extname(filePath).toLowerCase();
  const name = path.basename(filePath);
  try {
    if (ext === '.pdf') return await parsePDF(filePath);
    if (ext === '.docx') return await parseDOCX(filePath);
    if (ext === '.txt' || ext === '.md') return await parseTXT(filePath);
    const extLabel = ext.slice(1).toUpperCase();
    return `[${extLabel} file: "${name}" — text extraction is not supported for this format. Ask the student to paste the relevant content directly into the chat.]`;
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return `[Could not extract text from "${name}": ${msg}]`;
  }
}

export async function uploadFromUrl(url: string): Promise<Material> {
  const materialsDir = getMaterialsDir();
  await fs.ensureDir(materialsDir);

  const { title, content } = await fetchUrl(url);

  const id = `mat_${crypto.randomBytes(4).toString('hex')}`;
  const safeName = title.replace(/[^a-zA-Z0-9\s\-_]/g, '').slice(0, 60).trim() || 'web-page';
  const destName = `url_${id}.md`;
  const destPath = path.join(materialsDir, destName);

  await fs.writeFile(destPath, content, 'utf-8');
  const stats = await fs.stat(destPath);

  const metaPath = path.join(materialsDir, 'metadata.json');
  let metadata: Material[] = [];
  if (await fs.pathExists(metaPath)) {
    metadata = await fs.readJson(metaPath);
  }

  const material: Material = {
    id,
    name: safeName,
    type: 'textbook',
    path: destPath,
    uploadedAt: new Date().toISOString(),
    size: stats.size,
    tier: 2,
    content,
    sourceUrl: url,
  };

  metadata.push({ ...material, content: undefined });
  await fs.writeJson(metaPath, metadata, { spaces: 2 });

  return material;
}

export async function deleteMaterial(materialId: string): Promise<void> {
  const materialsDir = getMaterialsDir();
  const metaPath = path.join(materialsDir, 'metadata.json');
  if (!await fs.pathExists(metaPath)) return;

  const metadata: Material[] = await fs.readJson(metaPath);
  const material = metadata.find((m) => m.id === materialId);
  if (material) {
    await fs.remove(material.path);
  }
  const updated = metadata.filter((m) => m.id !== materialId);
  await fs.writeJson(metaPath, updated, { spaces: 2 });
}
