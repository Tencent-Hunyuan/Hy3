import { useStore } from '../store/useStore';
import { api } from './api';
import { buildGraceMessages, type StructuredDirective } from './gracePrompt';
import { sliceSection, stripLikelyTableOfContents } from './sectionSlicer';
import type { Module, TestSession } from '../../types';

export function formatError(code: string): string {
  if (code === 'NO_API_KEY') return '⚠️ No API key set. Open Settings to add your key.';
  if (code === 'INVALID_API_KEY') return '⚠️ Invalid API key. Check your key in Settings.';
  if (code === 'INSUFFICIENT_CREDITS') return '⚠️ Insufficient credits. Please top up.';
  if (code === 'RATE_LIMITED') return '⚠️ Rate limited. Please wait a moment.';
  if (code.startsWith('NETWORK')) return `⚠️ Network error: ${code.slice(8)}`;
  return `⚠️ Error: ${code}`;
}

// ── Signal extraction helpers ──────────────────────────────────────────────────

function extractCheatsheet(content: string): { title: string; inner: string; cleaned: string } | null {
  const re = /<CHEATSHEET(?:\s+title="([^"]*)")?>([\s\S]*?)<\/CHEATSHEET>/i;
  const match = content.match(re);
  if (!match) return null;
  const title = match[1]?.trim() || 'Cheatsheet';
  const inner = match[2].trim();
  const cleaned = content.replace(re, '').replace(/\n{3,}/g, '\n\n').trim();
  return { title, inner, cleaned };
}

function extractTestJson(content: string): { title: string; inner: string; cleaned: string } | null {
  // Try exact match with closing tag first
  const reFull = /<TEST_JSON(?:\s+title="([^"]*)")?>([\s\S]*?)<\/TEST_JSON>/i;
  const fullMatch = content.match(reFull);
  if (fullMatch) {
    const title = fullMatch[1]?.trim() || 'Test';
    const inner = fullMatch[2].trim();
    const cleaned = content.replace(reFull, '').replace(/\n{3,}/g, '\n\n').trim();
    return { title, inner, cleaned };
  }

  // Fallback: closing tag missing (truncated response) — find opening tag and extract JSON by brace-counting
  const reOpen = /<TEST_JSON(?:\s+title="([^"]*)")?>/i;
  const openMatch = content.match(reOpen);
  if (!openMatch || openMatch.index === undefined) return null;

  const title = openMatch[1]?.trim() || 'Test';
  const afterTag = content.slice(openMatch.index + openMatch[0].length);

  // Walk forward, tracking brace depth to find the end of the JSON object
  const jsonStart = afterTag.indexOf('{');
  if (jsonStart === -1) return null;
  let depth = 0;
  let inStr = false;
  let esc = false;
  let jsonEnd = -1;
  for (let i = jsonStart; i < afterTag.length; i++) {
    const c = afterTag[i];
    if (esc) { esc = false; continue; }
    if (c === '\\' && inStr) { esc = true; continue; }
    if (c === '"') { inStr = !inStr; continue; }
    if (inStr) continue;
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) { jsonEnd = i; break; } }
  }
  if (jsonEnd === -1) return null;

  const inner = afterTag.slice(jsonStart, jsonEnd + 1);
  const cleaned = content.slice(0, openMatch.index).replace(/\n{3,}/g, '\n\n').trim();
  return { title, inner, cleaned };
}

function parseTestJson(json: string): TestSession | null {
  try {
    // Strip markdown code fences if the model wrapped the JSON
    const stripped = json.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim();
    const data = JSON.parse(stripped) as { questions: TestSession['questions'] };
    if (!Array.isArray(data.questions)) return null;
    return {
      id: `test_${Date.now()}`,
      questions: data.questions,
      answers: {},
    };
  } catch { return null; }
}

function extractModulesJson(content: string): { inner: string; cleaned: string } | null {
  const reFull = /<MODULES_JSON>([\s\S]*?)<\/MODULES_JSON>/i;
  const fullMatch = content.match(reFull);
  if (fullMatch) {
    const inner = fullMatch[1].trim();
    const cleaned = content.replace(reFull, '').replace(/\n{3,}/g, '\n\n').trim();
    return { inner, cleaned };
  }

  // Fallback: closing tag missing (truncated response) — find opening tag and extract JSON by bracket-counting
  const reOpen = /<MODULES_JSON>/i;
  const openMatch = content.match(reOpen);
  if (!openMatch || openMatch.index === undefined) return null;

  const afterTag = content.slice(openMatch.index + openMatch[0].length);
  const jsonStart = afterTag.indexOf('[');
  if (jsonStart === -1) return null;
  let depth = 0;
  let inStr = false;
  let esc = false;
  let jsonEnd = -1;
  for (let i = jsonStart; i < afterTag.length; i++) {
    const c = afterTag[i];
    if (esc) { esc = false; continue; }
    if (c === '\\' && inStr) { esc = true; continue; }
    if (c === '"') { inStr = !inStr; continue; }
    if (inStr) continue;
    if (c === '[') depth++;
    else if (c === ']') { depth--; if (depth === 0) { jsonEnd = i; break; } }
  }
  if (jsonEnd === -1) return null;

  const inner = afterTag.slice(jsonStart, jsonEnd + 1);
  const cleaned = content.slice(0, openMatch.index).replace(/\n{3,}/g, '\n\n').trim();
  return { inner, cleaned };
}

interface RawModuleEntry {
  title: string;
  textbookSectionRef: string;
  startAnchor?: string;
  endAnchor?: string;
  /** Approximate character offset in the textbook where this anchor is expected — lets
   *  sliceSection pick the right occurrence when a heading repeats (e.g. as a running
   *  header on every page of its chapter). Undefined when no position estimate exists. */
  hintIndex?: number;
}

function parseModulesJson(json: string): RawModuleEntry[] | null {
  try {
    const stripped = json.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim();
    const data = JSON.parse(stripped) as RawModuleEntry[];
    if (!Array.isArray(data)) return null;
    return data;
  } catch { return null; }
}

/** Resolves each raw module entry's verbatim anchors into a cached, pre-sliced `sectionText` — falls back to no slice (whole textbook) if the anchors don't match. */
function resolveModules(raw: RawModuleEntry[], textbookContent: string | undefined): Module[] {
  return raw.map((m, idx) => {
    const sectionText = textbookContent && m.startAnchor
      ? sliceSection(textbookContent, m.startAnchor, m.endAnchor, m.hintIndex) ?? undefined
      : undefined;
    return {
      id: `mod_${Date.now()}_${idx}`,
      title: m.title,
      textbookSectionRef: m.textbookSectionRef,
      stage: 'not-started' as const,
      ...(sectionText ? { sectionText } : {}),
    };
  });
}

// ── Public API ───────────────────────────────────────────────────────────────

/**
 * Sends one message to Grace, streams the reply into the chat, and — once the
 * stream completes — chain-extracts any embedded signal tags (<CHEATSHEET>,
 * <TEST_JSON>, <MODULES_JSON>) from a single running `cleaned` string. Each
 * extractor must operate on the previous one's `cleaned` output, never the
 * original content, or an earlier extractor's tag-stripping gets clobbered
 * when multiple tags co-occur in one message (e.g. the exam-prep flow, which
 * emits both a cheatsheet and a test in the same turn).
 */
export async function sendToGrace(text: string, directive?: StructuredDirective): Promise<boolean> {
  const initial = useStore.getState();
  initial.setGraceTyping(true);
  const graceId = crypto.randomUUID();
  initial.addChatMessage({ id: graceId, role: 'grace', content: '', timestamp: new Date().toISOString() });

  const history = useStore.getState().chatMessages.filter((m) => m.id !== graceId);
  const s = useStore.getState();

  // Module-scoped turns (explain-hs/explain-college/generate-quiz) reuse the section
  // already sliced out at module-extraction time, instead of resending the whole
  // textbook every turn — cuts input size drastically for large textbooks and keeps
  // the model from having to self-locate the section inside an unrelated wall of text.
  const moduleSectionText =
    directive && directive.kind !== 'extract-modules' && directive.kind !== 'scan-chapter-starts' && directive.kind !== 'exam-prep'
      ? directive.module.sectionText
      : undefined;

  const messages = buildGraceMessages({
    userMessage: text, chatHistory: history,
    courseName: s.courseInfo.name,
    learningGoal: s.learningGoal,
    languagePreference: s.languagePreference,
    studyGuide: s.studyGuide,
    cheatsheet: s.cheatsheets.map(cs => `## ${cs.title}\n\n${cs.content}`).join('\n\n---\n\n'),
    // Pass all materials with content; textbook content is swapped for the module's
    // pre-sliced section when one is available, other materials go through in full.
    // For extract-modules specifically, the ToC is stripped out of what's shown —
    // it looks exactly like a clean heading to the model and gets grabbed as the
    // anchor instead of the real, later chapter heading (see sectionSlicer.ts).
    materials: s.uploadedMaterials
      .filter((m) => m.content)
      .map((m) => ({
        name: m.name,
        content: moduleSectionText && m.type === 'textbook'
          ? moduleSectionText
          : directive?.kind === 'extract-modules' && m.type === 'textbook'
          ? stripLikelyTableOfContents(m.content!)
          : m.content!,
        sourceUrl: m.sourceUrl,
        type: m.type,
      })),
    directive,
  });

  // Hy3-specific reasoning-effort tuning: the Beginner Pass is a fast, plain-language
  // explanation that doesn't need deep reasoning. Everything else (Intermediate Pass,
  // cheatsheet, quiz, exam-prep) stays on the model's own default ("high") since those
  // calls must stay tightly aligned with the source material.
  const reasoningEffort = directive?.kind === 'explain-hs' ? ('low' as const) : undefined;

  let succeeded = true;

  await api.llm.chat({ messages, reasoningEffort }, (chunk) => {
    if (chunk.error) {
      succeeded = false;
      useStore.getState().updateLastMessage(graceId, formatError(chunk.error));
      useStore.getState().setGraceTyping(false);
      return;
    }
    if (!chunk.done) {
      useStore.setState((st) => ({
        chatMessages: st.chatMessages.map((m) =>
          m.id === graceId ? { ...m, content: m.content + chunk.delta } : m
        ),
      }));
      return;
    }

    const msg = useStore.getState().chatMessages.find(m => m.id === graceId);
    if (msg?.content) {
      let cleaned = msg.content;

      const csMatch = extractCheatsheet(cleaned);
      if (csMatch) {
        cleaned = csMatch.cleaned;
        useStore.getState().addCheatsheet({
          id: `cs_${Date.now()}`,
          title: csMatch.title,
          content: csMatch.inner,
          createdAt: new Date().toISOString(),
        });
        useStore.getState().setLayoutMode('cowork');
        useStore.getState().setActivePanel('folder');
        api.cheatsheet.save(csMatch.inner).catch(() => {});
      }

      const testMatch = extractTestJson(cleaned);
      if (testMatch) {
        const session = parseTestJson(testMatch.inner);
        if (session) {
          cleaned = testMatch.cleaned;
          useStore.getState().addTest({
            id: session.id,
            title: testMatch.title,
            session,
            createdAt: new Date().toISOString(),
          });
          useStore.getState().setActiveTest(session);
        }
      }

      const modulesMatch = extractModulesJson(cleaned);
      if (modulesMatch) {
        const rawModules = parseModulesJson(modulesMatch.inner);
        if (rawModules) {
          cleaned = modulesMatch.cleaned;
          const textbookContent = useStore.getState().uploadedMaterials.find(m => m.type === 'textbook')?.content;
          // No chunk info here (single-pass path) — estimate each module's position
          // proportionally by its order in the returned list, so sliceSection still
          // has something better than "last occurrence" to disambiguate a repeated heading.
          const withHints = textbookContent
            ? rawModules.map((m, idx) => ({ ...m, hintIndex: Math.round((idx / rawModules.length) * textbookContent.length) }))
            : rawModules;
          useStore.getState().setModules(resolveModules(withHints, textbookContent));
        }
      }

      if (cleaned !== msg.content) {
        useStore.setState(st => ({
          chatMessages: st.chatMessages.map(m => m.id === graceId ? { ...m, content: cleaned } : m),
        }));
      }
    }
    useStore.getState().setGraceTyping(false);
  });

  return succeeded;
}

// ── Chapter/module extraction — chunked for oversized materials ────────────────
// A single Hy3 call can only see so much of the material at once. Most uploads
// fit that easily and go through the single-pass path above unchanged. Books
// too large for one context window get scanned in sequential, overlapping
// chunks instead, so chapters beyond whatever the first window covers aren't
// silently missed — each chunk only reports chapters that actually start
// within it; end boundaries are derived from chapter order afterward rather
// than asked of the model per chunk.

const CHUNK_SIZE = 200_000;
const CHUNK_OVERLAP = 2_000;

function splitIntoChunks(text: string, size: number, overlap: number): { text: string; start: number }[] {
  if (text.length <= size) return [{ text, start: 0 }];
  const chunks: { text: string; start: number }[] = [];
  let start = 0;
  while (start < text.length) {
    const end = Math.min(start + size, text.length);
    chunks.push({ text: text.slice(start, end), start });
    if (end >= text.length) break;
    start = end - overlap;
  }
  return chunks;
}

async function scanChunkForChapterStarts(
  chunkText: string, chunkIndex: number, chunkCount: number, alreadyFound: RawModuleEntry[],
  s: { courseInfo: { name: string }; learningGoal: string; languagePreference: string },
): Promise<RawModuleEntry[]> {
  const messages = buildGraceMessages({
    userMessage: `Scan chunk ${chunkIndex + 1} of ${chunkCount} for new chapter starts.`,
    chatHistory: [],
    courseName: s.courseInfo.name,
    learningGoal: s.learningGoal,
    languagePreference: s.languagePreference,
    materials: [{ name: 'textbook (chunk)', content: chunkText, type: 'textbook' }],
    directive: {
      kind: 'scan-chapter-starts',
      chunkIndex, chunkCount,
      alreadyFound: alreadyFound.map(f => ({ title: f.title, textbookSectionRef: f.textbookSectionRef })),
    },
  });

  let text = '';
  let errored = false;
  await api.llm.chat({ messages }, (chunk) => {
    if (chunk.error) { errored = true; return; }
    if (chunk.delta) text += chunk.delta;
  });
  if (errored) throw new Error('CHUNK_SCAN_FAILED');

  const match = extractModulesJson(text);
  if (!match) return [];
  return parseModulesJson(match.inner) ?? [];
}

/**
 * Extracts a textbook's chapter list. Delegates to the normal single-pass
 * sendToGrace() path when the material fits in one context window (the common
 * case — unchanged behavior, same speed). Larger materials are scanned in
 * chunks via scanChunkForChapterStarts() and resolved into modules here.
 */
export async function runExtractModules(hasSyllabus: boolean): Promise<boolean> {
  const s = useStore.getState();
  const textbook = s.uploadedMaterials.find(m => m.type === 'textbook');
  const fullText = textbook?.content ?? '';
  const scanText = stripLikelyTableOfContents(fullText);

  if (scanText.length <= CHUNK_SIZE) {
    const text = hasSyllabus
      ? 'Please extract the module list from the uploaded module outline / syllabus.'
      : "Please break the uploaded textbook into modules by its own chapters, so I can study it chapter by chapter.";
    return sendToGrace(text, { kind: 'extract-modules' });
  }

  const graceId = crypto.randomUUID();
  useStore.getState().setGraceTyping(true);
  useStore.getState().addChatMessage({ id: graceId, role: 'grace', content: '', timestamp: new Date().toISOString() });

  const chunks = splitIntoChunks(scanText, CHUNK_SIZE, CHUNK_OVERLAP);
  const found: RawModuleEntry[] = [];

  for (let i = 0; i < chunks.length; i++) {
    useStore.getState().updateLastMessage(graceId, `Scanning the material for chapters — part ${i + 1} of ${chunks.length}...`);
    let newOnes: RawModuleEntry[];
    try {
      newOnes = await scanChunkForChapterStarts(chunks[i].text, i, chunks.length, found, s);
    } catch {
      useStore.getState().updateLastMessage(graceId, `⚠️ Network error while scanning part ${i + 1} of ${chunks.length}. Try "Split into chapters" again.`);
      useStore.getState().setGraceTyping(false);
      return false;
    }
    // chunks[i].start is an offset into scanText (ToC-stripped), not the stored
    // fullText used for slicing — close enough as a position estimate since
    // stripping only shifts things by however much ToC text was cut, tiny next
    // to how far apart repeated headings typically land.
    for (const m of newOnes) {
      if (m.title && !found.some(f => f.title === m.title)) found.push({ ...m, hintIndex: chunks[i].start });
    }
  }

  if (found.length === 0) {
    useStore.getState().updateLastMessage(graceId, "I scanned the material but couldn't find clear chapter boundaries. Try naming a chapter directly in chat instead.");
    useStore.getState().setGraceTyping(false);
    return false;
  }

  const withEndAnchors: RawModuleEntry[] = found.map((m, idx) => ({
    ...m,
    endAnchor: idx + 1 < found.length ? found[idx + 1].startAnchor : '',
  }));

  useStore.getState().setModules(resolveModules(withEndAnchors, fullText));
  useStore.getState().updateLastMessage(
    graceId,
    `Split the material into ${found.length} modules (it's larger than one pass can cover, so I scanned it in ${chunks.length} parts). Click a module in the panel to start.`,
  );
  useStore.getState().setGraceTyping(false);
  return true;
}
