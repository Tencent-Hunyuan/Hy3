import { Router } from 'express';
import multer from 'multer';
import * as os from 'os';
import * as crypto from 'crypto';
import fs from 'fs-extra';
import { loadConfig, saveConfig, isHostedMode } from './services/configService';
import { uploadMaterial, deleteMaterial, uploadFromUrl } from './services/fileService';
import { loadLLMSettings, saveLLMSettings } from './services/settingsService';
import { streamChat, testConnection, completeChat } from './services/llmService';
import { saveCheatsheet } from './services/cheatsheetService';
import { isValidEmail, createSessionCookieValue, verifySessionFromRequest, requireAuth, logVisitor, SESSION_COOKIE_NAME } from './services/authService';
import type { LLMMessage, LLMSettings } from '../src/types';

const upload = multer({ dest: os.tmpdir() });

export const router = Router();

// ── Auth ──────────────────────────────────────────────────────────────────────
// Registered before requireAuth is applied — these two routes are always reachable.

router.post('/auth/login', async (req, res) => {
  const email = String(req.body?.email ?? '').trim().toLowerCase();
  if (!isValidEmail(email)) {
    res.status(400).json({ error: 'INVALID_EMAIL' });
    return;
  }
  await logVisitor(email, req.ip);
  if (isHostedMode()) {
    res.cookie(SESSION_COOKIE_NAME, createSessionCookieValue(email), {
      httpOnly: true,
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
      maxAge: 90 * 24 * 60 * 60 * 1000,
    });
  }
  res.json({ email });
});

router.get('/auth/me', (req, res) => {
  res.json({ authRequired: isHostedMode(), email: verifySessionFromRequest(req) });
});

// Everything registered below this line is protected in hosted mode; a no-op otherwise.
router.use(requireAuth);

// ── Config ────────────────────────────────────────────────────────────────────

router.get('/config', async (_req, res) => {
  res.json(await loadConfig());
});

router.post('/config', async (req, res) => {
  res.json(await saveConfig(req.body));
});

// ── Files ─────────────────────────────────────────────────────────────────────

router.post('/materials', upload.single('file'), async (req, res) => {
  if (!req.file) { res.status(400).json({ error: 'No file uploaded' }); return; }
  try {
    const material = await uploadMaterial(req.file.path, req.file.originalname);
    res.json(material);
  } catch (err) {
    res.status(500).json({ error: err instanceof Error ? err.message : String(err) });
  } finally {
    await fs.remove(req.file.path).catch(() => {});
  }
});

router.post('/materials/from-url', async (req, res) => {
  try {
    const material = await uploadFromUrl(req.body.url);
    res.json(material);
  } catch (err) {
    res.status(500).json({ error: err instanceof Error ? err.message : String(err) });
  }
});

router.delete('/materials/:id', async (req, res) => {
  await deleteMaterial(req.params.id);
  res.json({ ok: true });
});

// ── LLM Settings ──────────────────────────────────────────────────────────────

router.get('/settings', async (_req, res) => {
  const settings = await loadLLMSettings();
  const hosted = isHostedMode();
  res.json({
    ...settings,
    apiKey: hosted ? '' : settings.apiKey,
    mode: hosted ? 'hosted' : 'local',
    hasDefaultKey: hosted ? !!process.env.DEFAULT_LLM_API_KEY : true,
  });
});

router.post('/settings', async (req, res) => {
  if (isHostedMode()) {
    res.status(403).json({ error: 'HOSTED_MODE_READ_ONLY' });
    return;
  }
  try {
    res.json(await saveLLMSettings(req.body));
  } catch (err) {
    console.error('[settings:save] failed:', err);
    res.status(500).json({ error: err instanceof Error ? err.message : String(err) });
  }
});

router.post('/settings/test-connection', async (req, res) => {
  res.json(await testConnection(req.body));
});

// ── LLM Chat (streaming via SSE) ───────────────────────────────────────────────

router.post('/llm/chat', async (req, res) => {
  const base = await loadLLMSettings();
  const override = req.body.settingsOverride as Partial<LLMSettings> | undefined;
  const settings = override?.apiKey ? { ...base, ...override } : base;
  const streamId = crypto.randomUUID();

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  const messages: LLMMessage[] = req.body.messages ?? [];
  const reasoningEffort = req.body.reasoningEffort as 'high' | 'low' | 'none' | undefined;

  try {
    await streamChat(messages, settings, streamId, (chunk) => {
      res.write(`data: ${JSON.stringify(chunk)}\n\n`);
    }, reasoningEffort);
  } catch (err) {
    res.write(`data: ${JSON.stringify({ id: streamId, delta: '', done: true, error: String(err) })}\n\n`);
  }
  res.end();
});

// ── LLM grading (non-streaming, used for essay/code test feedback) ───────────

interface GradePayload {
  questionId: string;
  type: 'essay' | 'code';
  question: string;
  rubric: string;
  answer: string;
  points: number;
  settingsOverride?: Partial<LLMSettings>;
}

router.post('/llm/grade', async (req, res) => {
  const payload = req.body as GradePayload;
  const base = await loadLLMSettings();
  const settings = payload.settingsOverride?.apiKey ? { ...base, ...payload.settingsOverride } : base;
  const systemPrompt = `You are a strict but fair academic grader. Grade the student's answer against the rubric provided. Return ONLY valid JSON with no extra text and no code fences.`;
  const userPrompt = `Question: ${payload.question}

Rubric and model answer:
${payload.rubric}

Student's answer:
${payload.answer || '(no answer provided)'}

Grade this answer strictly against the rubric. Return JSON in exactly this format:
{"correct":true,"score":3,"maxScore":${payload.points},"explanation":"..."}

Rules:
- "correct" = true if score >= 60% of maxScore
- "explanation" must be specific and useful: mention what the student got right, what was missing, and the key points from the rubric they should have covered. 2-4 sentences.
- Do not be lenient — grade strictly`;

  const raw = await completeChat(
    [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt },
    ],
    settings,
  );

  try {
    const cleaned = raw.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
    const data = JSON.parse(cleaned) as { correct: boolean; score: number; maxScore: number; explanation: string };
    res.json({
      questionId: payload.questionId,
      correct: data.correct ?? data.score >= data.maxScore * 0.6,
      score: data.score ?? 0,
      maxScore: data.maxScore ?? payload.points,
      explanation: data.explanation ?? raw,
    });
  } catch {
    res.json({
      questionId: payload.questionId,
      correct: false,
      score: 0,
      maxScore: payload.points,
      explanation: raw || 'Grading failed — please try again.',
    });
  }
});

// ── Cheatsheet ────────────────────────────────────────────────────────────────

router.post('/cheatsheets', async (req, res) => {
  res.json({ path: await saveCheatsheet(req.body.content) });
});
