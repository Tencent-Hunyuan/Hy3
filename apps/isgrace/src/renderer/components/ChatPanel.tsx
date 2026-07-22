import { useEffect, useRef, useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import GraceAvatar from './GraceAvatar';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { sendToGrace } from '../services/dispatchGrace';
import { useLang } from '../i18n/useLang';
import type { Module } from '../../types';

const SUPPORTED_EXTS = ['.pdf', '.docx', '.pptx', '.txt', '.md'];

// ── Markdown render components ─────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mdComponents: Record<string, React.ComponentType<any>> = {
  h1: ({ children }: { children: React.ReactNode }) => (
    <h1 style={{ fontSize: 18, fontWeight: 700, color: '#111', margin: '6px 0 8px', letterSpacing: '-0.025em', lineHeight: 1.3 }}>{children}</h1>
  ),
  h2: ({ children }: { children: React.ReactNode }) => (
    <h2 style={{ fontSize: 16, fontWeight: 700, color: '#111', margin: '18px 0 6px', letterSpacing: '-0.015em', lineHeight: 1.3 }}>{children}</h2>
  ),
  h3: ({ children }: { children: React.ReactNode }) => (
    <h3 style={{ fontSize: 15, fontWeight: 700, color: '#333', margin: '14px 0 4px', lineHeight: 1.3 }}>{children}</h3>
  ),
  p: ({ children }: { children: React.ReactNode }) => (
    <p style={{ margin: '0 0 12px', lineHeight: 1.8 }}>{children}</p>
  ),
  ul: ({ children }: { children: React.ReactNode }) => (
    <ul style={{ margin: '0 0 12px', paddingLeft: 22, lineHeight: 1.8 }}>{children}</ul>
  ),
  ol: ({ children }: { children: React.ReactNode }) => (
    <ol style={{ margin: '0 0 12px', paddingLeft: 22, lineHeight: 1.8 }}>{children}</ol>
  ),
  li: ({ children }: { children: React.ReactNode }) => (
    <li style={{ margin: '2px 0' }}>{children}</li>
  ),
  strong: ({ children }: { children: React.ReactNode }) => (
    <strong style={{ fontWeight: 700, color: '#111' }}>{children}</strong>
  ),
  em: ({ children }: { children: React.ReactNode }) => (
    <em style={{ fontStyle: 'italic', color: '#444' }}>{children}</em>
  ),
  hr: () => (
    <hr style={{ border: 'none', borderTop: '1px solid #E8E0D5', margin: '16px 0' }} />
  ),
  blockquote: ({ children }: { children: React.ReactNode }) => (
    <blockquote style={{ borderLeft: '3px solid #E8D84B', paddingLeft: 14, margin: '0 0 12px', color: '#555', fontStyle: 'italic' }}>{children}</blockquote>
  ),
  pre: ({ children }: { children: React.ReactNode }) => (
    <pre style={{ backgroundColor: '#F6F3EE', border: '1px solid #E8E0D5', borderRadius: 8, padding: '12px 14px', overflowX: 'auto', margin: '0 0 14px', fontSize: 13, lineHeight: 1.6, fontFamily: 'ui-monospace, "Cascadia Code", monospace' }}>{children}</pre>
  ),
  code: ({ children, className }: { children: React.ReactNode; className?: string }) => {
    const text = String(children);
    const isBlock = text.includes('\n') || (className ?? '').startsWith('language-');
    return isBlock
      ? <code style={{ fontFamily: 'ui-monospace, "Cascadia Code", monospace', fontSize: 13 }}>{children}</code>
      : <code style={{ backgroundColor: '#F0EDE8', borderRadius: 4, padding: '1px 5px', fontSize: '0.88em', fontFamily: 'ui-monospace, monospace', color: '#b45309' }}>{children}</code>;
  },
  table: ({ children }: { children: React.ReactNode }) => (
    <div style={{ overflowX: 'auto', margin: '4px 0 16px' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 14 }}>{children}</table>
    </div>
  ),
  th: ({ children }: { children: React.ReactNode }) => (
    <th style={{ textAlign: 'left', padding: '7px 12px', borderBottom: '2px solid #E8E0D5', fontWeight: 600, color: '#333', backgroundColor: '#F8F5F0', fontSize: 13 }}>{children}</th>
  ),
  td: ({ children }: { children: React.ReactNode }) => (
    <td style={{ padding: '6px 12px', borderBottom: '1px solid #F0EDE8', color: '#444' }}>{children}</td>
  ),
};

// ── Setup flow types ───────────────────────────────────────────────────────────
type SetupStep = 1 | 2 | 3;

interface SetupState {
  step: SetupStep;
  pendingMsg: string;
  materials: string[];
  purpose: 'university' | 'personal' | '';
  language: 'english' | 'chinese' | 'bilingual' | 'other' | '';
  langOther: string;
}

// SUGGESTIONS are now driven by translations — see useLang() call inside the component

export default function ChatPanel() {
  const {
    chatMessages, isGraceTyping, addChatMessage,
    setSettingsOpen, llmReady,
    activeSubjectId, addMaterial, userName,
    setLanguagePreference, setLearningGoal,
    modules, activeModuleId, updateModule,
  } = useStore();
  const { t } = useLang();

  const [input, setInput]           = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading]   = useState(false);

  // Setup flow state (null = not in setup)
  const [setup, setSetup] = useState<SetupState | null>(null);

  const bottomRef   = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isGraceTyping, setup]);

  // ── File upload ─────────────────────────────────────────────────────────────

  async function uploadFiles(files: FileList | File[]) {
    setUploading(true);
    for (const file of Array.from(files)) {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!SUPPORTED_EXTS.includes(ext)) continue;
      try {
        const material = await api.file.uploadMaterial(file);
        addMaterial(material);
      } catch (e) { console.error('Upload failed', e); }
    }
    setUploading(false);
    const state = useStore.getState();
    api.config.save({ subjects: state.subjects, activeSubjectId: state.activeSubjectId }).catch(() => {});
  }

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pickResolveRef = useRef<(() => void) | null>(null);

  /** Opens the browser's file picker; resolves once the selected files finish uploading. */
  function handlePickFiles(): Promise<void> {
    return new Promise((resolve) => {
      pickResolveRef.current = resolve;
      fileInputRef.current?.click();
    });
  }

  async function handleFilesSelected(e: React.ChangeEvent<HTMLInputElement>) {
    // Snapshot into a real array before clearing the input — e.target.files is a
    // live FileList tied to the input element, so resetting e.target.value (done
    // to allow re-selecting the same file later) empties it out from under us too.
    const files = Array.from(e.target.files ?? []);
    e.target.value = '';
    if (files.length > 0) {
      await uploadFiles(files);
    }
    pickResolveRef.current?.();
    pickResolveRef.current = null;
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    uploadFiles(e.dataTransfer.files);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── First message → triggers setup flow ────────────────────────────────────

  async function handleSend() {
    const text = input.trim();
    if (!text || isGraceTyping) return;
    if (!llmReady) { setSettingsOpen(true); return; }

    const userMsg = {
      id: crypto.randomUUID(), role: 'user' as const,
      content: text, timestamp: new Date().toISOString(),
    };
    addChatMessage(userMsg);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    // First message in a fresh subject → enter setup flow
    const isFirstMessage = chatMessages.length === 0 && activeSubjectId === null;
    if (isFirstMessage && setup === null) {
      setSetup({ step: 1, pendingMsg: text, materials: [], purpose: '', language: '', langOther: '' });
      return;
    }

    // Normal send
    await sendToGrace(text);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  // ── Setup flow handlers ─────────────────────────────────────────────────────

  function handleSetupNext() {
    if (!setup) return;
    if (setup.step < 3) {
      setSetup({ ...setup, step: (setup.step + 1) as SetupStep });
    } else {
      // Commit preferences
      const langMap: Record<string, string> = {
        english: 'English',
        chinese: '中文',
        bilingual: '中文解释，英文专业术语',
        other: setup.langOther.trim() || 'Other',
      };
      const purposeMap: Record<string, string> = {
        university: '大学课程 / University course',
        personal: '个人兴趣 / Personal interest',
      };
      if (setup.language) setLanguagePreference(langMap[setup.language]);
      if (setup.purpose) setLearningGoal(purposeMap[setup.purpose]);
      setSetup(null);
      sendToGrace(setup.pendingMsg);
    }
  }

  function handleSetupSkip() {
    if (!setup) return;
    setSetup(null);
    sendToGrace(setup.pendingMsg);
  }

  // ── Module stage advance (explicit button, not free-text inference) ────────

  async function sendModuleTurn(module: Module, text: string, kind: 'explain-hs' | 'explain-college' | 'generate-cheatsheet' | 'generate-quiz'): Promise<boolean> {
    addChatMessage({ id: crypto.randomUUID(), role: 'user', content: text, timestamp: new Date().toISOString() });
    return sendToGrace(text, {
      kind,
      module: { title: module.title, textbookSectionRef: module.textbookSectionRef, sectionText: module.sectionText },
    });
  }

  async function handleModuleAdvance(module: Module, kind: 'explain-hs' | 'explain-college' | 'generate-quiz') {
    if (kind === 'explain-hs') {
      const succeeded = await sendModuleTurn(
        module,
        `Please explain "${module.title}" at a high-school level, strictly from the textbook section (${module.textbookSectionRef}).`,
        'explain-hs',
      );
      if (succeeded) updateModule(module.id, { stage: 'hs-explained' });
      return;
    }

    if (kind === 'explain-college') {
      // Explanation and cheatsheet are now two separate turns — each gets its own
      // full output budget instead of splitting one between a long explanation
      // and the cheatsheet that follows it (was starving the cheatsheet of room).
      const explained = await sendModuleTurn(
        module,
        `No more questions — please give the college-level explanation for "${module.title}".`,
        'explain-college',
      );
      if (!explained) return; // network error — stage stays put, button lets them retry

      const cheatsheeted = await sendModuleTurn(
        module,
        `Generate the cheatsheet for "${module.title}".`,
        'generate-cheatsheet',
      );
      if (cheatsheeted) updateModule(module.id, { stage: 'college-explained' });
      return;
    }

    // generate-quiz
    const succeeded = await sendModuleTurn(
      module,
      `No more questions — please generate the exam questions for "${module.title}".`,
      'generate-quiz',
    );
    if (succeeded) updateModule(module.id, { stage: 'quiz-ready' });
  }

  // Suggestion chip clicked on home screen
  function handleSuggestion(label: string) {
    setInput(label);
    textareaRef.current?.focus();
  }

  // ── Home state ──────────────────────────────────────────────────────────────

  const isHome = activeSubjectId === null && chatMessages.length === 0 && setup === null;

  if (isHome) {
    return (
      <div
        className="flex flex-col h-full"
        style={{ backgroundColor: '#FEFEFE', position: 'relative' }}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
      >
        {isDragging && <DropOverlay />}
        <HiddenFileInput inputRef={fileInputRef} onFilesSelected={handleFilesSelected} />

        {/* Center welcome */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '48px 40px' }}>
          <div style={{ width: '100%', maxWidth: 700 }}>

            {/* Grace + greeting row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginBottom: 44 }}>
              <GraceAvatar size="md" />
              <div>
                <h1 style={{ fontSize: 26, fontWeight: 700, color: '#111', letterSpacing: '-0.025em', margin: '0 0 6px', lineHeight: 1.2 }}>
                  {t.chatGreeting(userName)}
                </h1>
                <p style={{ fontSize: 15, color: '#999', lineHeight: 1.6, margin: 0 }}>
                  {t.chatSubtitle}
                </p>
              </div>
            </div>

            {/* Suggestion cards — 3 columns */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
              {t.chatSuggestions.map((s) => (
                <button
                  key={s.label}
                  onClick={() => handleSuggestion(s.label)}
                  style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'flex-start',
                    gap: 12, padding: '20px 20px 18px',
                    borderRadius: 12,
                    border: '1.5px solid #EDEAE4',
                    backgroundColor: '#FAFAF8',
                    cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                    transition: 'background-color 0.12s, border-color 0.12s, transform 0.12s',
                  }}
                  onMouseEnter={(e) => {
                    const el = e.currentTarget as HTMLElement;
                    el.style.backgroundColor = '#FEFBE8';
                    el.style.borderColor = '#D8C850';
                    el.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    const el = e.currentTarget as HTMLElement;
                    el.style.backgroundColor = '#FAFAF8';
                    el.style.borderColor = '#EDEAE4';
                    el.style.transform = 'translateY(0)';
                  }}
                >
                  <span style={{ fontSize: 22, lineHeight: 1 }}>{s.emoji}</span>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', margin: '0 0 5px', letterSpacing: '-0.01em' }}>
                      {s.label}
                    </p>
                    <p style={{ fontSize: 12, color: '#AAA', lineHeight: 1.55, margin: 0 }}>
                      {s.desc}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <ChatInputBar
          value={input} onChange={setInput} onKeyDown={handleKeyDown}
          onSend={handleSend} onPickFiles={handlePickFiles}
          uploading={uploading} disabled={isGraceTyping} llmReady={llmReady}
          inputRef={textareaRef}
        />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // ── Chat state (with or without setup card) ─────────────────────────────────

  return (
    <div
      className="flex flex-col h-full"
      style={{ backgroundColor: '#FEFEFE', position: 'relative' }}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
    >
      {isDragging && <DropOverlay />}
      <HiddenFileInput inputRef={fileInputRef} onFilesSelected={handleFilesSelected} />

      {!llmReady && (
        <button
          onClick={() => setSettingsOpen(true)}
          style={{
            margin: '10px 16px 0', padding: '9px 14px', borderRadius: 9,
            backgroundColor: '#FEFBE8', border: '1.5px solid #F4D35E',
            fontSize: 12, color: '#7a6000', cursor: 'pointer',
            textAlign: 'left', fontFamily: 'inherit', lineHeight: 1.5,
          }}
        >
          <strong>{t.chatNoApiKeyBold}</strong>{t.chatNoApiKeySuffix}
        </button>
      )}

      <div className="flex-1 overflow-y-auto" style={{ padding: '24px 0' }}>
        {chatMessages.map((msg, idx) => {
          const isLast = idx === chatMessages.length - 1;
          return msg.role === 'grace'
            ? <GraceMessage key={msg.id} content={msg.content} isStreaming={isGraceTyping && isLast} startedAt={msg.timestamp} />
            : <UserMessage key={msg.id} content={msg.content} />;
        })}

        {/* Setup flow card */}
        {setup && (
          <SetupCard
            setup={setup}
            uploading={uploading}
            onChange={setSetup}
            onNext={handleSetupNext}
            onSkip={handleSetupSkip}
            onPickFiles={handlePickFiles}
          />
        )}

        {/* Active module — stage-gated teaching flow */}
        {!setup && activeModuleId && modules.find(m => m.id === activeModuleId) && (
          <ModuleStageCard
            module={modules.find(m => m.id === activeModuleId)!}
            disabled={isGraceTyping}
            onAdvance={handleModuleAdvance}
          />
        )}

        <div ref={bottomRef} />
      </div>

      <ChatInputBar
        value={input} onChange={setInput} onKeyDown={handleKeyDown}
        onSend={handleSend} onPickFiles={handlePickFiles}
        uploading={uploading}
        disabled={isGraceTyping || setup !== null}
        llmReady={llmReady}
        inputRef={textareaRef}
      />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ── Setup card ─────────────────────────────────────────────────────────────────

function SetupCard({
  setup, uploading, onChange, onNext, onSkip, onPickFiles,
}: {
  setup: SetupState;
  uploading: boolean;
  onChange: (s: SetupState) => void;
  onNext: () => void;
  onSkip: () => void;
  onPickFiles: () => Promise<void>;
}) {
  const uploadedMaterials = useStore((s) => s.uploadedMaterials);
  const addMaterial = useStore((s) => s.addMaterial);
  const { t } = useLang();
  const [linkUrl, setLinkUrl] = useState('');
  const [linkLoading, setLinkLoading] = useState(false);
  const [linkError, setLinkError] = useState('');

  async function handleAddLink() {
    const url = linkUrl.trim();
    if (!url) return;
    const normalized = /^https?:\/\//i.test(url) ? url : 'https://' + url;
    setLinkError('');
    setLinkLoading(true);
    try {
      const material = await api.file.uploadUrl(normalized);
      addMaterial(material);
      setLinkUrl('');
      if (!setup.materials.includes('link')) {
        onChange({ ...setup, materials: [...setup.materials, 'link'] });
      }
      const state = useStore.getState();
      api.config.save({ subjects: state.subjects, activeSubjectId: state.activeSubjectId }).catch(() => {});
    } catch (e) {
      setLinkError(e instanceof Error ? e.message : 'Failed to fetch URL');
    } finally {
      setLinkLoading(false);
    }
  }

  const step = setup.step;
  const uploadedTypes = uploadedMaterials.map((m) => m.type);

  const cardContent = (() => {
    if (step === 1) {
      return (
        <>
          <p style={{ margin: '0 0 14px', fontSize: 14.5, lineHeight: 1.65, color: '#1a1a1a' }}>
            {t.setupStep1Q}<br />
            <span style={{ fontSize: 13, color: '#888' }}>{t.setupStep1Hint}</span>
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {t.setupMatTypes.map((mat) => {
              const checked = setup.materials.includes(mat.id) || uploadedTypes.includes(mat.id as never);

              // ── Link row — URL input instead of file upload ──────────────
              if (mat.id === 'link') {
                const hasLinks = uploadedMaterials.some((m) => m.sourceUrl);
                return (
                  <div key={mat.id} style={{ borderRadius: 8, backgroundColor: hasLinks ? '#FEFBE8' : '#F6F3EE', border: `1.5px solid ${hasLinks ? '#E8D84B' : '#EDEAE4'}`, transition: 'all 0.12s', overflow: 'hidden' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px' }}>
                      <span style={{ fontSize: 15, flexShrink: 0 }}>{mat.emoji}</span>
                      <span style={{ flex: 1, fontSize: 13, color: '#1a1a1a', fontWeight: 500 }}>{mat.label}</span>
                      {hasLinks && <span style={{ fontSize: 11, color: '#92760a', fontWeight: 600 }}>{uploadedMaterials.filter(m => m.sourceUrl).length} added</span>}
                    </div>
                    <div style={{ padding: '0 10px 10px', display: 'flex', gap: 6 }}>
                      <input
                        type="text"
                        value={linkUrl}
                        onChange={(e) => { setLinkUrl(e.target.value); setLinkError(''); }}
                        onKeyDown={(e) => { if (e.key === 'Enter') handleAddLink(); }}
                        placeholder="https://…"
                        disabled={linkLoading}
                        style={{
                          flex: 1, fontSize: 12, padding: '5px 9px', borderRadius: 6,
                          border: '1px solid #DEDAD4', backgroundColor: '#FEFEFE',
                          color: '#333', outline: 'none', fontFamily: 'inherit',
                          opacity: linkLoading ? 0.5 : 1,
                        }}
                      />
                      <button
                        onClick={handleAddLink}
                        disabled={linkLoading || !linkUrl.trim()}
                        style={{
                          fontSize: 11, padding: '5px 12px', borderRadius: 6, flexShrink: 0,
                          border: '1px solid #DEDAD4',
                          backgroundColor: linkUrl.trim() && !linkLoading ? '#1a1a1a' : 'transparent',
                          color: linkUrl.trim() && !linkLoading ? '#FEFEFE' : '#AAA',
                          cursor: linkLoading || !linkUrl.trim() ? 'default' : 'pointer',
                          fontFamily: 'inherit', transition: 'all 0.12s',
                        }}
                      >
                        {linkLoading ? '…' : 'Add'}
                      </button>
                    </div>
                    {linkError && (
                      <p style={{ margin: '0 10px 8px', fontSize: 10, color: '#e57373' }}>{linkError}</p>
                    )}
                  </div>
                );
              }

              // ── File-based rows ──────────────────────────────────────────
              return (
                <div key={mat.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 8, backgroundColor: checked ? '#FEFBE8' : '#F6F3EE', border: `1.5px solid ${checked ? '#E8D84B' : '#EDEAE4'}`, transition: 'all 0.12s' }}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) => {
                      const mats = e.target.checked
                        ? [...setup.materials, mat.id]
                        : setup.materials.filter((m) => m !== mat.id);
                      onChange({ ...setup, materials: mats });
                    }}
                    style={{ width: 15, height: 15, accentColor: '#F4D35E', flexShrink: 0, cursor: 'pointer' }}
                  />
                  <span style={{ fontSize: 15, flexShrink: 0 }}>{mat.emoji}</span>
                  <span style={{ flex: 1, fontSize: 13, color: '#1a1a1a', fontWeight: 500 }}>{mat.label}</span>
                  <button
                    onClick={async () => {
                      await onPickFiles();
                      if (!setup.materials.includes(mat.id)) {
                        onChange({ ...setup, materials: [...setup.materials, mat.id] });
                      }
                    }}
                    disabled={uploading}
                    style={{
                      fontSize: 11, color: '#666', border: '1px solid #DEDAD4',
                      borderRadius: 5, padding: '3px 8px', cursor: uploading ? 'wait' : 'pointer',
                      backgroundColor: '#FEFEFE', fontFamily: 'inherit', flexShrink: 0,
                    }}
                  >
                    {uploading ? '…' : t.setupUpload}
                  </button>
                </div>
              );
            })}
          </div>
        </>
      );
    }

    if (step === 2) {
      return (
        <>
          <p style={{ margin: '0 0 14px', fontSize: 14.5, lineHeight: 1.65, color: '#1a1a1a' }}>
            {t.setupStep2Q}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {t.setupPurposeOpts.map((opt) => (
              <label
                key={opt.id}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '11px 14px', borderRadius: 10, cursor: 'pointer',
                  border: `1.5px solid ${setup.purpose === opt.id ? '#E8D84B' : '#EDEAE4'}`,
                  backgroundColor: setup.purpose === opt.id ? '#FEFBE8' : '#F6F3EE',
                  transition: 'all 0.12s',
                }}
              >
                <input
                  type="radio" name="purpose" value={opt.id}
                  checked={setup.purpose === opt.id}
                  onChange={() => onChange({ ...setup, purpose: opt.id as SetupState['purpose'] })}
                  style={{ accentColor: '#F4D35E', width: 15, height: 15 }}
                />
                <span style={{ fontSize: 16 }}>{opt.emoji}</span>
                <span style={{ fontSize: 14, color: '#1a1a1a', fontWeight: 500 }}>{opt.label}</span>
              </label>
            ))}
          </div>
        </>
      );
    }

    // step === 3 — AI response language (always bilingual labels)
    return (
      <>
        <p style={{ margin: '0 0 14px', fontSize: 14.5, lineHeight: 1.65, color: '#1a1a1a' }}>
          {t.setupStep3Q}
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {t.setupLangOpts.map((opt) => (
            <label
              key={opt.id}
              style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '11px 14px', borderRadius: 10, cursor: 'pointer',
                border: `1.5px solid ${setup.language === opt.id ? '#E8D84B' : '#EDEAE4'}`,
                backgroundColor: setup.language === opt.id ? '#FEFBE8' : '#F6F3EE',
                transition: 'all 0.12s',
              }}
            >
              <input
                type="radio" name="language" value={opt.id}
                checked={setup.language === opt.id}
                onChange={() => onChange({ ...setup, language: opt.id as SetupState['language'] })}
                style={{ accentColor: '#F4D35E', width: 15, height: 15 }}
              />
              <span style={{ fontSize: 15 }}>{opt.emoji}</span>
              <span style={{ fontSize: 14, color: '#1a1a1a', fontWeight: 500 }}>
                {opt.label}
                <span style={{ fontWeight: 400, color: '#888', marginLeft: 6, fontSize: 12 }}>{opt.sub}</span>
              </span>
            </label>
          ))}
        </div>
        {setup.language === 'other' && (
          <input
            autoFocus type="text"
            value={setup.langOther}
            onChange={(e) => onChange({ ...setup, langOther: e.target.value })}
            placeholder={t.setupStep3OtherPlaceholder}
            style={{
              marginTop: 10, width: '100%', padding: '9px 12px', borderRadius: 8,
              border: '1.5px solid #DEDAD4', backgroundColor: '#FEFEFE',
              fontSize: 13, color: '#1a1a1a', outline: 'none',
              fontFamily: 'inherit', boxSizing: 'border-box',
            }}
          />
        )}
      </>
    );
  })();

  const stepLabel = t.setupStepLabels[step - 1];
  const isLastStep = step === 3;
  const canProceed =
    step === 1 ? true :
    step === 2 ? !!setup.purpose :
    !!setup.language && (setup.language !== 'other' || !!setup.langOther.trim());

  return (
    <div style={{ display: 'flex', gap: 14, padding: '4px 24px 20px', maxWidth: 720 }}>
      {/* Grace avatar */}
      <div style={{ flexShrink: 0, marginTop: 2 }}>
        <GraceAvatar size="xs" />
      </div>

      {/* Card */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Step indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              style={{
                width: 22, height: 22, borderRadius: '50%',
                backgroundColor: n === step ? '#1a1a1a' : n < step ? '#F4D35E' : '#EDEAE4',
                color: n === step ? '#FEFEFE' : n < step ? '#1a1a1a' : '#AAA',
                fontSize: 11, fontWeight: 700,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              {n < step ? '✓' : n}
            </div>
          ))}
          <span style={{ fontSize: 12, color: '#888', marginLeft: 2 }}>{stepLabel}</span>
        </div>

        {/* Card body */}
        <div style={{
          backgroundColor: '#FAFAF8', borderRadius: 14,
          border: '1.5px solid #EDEAE4', padding: '18px 20px',
        }}>
          {cardContent}

          {/* Buttons */}
          <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'flex-end' }}>
            <button
              onClick={onSkip}
              style={{
                fontSize: 13, color: '#AAA', border: '1px solid #EDEAE4',
                borderRadius: 8, padding: '7px 14px', cursor: 'pointer',
                backgroundColor: 'transparent', fontFamily: 'inherit',
              }}
            >
              {t.setupSkip}
            </button>
            <button
              onClick={onNext}
              disabled={!canProceed}
              style={{
                fontSize: 13, fontWeight: 600,
                color: canProceed ? '#1a1a1a' : '#AAA',
                backgroundColor: canProceed ? '#F4D35E' : '#EDEAE4',
                border: 'none', borderRadius: 8, padding: '7px 18px',
                cursor: canProceed ? 'pointer' : 'default', fontFamily: 'inherit',
                transition: 'all 0.12s',
              }}
            >
              {isLastStep ? t.setupStart : t.setupNext}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Module stage card ──────────────────────────────────────────────────────────
// Same visual pattern as SetupCard. Advances Module.stage via an explicit button
// click (deterministic), never by parsing the model's free-text reply.

function ModuleStageCard({ module, disabled, onAdvance }: {
  module: Module;
  disabled: boolean;
  onAdvance: (module: Module, kind: 'explain-hs' | 'explain-college' | 'generate-quiz') => void;
}) {
  const next = (() => {
    if (module.stage === 'not-started') {
      return { label: `Explain "${module.title}" — high-school level`, kind: 'explain-hs' as const };
    }
    if (module.stage === 'hs-explained') {
      return { label: 'No more questions — give the college-level explanation', kind: 'explain-college' as const };
    }
    if (module.stage === 'college-explained') {
      return { label: 'No more questions — generate exam questions', kind: 'generate-quiz' as const };
    }
    return null; // 'quiz-ready' — nothing further to do here
  })();

  return (
    <div style={{ display: 'flex', gap: 14, padding: '4px 24px 20px', maxWidth: 720 }}>
      <div style={{ flexShrink: 0, marginTop: 2 }}>
        <GraceAvatar size="xs" />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          backgroundColor: '#FAFAF8', borderRadius: 14,
          border: '1.5px solid #EDEAE4', padding: '14px 18px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
        }}>
          <div style={{ minWidth: 0 }}>
            <p style={{ margin: '0 0 2px', fontSize: 13, fontWeight: 600, color: '#1a1a1a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {module.title}
            </p>
            <p style={{ margin: 0, fontSize: 11.5, color: '#999' }}>{module.textbookSectionRef}</p>
          </div>
          {next ? (
            <button
              onClick={() => onAdvance(module, next.kind)}
              disabled={disabled}
              style={{
                flexShrink: 0, fontSize: 12.5, fontWeight: 600,
                color: disabled ? '#AAA' : '#1a1a1a',
                backgroundColor: disabled ? '#EDEAE4' : '#F4D35E',
                border: 'none', borderRadius: 8, padding: '8px 16px',
                cursor: disabled ? 'default' : 'pointer', fontFamily: 'inherit',
              }}
            >
              {next.label}
            </button>
          ) : (
            <span style={{ flexShrink: 0, fontSize: 12, color: '#7a9e6a', fontWeight: 600 }}>
              ✓ Quiz ready — check the test panel
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Message components ─────────────────────────────────────────────────────────

function GraceMessage({ content, isStreaming, startedAt }: { content: string; isStreaming?: boolean; startedAt: string }) {
  return (
    <div style={{ display: 'flex', gap: 14, padding: '4px 24px 16px', maxWidth: 780, width: '100%' }}>
      <div style={{ flexShrink: 0, marginTop: 2 }}>
        <GraceAvatar size="xs" />
      </div>
      <div style={{ flex: 1, fontSize: 15, color: '#1a1a1a', minWidth: 0, wordBreak: 'break-word' }}>
        {!content
          ? (isStreaming ? <StreamingStats startedAt={startedAt} content={content} /> : <span style={{ color: '#CCCCCC' }}>▋</span>)
          : <>
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                {content}
              </ReactMarkdown>
              {isStreaming && <StreamingStats startedAt={startedAt} content={content} />}
            </>
        }
      </div>
    </div>
  );
}

/** Live "⏱ Ns · ~N tokens" indicator shown while a reply is streaming — ticks every
 * 500ms independent of new content arriving, so a long pause (large context, slow
 * generation) still visibly shows time passing instead of looking frozen. Token
 * count is a rough chars/4 estimate on the accumulated text, not a real API figure. */
function StreamingStats({ startedAt, content }: { startedAt: string; content: string }) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, []);

  const elapsedSec = Math.max(0, (now - new Date(startedAt).getTime()) / 1000);
  const tokens = Math.ceil(content.length / 4);

  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 7,
      fontSize: 12, color: '#BBBBBB', fontVariantNumeric: 'tabular-nums',
      marginTop: content ? 6 : 0, marginLeft: content ? 0 : 0,
    }}>
      {!content && <span style={{ color: '#CCCCCC' }}>▋</span>}
      <span>⏱ {elapsedSec.toFixed(0)}s</span>
      {tokens > 0 && <span>· ~{tokens.toLocaleString()} tokens</span>}
    </span>
  );
}

function UserMessage({ content }: { content: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '4px 24px 16px' }}>
      <div style={{
        maxWidth: '72%', backgroundColor: '#1a1a1a', color: '#FEFEFE',
        borderRadius: 20, padding: '11px 18px', fontSize: 15, lineHeight: 1.65,
        whiteSpace: 'pre-wrap', wordBreak: 'break-word',
      }}>
        {content}
      </div>
    </div>
  );
}

// ── Hidden file input (drives the native file picker) ──────────────────────────

function HiddenFileInput({ inputRef, onFilesSelected }: {
  inputRef: React.RefObject<HTMLInputElement | null>;
  onFilesSelected: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <input
      ref={inputRef}
      type="file"
      multiple
      accept={SUPPORTED_EXTS.join(',')}
      onChange={onFilesSelected}
      style={{ display: 'none' }}
    />
  );
}

// ── Drop overlay ───────────────────────────────────────────────────────────────

function DropOverlay() {
  return (
    <div style={{
      position: 'absolute', inset: 0, zIndex: 50, pointerEvents: 'none',
      backgroundColor: 'rgba(244,211,94,0.10)',
      border: '2px dashed #F4D35E', borderRadius: 0,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <span style={{ fontSize: 15, color: '#888', fontWeight: 500, pointerEvents: 'none' }}>↓</span>
    </div>
  );
}

// ── Input bar ─────────────────────────────────────────────────────────────────

function ChatInputBar({ value, onChange, onKeyDown, onSend, onPickFiles, uploading, disabled, llmReady, inputRef }: {
  value: string;
  onChange: (v: string) => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  onSend: () => void;
  onPickFiles: () => void;
  uploading: boolean;
  disabled: boolean;
  llmReady: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
}) {
  const { t } = useLang();
  return (
    <div style={{ padding: '10px 16px 16px', flexShrink: 0 }}>
      <div style={{
        display: 'flex', alignItems: 'flex-end', gap: 0,
        backgroundColor: '#F6F3EE', borderRadius: 18,
        border: '1.5px solid #DEDAD4', padding: '6px 6px 6px 4px',
      }}>
        {/* Upload button */}
        <button
          onClick={onPickFiles}
          disabled={uploading}
          title={t.chatUploadTitle}
          style={{
            flexShrink: 0, width: 32, height: 32, borderRadius: 12,
            border: 'none', backgroundColor: 'transparent',
            cursor: uploading ? 'wait' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: uploading ? '#F4D35E' : '#AAAAAA', transition: 'color 0.15s, background-color 0.15s',
          }}
          onMouseEnter={(e) => { (e.currentTarget).style.color = '#888'; (e.currentTarget).style.backgroundColor = '#EDEAE4'; }}
          onMouseLeave={(e) => { (e.currentTarget).style.color = uploading ? '#F4D35E' : '#AAAAAA'; (e.currentTarget).style.backgroundColor = 'transparent'; }}
        >
          {uploading
            ? <span style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid #F4D35E', borderTopColor: 'transparent', animation: 'spin 0.7s linear infinite', display: 'block' }} />
            : <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          }
        </button>

        {/* Textarea */}
        <textarea
          ref={inputRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={disabled && !uploading ? t.chatPlaceholderSetup : llmReady ? t.chatPlaceholder : t.chatPlaceholderNoKey}
          rows={1}
          disabled={disabled}
          style={{
            flex: 1, resize: 'none', border: 'none', outline: 'none',
            backgroundColor: 'transparent', padding: '7px 8px',
            fontSize: 15, lineHeight: 1.5, color: '#1a1a1a',
            maxHeight: 160, fontFamily: 'inherit', opacity: disabled ? 0.5 : 1,
          }}
          onInput={(e) => {
            const el = e.target as HTMLTextAreaElement;
            el.style.height = 'auto';
            el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
          }}
        />

        {/* Send button */}
        <button
          onClick={onSend}
          disabled={!value.trim() || disabled}
          style={{
            flexShrink: 0, width: 32, height: 32, borderRadius: 12,
            backgroundColor: value.trim() && !disabled ? '#1a1a1a' : '#DEDAD4',
            border: 'none', cursor: value.trim() && !disabled ? 'pointer' : 'default',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'background-color 0.15s',
          }}
        >
          {disabled && !uploading
            ? <span style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid #AAA', borderTopColor: 'transparent', animation: 'spin 0.7s linear infinite', display: 'block' }} />
            : <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={value.trim() && !disabled ? '#FEFEFE' : '#AAA'} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
          }
        </button>
      </div>
    </div>
  );
}
