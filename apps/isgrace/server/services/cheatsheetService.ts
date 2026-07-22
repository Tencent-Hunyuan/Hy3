import fs from 'fs-extra';
import * as path from 'path';
import { getWorkspaceDir } from './configService';

export async function saveCheatsheet(content: string): Promise<string> {
  const chaptersDir = path.join(getWorkspaceDir(), 'chapters');
  await fs.ensureDir(chaptersDir);
  const filePath = path.join(chaptersDir, `cheatsheet_${Date.now()}.md`);
  await fs.writeFile(filePath, content, 'utf-8');
  return filePath;
}
