import crypto from 'crypto';
import type { Request, Response, NextFunction } from 'express';
import fs from 'fs-extra';
import * as path from 'path';
import { getWorkspaceDir, isHostedMode } from './configService';

export const SESSION_COOKIE_NAME = 'isgrace_session';

export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function sign(payload: string, secret: string): string {
  return crypto.createHmac('sha256', secret).update(payload).digest('hex');
}

export function createSessionCookieValue(email: string): string {
  const secret = process.env.SESSION_SECRET!;
  const encoded = Buffer.from(email, 'utf8').toString('base64url');
  return `${encoded}.${sign(encoded, secret)}`;
}

/** Hand-parses the raw Cookie header — no cookie-parser dependency needed for one named cookie. */
function readCookie(req: Request, name: string): string | undefined {
  const header = req.headers.cookie;
  if (!header) return undefined;
  for (const part of header.split(';')) {
    const eq = part.indexOf('=');
    if (eq === -1) continue;
    const key = part.slice(0, eq).trim();
    if (key === name) return decodeURIComponent(part.slice(eq + 1).trim());
  }
  return undefined;
}

export function verifySessionFromRequest(req: Request): string | null {
  const secret = process.env.SESSION_SECRET;
  if (!secret) return null;
  const token = readCookie(req, SESSION_COOKIE_NAME);
  if (!token) return null;
  const [encoded, sig] = token.split('.');
  if (!encoded || !sig) return null;

  const expected = sign(encoded, secret);
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;

  try {
    return Buffer.from(encoded, 'base64url').toString('utf8');
  } catch {
    return null;
  }
}

/** No-op when not hosted (local solo dev is never gated); 401s an unauthenticated request otherwise. */
export function requireAuth(req: Request, res: Response, next: NextFunction): void {
  if (!isHostedMode()) { next(); return; }
  if (!verifySessionFromRequest(req)) {
    res.status(401).json({ error: 'AUTH_REQUIRED' });
    return;
  }
  next();
}

export async function logVisitor(email: string, ip?: string): Promise<void> {
  const filePath = path.join(getWorkspaceDir(), 'visitors.jsonl');
  await fs.ensureDir(path.dirname(filePath));
  const line = JSON.stringify({ email, ip, at: new Date().toISOString() }) + '\n';
  await fs.appendFile(filePath, line, 'utf-8');
}
