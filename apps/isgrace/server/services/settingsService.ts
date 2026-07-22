import fs from 'fs-extra';
import * as path from 'path';
import type { LLMSettings, LLMProvider } from '../../src/types';
import { DEFAULT_LLM_SETTINGS } from '../../src/types';
import { getWorkspaceDir, isHostedMode } from './configService';

function getSettingsPath(): string {
  return path.join(getWorkspaceDir(), 'settings.json');
}

/** Hosted mode's shared default, sourced entirely from env vars — never the file on disk. */
function hostedDefaultSettings(): LLMSettings {
  return {
    apiKey: process.env.DEFAULT_LLM_API_KEY ?? '',
    provider: (process.env.DEFAULT_LLM_PROVIDER as LLMProvider | undefined) ?? DEFAULT_LLM_SETTINGS.provider,
    model: process.env.DEFAULT_LLM_MODEL ?? DEFAULT_LLM_SETTINGS.model,
    temperature: process.env.DEFAULT_LLM_TEMPERATURE ? parseFloat(process.env.DEFAULT_LLM_TEMPERATURE) : DEFAULT_LLM_SETTINGS.temperature,
  };
}

export async function loadLLMSettings(): Promise<LLMSettings> {
  if (isHostedMode()) return hostedDefaultSettings();

  try {
    const settingsPath = getSettingsPath();
    if (await fs.pathExists(settingsPath)) {
      const raw = await fs.readJson(settingsPath);
      return { ...DEFAULT_LLM_SETTINGS, ...raw };
    }
  } catch (e) {
    console.error('[settingsService] load failed:', e);
  }
  return { ...DEFAULT_LLM_SETTINGS };
}

export async function saveLLMSettings(settings: Partial<LLMSettings>): Promise<LLMSettings> {
  if (isHostedMode()) throw new Error('HOSTED_MODE_READ_ONLY');
  const existing = await loadLLMSettings();
  const merged = { ...existing, ...settings };
  const settingsPath = getSettingsPath();
  await fs.ensureDir(path.dirname(settingsPath));
  await fs.writeJson(settingsPath, merged, { spaces: 2 });
  return merged;
}
