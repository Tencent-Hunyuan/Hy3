import fs from 'fs-extra';
import * as path from 'path';
import type { Config } from '../../src/types';

const WORKSPACE_DIR = process.env.WORKSPACE_DIR
  ? path.resolve(process.env.WORKSPACE_DIR)
  : path.join(process.cwd(), 'data');
const CONFIG_PATH = path.join(WORKSPACE_DIR, 'config.json');

const DEFAULT_CONFIG: Config = {
  onboardingComplete: false,
  userName: '',
  subjects: [],
  activeSubjectId: null,
  languagePreference: '',
  detectedLanguage: 'en',
};

export async function ensureWorkspace(): Promise<void> {
  await fs.ensureDir(WORKSPACE_DIR);
  await fs.ensureDir(path.join(WORKSPACE_DIR, 'materials'));
  await fs.ensureDir(path.join(WORKSPACE_DIR, 'chapters'));
  await fs.ensureDir(path.join(WORKSPACE_DIR, 'tests'));
}

export async function loadConfig(): Promise<Config> {
  await ensureWorkspace();
  if (await fs.pathExists(CONFIG_PATH)) {
    return await fs.readJson(CONFIG_PATH);
  }
  return DEFAULT_CONFIG;
}

export async function saveConfig(config: Partial<Config>): Promise<Config> {
  await ensureWorkspace();
  const existing = await loadConfig();
  const merged = { ...existing, ...config };
  await fs.writeJson(CONFIG_PATH, merged, { spaces: 2 });
  return merged;
}

export function getWorkspaceDir(): string {
  return WORKSPACE_DIR;
}

export function getMaterialsDir(): string {
  return path.join(WORKSPACE_DIR, 'materials');
}

/** True when this instance is running as a shared public deployment (login gate + key redaction active). */
export function isHostedMode(): boolean {
  return !!process.env.SESSION_SECRET;
}
