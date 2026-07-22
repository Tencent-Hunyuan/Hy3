import { useState, useEffect, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { sendToGrace, runExtractModules } from '../services/dispatchGrace';
import { useLang } from '../i18n/useLang';
import type { CheatsheetEntry, Material, ModuleStage } from '../../types';

const STAGE_LABELS: Record<ModuleStage, string> = {
  'not-started': 'Not started',
  'hs-explained': 'HS pass done',
  'college-explained': 'College pass done',
  'quiz-ready': 'Quiz ready',
};

type ViewMode = 'list' | 'cheatsheet' | 'guide';

export default function ResourcePanel() {
  const {
    uploadedMaterials, cheatsheets, studyGuide, tests,
    removeMaterial, addMaterial, updateMaterialType, setActivePanel, setActiveTest,
    setLayoutMode, modules, activeModuleId, setActiveModuleId, addChatMessage, isGraceTyping,
  } = useStore();
  const { t } = useLang();

  const [view, setView] = useState<ViewMode>('list');
  const [viewingCS, setViewingCS] = useState<CheatsheetEntry | null>(null);
  const [uploading, setUploading] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [urlLoading, setUrlLoading] = useState(false);
  const [urlError, setUrlError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Reset view if content disappears
  useEffect(() => {
    if (view === 'cheatsheet' && cheatsheets.length === 0) { setView('list'); setLayoutMode('normal'); }
    if (view === 'guide' && !studyGuide) { setView('list'); setLayoutMode('normal'); }
  }, [cheatsheets, studyGuide, view]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-open latest cheatsheet when a new one is generated
  const prevCSCount = useCallback(() => cheatsheets.length, [cheatsheets]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (cheatsheets.length > 0) {
      const latest = cheatsheets[cheatsheets.length - 1];
      setViewingCS(latest);
      setView('cheatsheet');
      setLayoutMode('cowork');
    }
  }, [cheatsheets.length]); // eslint-disable-line react-hooks/exhaustive-deps
  void prevCSCount;

  const handleBack = useCallback(() => {
    setView('list');
    setLayoutMode('normal');
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handlePickFiles() {
    fileInputRef.current?.click();
  }

  async function uploadFileList(files: File[]) {
    if (files.length === 0) return;
    setUploading(true);
    for (const file of files) {
      try {
        const material = await api.file.uploadMaterial(file);
        addMaterial(material);
      } catch (err) { console.error('Upload failed', err); }
    }
    setUploading(false);
    const state = useStore.getState();
    api.config.save({ subjects: state.subjects, activeSubjectId: state.activeSubjectId }).catch(() => {});
  }

  const [isDragging, setIsDragging] = useState(false);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    uploadFileList(Array.from(e.dataTransfer.files));
  }

  async function handleFilesSelected(e: React.ChangeEvent<HTMLInputElement>) {
    // Snapshot into a real array before clearing the input — e.target.files is a
    // live FileList tied to the input element, so resetting e.target.value (done
    // to allow re-selecting the same file later) empties it out from under us too.
    const files = Array.from(e.target.files ?? []);
    e.target.value = '';
    await uploadFileList(files);
  }

  async function handleAddUrl() {
    const url = urlInput.trim();
    if (!url) return;
    let normalized = url;
    if (!/^https?:\/\//i.test(normalized)) normalized = 'https://' + normalized;
    setUrlError('');
    setUrlLoading(true);
    try {
      const material = await api.file.uploadUrl(normalized);
      addMaterial(material);
      setUrlInput('');
      const state = useStore.getState();
      api.config.save({ subjects: state.subjects, activeSubjectId: state.activeSubjectId }).catch(() => {});
    } catch (e) {
      setUrlError(e instanceof Error ? e.message : 'Failed to fetch URL');
    } finally {
      setUrlLoading(false);
    }
  }

  async function handleExtractModules() {
    const hasSyllabus = uploadedMaterials.some(m => m.type === 'syllabus');
    const text = hasSyllabus
      ? 'Please extract the module list from the uploaded module outline / syllabus.'
      : "Please break the uploaded textbook into modules by its own chapters, so I can study it chapter by chapter.";
    addChatMessage({ id: crypto.randomUUID(), role: 'user', content: text, timestamp: new Date().toISOString() });
    await runExtractModules(hasSyllabus);
  }

  async function handleExamPrep() {
    const text = 'Please prepare a cheatsheet and practice quiz for my upcoming exam, based on the exam guide and the textbook.';
    addChatMessage({ id: crypto.randomUUID(), role: 'user', content: text, timestamp: new Date().toISOString() });
    await sendToGrace(text, { kind: 'exam-prep' });
  }

  // ── Expanded content views ──────────────────────────────────────────────────

  if (view === 'cheatsheet' && viewingCS) {
    return (
      <div className="flex flex-col h-full" style={{ backgroundColor: '#FEFEFE' }}>
        <PanelHeader
          title={viewingCS.title}
          onBack={handleBack}
          onCopy={() => navigator.clipboard.writeText(viewingCS.content).catch(() => {})}
        />
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={csComponents}
          >
            {viewingCS.content}
          </ReactMarkdown>
        </div>
      </div>
    );
  }

  if (view === 'guide' && studyGuide) {
    return (
      <div className="flex flex-col h-full" style={{ backgroundColor: '#FEFEFE' }}>
        <PanelHeader title={t.resStudyGuide} onBack={handleBack} />
        <div style={{
          flex: 1, overflowY: 'auto', padding: '16px 18px',
          fontSize: 13, lineHeight: 1.8, color: '#1a1a1a',
          whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        }}>
          {studyGuide}
        </div>
      </div>
    );
  }

  // ── Compact list view ───────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full overflow-y-auto" style={{ backgroundColor: '#FEFEFE' }}>

      {/* Materials */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.pptx,.txt,.md"
        onChange={handleFilesSelected}
        style={{ display: 'none' }}
      />
      <section
        style={{ padding: '16px 14px 12px' }}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <span style={{ fontSize: 10, fontWeight: 700, color: '#BBBBBB', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            {t.resMaterials}
          </span>
          <button
            onClick={handlePickFiles}
            disabled={uploading}
            style={{
              fontSize: 11, color: '#888', border: '1px solid #DEDAD4',
              borderRadius: 5, padding: '2px 8px', cursor: 'pointer',
              backgroundColor: 'transparent', fontFamily: 'inherit',
              opacity: uploading ? 0.5 : 1, transition: 'opacity 0.15s',
            }}
          >
            {uploading ? '…' : t.resAdd}
          </button>
        </div>

        {uploadedMaterials.length === 0 ? (
          <button
            onClick={handlePickFiles}
            style={{
              width: '100%', padding: '12px 10px', borderRadius: 8,
              border: `1.5px dashed ${isDragging ? '#F4D35E' : '#E0DBD4'}`,
              backgroundColor: isDragging ? '#FEFBE8' : 'transparent',
              cursor: 'pointer', fontSize: 12, color: isDragging ? '#8a7a3a' : '#C0BAB2',
              textAlign: 'center', fontFamily: 'inherit', transition: 'all 0.12s',
            }}
          >
            {t.resDropHint}
          </button>
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 1 }}>
            {uploadedMaterials.map(mat => (
              <li
                key={mat.id}
                className="group"
                style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '5px 6px', borderRadius: 6 }}
              >
                {mat.sourceUrl ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#BBBBBB" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                  </svg>
                ) : (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#BBBBBB" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                  </svg>
                )}
                <span style={{
                  flex: 1, fontSize: 12, color: '#444',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}
                  title={mat.sourceUrl ?? mat.name}
                >
                  {mat.name}
                </span>
                <select
                  value={mat.type}
                  onChange={(e) => {
                    updateMaterialType(mat.id, e.target.value as Material['type']);
                    const state = useStore.getState();
                    api.config.save({ subjects: state.subjects }).catch(() => {});
                  }}
                  title="Material type — used to scope module teaching and exam-prep"
                  style={{
                    fontSize: 10, color: '#888', border: '1px solid #DEDAD4',
                    borderRadius: 5, padding: '2px 4px', backgroundColor: 'transparent',
                    fontFamily: 'inherit', flexShrink: 0, cursor: 'pointer',
                  }}
                >
                  <option value="textbook">textbook</option>
                  <option value="syllabus">syllabus</option>
                  <option value="guide">guide</option>
                  <option value="exam">exam</option>
                  <option value="other">other</option>
                </select>
                <button
                  onClick={() => {
                    removeMaterial(mat.id);
                    const state = useStore.getState();
                    api.config.save({ subjects: state.subjects }).catch(() => {});
                  }}
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{
                    color: '#CCC', background: 'none', border: 'none',
                    cursor: 'pointer', fontSize: 16, lineHeight: 1,
                    padding: '0 2px', flexShrink: 0,
                  }}
                  title="Remove"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* URL input */}
        <div style={{ marginTop: 8 }}>
          <div style={{ display: 'flex', gap: 4 }}>
            <input
              type="text"
              value={urlInput}
              onChange={(e) => { setUrlInput(e.target.value); setUrlError(''); }}
              onKeyDown={(e) => { if (e.key === 'Enter') handleAddUrl(); }}
              placeholder="Paste a URL…"
              disabled={urlLoading}
              style={{
                flex: 1, fontSize: 11, padding: '4px 8px', borderRadius: 5,
                border: '1px solid #DEDAD4', backgroundColor: '#FEFEFE',
                color: '#444', outline: 'none', fontFamily: 'inherit',
                opacity: urlLoading ? 0.5 : 1,
              }}
            />
            <button
              onClick={handleAddUrl}
              disabled={urlLoading || !urlInput.trim()}
              style={{
                fontSize: 11, padding: '4px 10px', borderRadius: 5, flexShrink: 0,
                border: '1px solid #DEDAD4', backgroundColor: 'transparent',
                cursor: urlLoading || !urlInput.trim() ? 'default' : 'pointer',
                color: '#888', fontFamily: 'inherit',
                opacity: urlLoading || !urlInput.trim() ? 0.45 : 1,
              }}
            >
              {urlLoading ? '…' : 'Add'}
            </button>
          </div>
          {urlError && (
            <p style={{ margin: '4px 0 0', fontSize: 10, color: '#e57373' }}>{urlError}</p>
          )}
        </div>
      </section>

      {/* Modules — course mode splits by the syllabus/module outline; self-study mode splits by the textbook's own chapters */}
      {(modules.length > 0 || uploadedMaterials.some(m => m.type === 'syllabus' || m.type === 'textbook')) && (
        <>
          <div style={{ margin: '2px 14px', borderTop: '1px solid #F0EBE4' }} />
          <section style={{ padding: '12px 14px 16px' }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: '#BBBBBB', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'block', marginBottom: 8 }}>
              Modules
            </span>
            {modules.length === 0 && (
              <>
                <p style={{ margin: '0 0 8px', fontSize: 12, color: '#999', lineHeight: 1.5 }}>
                  Split your material into modules to get a guided, button-driven flow instead of typing chapter names in chat.
                </p>
                <button
                  onClick={handleExtractModules}
                  disabled={isGraceTyping}
                  style={{
                    width: '100%', fontSize: 12.5, fontWeight: 600, color: '#1a1a1a',
                    border: 'none', borderRadius: 8, padding: '9px 12px',
                    cursor: isGraceTyping ? 'wait' : 'pointer',
                    backgroundColor: '#F4D35E', fontFamily: 'inherit',
                    opacity: isGraceTyping ? 0.5 : 1,
                  }}
                >
                  {uploadedMaterials.some(m => m.type === 'syllabus') ? 'Extract module list' : 'Split into chapters'}
                </button>
              </>
            )}
            {modules.length > 0 && !activeModuleId && (
              <p style={{ margin: '0 0 8px', fontSize: 11.5, color: '#999' }}>
                Click a module below to start learning it.
              </p>
            )}
            {modules.length > 0 && (
              <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 1 }}>
                {modules.map(mod => (
                  <li key={mod.id}>
                    <button
                      onClick={() => setActiveModuleId(mod.id)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 8, width: '100%',
                        padding: '7px 8px', borderRadius: 7, textAlign: 'left',
                        border: mod.id === activeModuleId ? '1px solid #F4D35E' : '1px solid #F0EBE4',
                        backgroundColor: mod.id === activeModuleId ? '#FEFBE8' : 'transparent',
                        cursor: 'pointer', fontFamily: 'inherit', transition: 'background-color 0.1s',
                      }}
                      onMouseEnter={(e) => { if (mod.id !== activeModuleId) e.currentTarget.style.backgroundColor = '#FEF9EC'; }}
                      onMouseLeave={(e) => { if (mod.id !== activeModuleId) e.currentTarget.style.backgroundColor = 'transparent'; }}
                    >
                      <span style={{
                        flex: 1, fontSize: 12, color: '#333',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {mod.title}
                      </span>
                      <span style={{ flexShrink: 0, fontSize: 10, color: '#999' }}>{STAGE_LABELS[mod.stage]}</span>
                      <svg style={{ flexShrink: 0 }} width="9" height="9" viewBox="0 0 12 12" fill="none"
                        stroke="#CCCCCC" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="4 2 8 6 4 10" />
                      </svg>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}

      {/* Exam prep */}
      {uploadedMaterials.some(m => m.type === 'exam') && (
        <>
          <div style={{ margin: '2px 14px', borderTop: '1px solid #F0EBE4' }} />
          <section style={{ padding: '12px 14px 16px' }}>
            <button
              onClick={handleExamPrep}
              disabled={isGraceTyping}
              style={{
                width: '100%', padding: '9px 12px', borderRadius: 8,
                border: '1.5px solid #F4D35E', backgroundColor: isGraceTyping ? '#EDEAE4' : '#FEFBE8',
                cursor: isGraceTyping ? 'wait' : 'pointer', fontSize: 12.5, fontWeight: 600,
                color: '#7a6000', textAlign: 'center', fontFamily: 'inherit',
                opacity: isGraceTyping ? 0.6 : 1,
              }}
            >
              Prepare for exam
            </button>
          </section>
        </>
      )}

      {/* Generated content */}
      {(cheatsheets.length > 0 || studyGuide || tests.length > 0) && (
        <>
          <div style={{ margin: '2px 14px', borderTop: '1px solid #F0EBE4' }} />
          <section style={{ padding: '12px 14px 16px' }}>
            <span style={{
              fontSize: 10, fontWeight: 700, color: '#BBBBBB',
              textTransform: 'uppercase', letterSpacing: '0.1em',
              display: 'block', marginBottom: 8,
            }}>
              {t.resGenerated}
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {cheatsheets.map(cs => (
                <ActionRow
                  key={cs.id}
                  icon={<CheatsheetIcon />}
                  label={cs.title}
                  onClick={() => { setViewingCS(cs); setView('cheatsheet'); setLayoutMode('cowork'); }}
                />
              ))}
              {tests.map(te => (
                <ActionRow
                  key={te.id}
                  icon={<TestIcon />}
                  label={te.title}
                  onClick={() => { setActiveTest(te.session); setActivePanel('test'); setLayoutMode('cowork'); }}
                />
              ))}
              {studyGuide && (
                <ActionRow
                  icon={<GuideIcon />}
                  label={t.resStudyGuide}
                  onClick={() => setView('guide')}
                />
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function PanelHeader({ title, onBack, onCopy }: { title: string; onBack: () => void; onCopy?: () => void }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '14px 16px', borderBottom: '1px solid #F0EBE4', flexShrink: 0,
    }}>
      <button
        onClick={onBack}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: 26, height: 26, borderRadius: 6, border: '1px solid #DEDAD4',
          backgroundColor: 'transparent', cursor: 'pointer', color: '#888', flexShrink: 0,
        }}
      >
        <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="8 2 4 6 8 10" />
        </svg>
      </button>
      <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', letterSpacing: '-0.01em', flex: 1 }}>
        {title}
      </span>
      {onCopy && (
        <button
          onClick={onCopy}
          title="Copy to clipboard"
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: 26, height: 26, borderRadius: 6, border: '1px solid #DEDAD4',
            backgroundColor: 'transparent', cursor: 'pointer', color: '#888', flexShrink: 0,
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      )}
    </div>
  );
}

// ── Cheatsheet ReactMarkdown component map ─────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const csComponents: Record<string, React.ComponentType<any>> = {
  h1: ({ children }: { children: React.ReactNode }) => (
    <h1 style={{ fontSize: 17, fontWeight: 700, color: '#111', margin: '0 0 14px', letterSpacing: '-0.02em', lineHeight: 1.3 }}>{children}</h1>
  ),
  h2: ({ children }: { children: React.ReactNode }) => (
    <h2 style={{ fontSize: 12, fontWeight: 700, color: '#999', margin: '22px 0 8px', textTransform: 'uppercase', letterSpacing: '0.07em' }}>{children}</h2>
  ),
  h3: ({ children }: { children: React.ReactNode }) => (
    <h3 style={{ fontSize: 13.5, fontWeight: 600, color: '#333', margin: '14px 0 4px' }}>{children}</h3>
  ),
  p: ({ children }: { children: React.ReactNode }) => (
    <p style={{ margin: '0 0 10px', fontSize: 13.5, lineHeight: 1.75, color: '#1a1a1a' }}>{children}</p>
  ),
  ul: ({ children }: { children: React.ReactNode }) => (
    <ul style={{ margin: '0 0 10px', paddingLeft: 0, listStyle: 'none' }}>{children}</ul>
  ),
  ol: ({ children }: { children: React.ReactNode }) => (
    <ol style={{ margin: '0 0 10px', paddingLeft: 20, lineHeight: 1.75, fontSize: 13.5 }}>{children}</ol>
  ),
  li: ({ children }: { children: React.ReactNode }) => (
    <li style={{ display: 'flex', gap: 8, margin: '3px 0', fontSize: 13.5, lineHeight: 1.75, color: '#1a1a1a' }}>
      <span style={{ color: '#E8C84B', fontWeight: 700, flexShrink: 0, marginTop: 2 }}>•</span>
      <span>{children}</span>
    </li>
  ),
  strong: ({ children }: { children: React.ReactNode }) => (
    <strong style={{ fontWeight: 700, color: '#111' }}>{children}</strong>
  ),
  em: ({ children }: { children: React.ReactNode }) => (
    <em style={{ fontStyle: 'italic', color: '#555' }}>{children}</em>
  ),
  hr: () => (
    <hr style={{ border: 'none', borderTop: '1px solid #EEE8E0', margin: '18px 0' }} />
  ),
  blockquote: ({ children }: { children: React.ReactNode }) => (
    <blockquote style={{ borderLeft: '3px solid #E8C84B', paddingLeft: 12, margin: '0 0 10px', color: '#555', fontStyle: 'italic' }}>{children}</blockquote>
  ),
  code: ({ inline, children }: { inline?: boolean; children: React.ReactNode }) =>
    inline
      ? <code style={{ backgroundColor: '#F5F0E8', borderRadius: 4, padding: '1px 5px', fontSize: 12.5, fontFamily: 'ui-monospace, monospace', color: '#333' }}>{children}</code>
      : <pre style={{ backgroundColor: '#F5F0E8', borderRadius: 8, padding: '10px 14px', overflowX: 'auto', margin: '0 0 12px', fontSize: 12.5, lineHeight: 1.6, fontFamily: 'ui-monospace, monospace' }}><code>{children}</code></pre>,
  table: ({ children }: { children: React.ReactNode }) => (
    <div style={{ overflowX: 'auto', margin: '0 0 14px' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 13, lineHeight: 1.6 }}>{children}</table>
    </div>
  ),
  thead: ({ children }: { children: React.ReactNode }) => (
    <thead style={{ backgroundColor: '#F5F0E8' }}>{children}</thead>
  ),
  th: ({ children }: { children: React.ReactNode }) => (
    <th style={{ padding: '7px 12px', textAlign: 'left', fontWeight: 700, fontSize: 12, color: '#555', borderBottom: '2px solid #E8E0D5', whiteSpace: 'nowrap' }}>{children}</th>
  ),
  td: ({ children }: { children: React.ReactNode }) => (
    <td style={{ padding: '6px 12px', borderBottom: '1px solid #EEE8E0', verticalAlign: 'top', color: '#222' }}>{children}</td>
  ),
};

function ActionRow({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="hover:bg-amber-50"
      style={{
        display: 'flex', alignItems: 'center', gap: 9, padding: '7px 8px',
        borderRadius: 7, border: 'none', backgroundColor: 'transparent',
        cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left', width: '100%',
        transition: 'background-color 0.1s',
      }}
    >
      <span style={{ color: '#AAA', flexShrink: 0, display: 'flex' }}>{icon}</span>
      <span style={{ fontSize: 13, color: '#333', flex: 1 }}>{label}</span>
      <svg style={{ flexShrink: 0 }} width="10" height="10" viewBox="0 0 12 12" fill="none"
        stroke="#CCCCCC" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="4 2 8 6 4 10" />
      </svg>
    </button>
  );
}

function CheatsheetIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
    </svg>
  );
}

function GuideIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
    </svg>
  );
}

function TestIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
      <polyline points="10 9 9 9 8 9"/>
    </svg>
  );
}
