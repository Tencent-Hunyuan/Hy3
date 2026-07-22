import { useEffect, useRef, useState } from 'react';
import GraceAvatar from './GraceAvatar';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { PROVIDER_CONFIGS } from '../../types';
import type { LLMProvider } from '../../types';

export default function Onboarding() {
  const {
    onboardingStep, setOnboardingStep,
    setOnboardingComplete,
    setUserName,
    loadLLMSettings, saveLLMSettings,
  } = useStore();

  const [name, setName] = useState('');
  const nameRef = useRef<HTMLInputElement>(null);

  const [selectedProvider, setSelectedProvider] = useState<LLMProvider>('openrouter');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [selectedModel, setSelectedModel] = useState('anthropic/claude-sonnet-4-5');
  const [testState, setTestState] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle');
  const [testError, setTestError] = useState('');
  const apiKeyRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.settings.load().then((s) => {
      if (s.apiKey) { setApiKey(s.apiKey); setTestState('ok'); }
      setSelectedModel(s.model);
      setSelectedProvider((s.provider ?? 'openrouter') as LLMProvider);
      loadLLMSettings(s);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (onboardingStep === 1) setTimeout(() => nameRef.current?.focus(), 60);
    if (onboardingStep === 2) setTimeout(() => apiKeyRef.current?.focus(), 60);
  }, [onboardingStep]);

  const providerCfg = PROVIDER_CONFIGS.find(p => p.id === selectedProvider)!;

  function handleProviderChange(p: LLMProvider) {
    setSelectedProvider(p);
    const cfg = PROVIDER_CONFIGS.find(c => c.id === p);
    if (cfg) setSelectedModel(cfg.models[0].id);
    setTestState('idle');
    setTestError('');
  }

  async function handleTestConnection() {
    if (!apiKey.trim()) return;
    setTestState('testing');
    setTestError('');
    try {
      const result = await api.settings.testConnection({
        apiKey: apiKey.trim(), model: selectedModel,
        temperature: 0.7, provider: selectedProvider,
      });
      if (result.ok) { setTestState('ok'); }
      else { setTestState('error'); setTestError(result.error ?? 'Connection failed'); }
    } catch (err) {
      setTestState('error');
      setTestError(err instanceof Error ? err.message : 'Network error');
    }
  }

  async function handleLLMContinue() {
    const displayName = name.trim() || 'there';
    setUserName(displayName);

    if (apiKey.trim()) {
      const localSettings = { apiKey: apiKey.trim(), model: selectedModel, temperature: 0.7, provider: selectedProvider };
      saveLLMSettings(localSettings);
      api.settings.save(localSettings).then((saved) => saveLLMSettings(saved)).catch((err) => {
        console.error('[Onboarding] settings save failed:', err);
      });
    }

    try {
      await api.config.save({ onboardingComplete: true, userName: displayName, subjects: [], activeSubjectId: null });
    } catch (err) {
      console.error('[Onboarding] config save failed:', err);
    }

    setOnboardingComplete(true);
  }

  const step = onboardingStep;

  // ── Step 0: Full-page welcome ────────────────────────────────────────────────
  if (step === 0) {
    return (
      <div style={{ position: 'fixed', inset: 0, display: 'flex', fontFamily: 'inherit' }}>

        {/* ── Left: dark brand panel ───────────────────────────────────────── */}
        <div style={{
          flex: '0 0 44%',
          backgroundColor: '#100F0A',
          display: 'flex',
          flexDirection: 'column',
          padding: '36px 44px 44px',
          position: 'relative',
          overflow: 'hidden',
        }}>
          {/* Logo + badge */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: '#FAF7F0', letterSpacing: '-0.025em' }}>
              isGrace
            </span>
            <span style={{
              fontSize: 10, fontWeight: 600, color: '#5A5030',
              border: '1px solid #252318', borderRadius: 4,
              padding: '3px 9px', letterSpacing: '0.09em', textTransform: 'uppercase',
            }}>
              Open Source
            </span>
          </div>

          {/* Grace — centered with warm glow */}
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
            <div style={{
              position: 'absolute',
              width: 340, height: 340, borderRadius: '50%',
              background: 'radial-gradient(circle, rgba(244,211,94,0.10) 0%, transparent 65%)',
              pointerEvents: 'none',
            }} />
            <img
              src="/assets/grace-avatar-nobg.svg"
              alt="Grace"
              draggable={false}
              style={{ height: 340, width: 'auto', userSelect: 'none', position: 'relative', zIndex: 1 }}
            />
          </div>

          {/* Right-edge gradient — softens the seam */}
          <div style={{
            position: 'absolute', top: 0, right: 0,
            width: 100, height: '100%',
            background: 'linear-gradient(to right, transparent, #100F0A)',
            pointerEvents: 'none', zIndex: 2,
          }} />

          {/* Bottom tagline */}
          <div>
            <h1 style={{
              fontSize: 27, fontWeight: 700, color: '#FAF7F0',
              letterSpacing: '-0.03em', lineHeight: 1.25, margin: '0 0 10px',
            }}>
              Turn reading<br />into knowing.
            </h1>
            <p style={{ fontSize: 12, color: '#3E3820', margin: 0, letterSpacing: '0.02em' }}>
              Free · Open Source · Bring your own key
            </p>
          </div>
        </div>

        {/* ── Right: value-prop panel ──────────────────────────────────────── */}
        <div style={{
          flex: 1,
          backgroundColor: '#FAFAF7',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 72px',
          overflowY: 'auto',
        }}>
          <div style={{ maxWidth: 440 }}>
            <p style={{
              fontSize: 11, fontWeight: 700, letterSpacing: '0.1em',
              color: '#C8A820', textTransform: 'uppercase', margin: '0 0 18px',
            }}>
              Your AI Study Partner
            </p>

            <h2 style={{
              fontSize: 36, fontWeight: 700, letterSpacing: '-0.03em',
              color: '#111', lineHeight: 1.18, margin: '0 0 18px',
            }}>
              AI knowing it<br />isn't you knowing it.
            </h2>

            <p style={{ fontSize: 15, color: '#888', lineHeight: 1.72, margin: '0 0 40px' }}>
              In the AI age, content is everywhere. The real bottleneck is the gap between
              consuming information and actually owning it. isGrace closes that gap — through
              structured passes, active output, and memory that persists.
            </p>

            {/* Feature list */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 22, marginBottom: 48 }}>
              {[
                {
                  title: 'Structured learning, not passive scrolling',
                  desc: 'Beginner Pass builds intuition. Intermediate Pass goes deep. Then you\'re tested on exactly what the material covers.',
                },
                {
                  title: 'You produce the output — AI doesn\'t',
                  desc: 'Interactive tests make you construct answers. Passive reading tricks you into thinking you\'ve learned. Active recall doesn\'t.',
                },
                {
                  title: 'Study materials always persist',
                  desc: 'Cheatsheets, summaries, and chat history are saved per subject. Re-open any session and pick up exactly where you left off.',
                },
                {
                  title: 'Any model, your key, always free',
                  desc: 'Claude, GPT-4o, Gemini, DeepSeek, Qwen. Open source. No subscription, no lock-in.',
                },
                {
                  title: 'Your data never leaves your device',
                  desc: 'Everything — your materials, notes, and chat history — is stored locally. Nothing is uploaded to isGrace\'s servers. Ever.',
                },
              ].map((f) => (
                <div key={f.title} style={{ display: 'flex', gap: 16 }}>
                  <span style={{
                    color: '#C8A820', fontSize: 8, marginTop: 5, flexShrink: 0,
                  }}>◆</span>
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a', margin: '0 0 3px' }}>
                      {f.title}
                    </p>
                    <p style={{ fontSize: 13, color: '#AAA', lineHeight: 1.55, margin: 0 }}>
                      {f.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={() => setOnboardingStep(1)}
              style={{
                padding: '15px 40px', borderRadius: 12,
                backgroundColor: '#F4D35E', border: 'none',
                fontSize: 15, fontWeight: 600, color: '#1a1a1a',
                cursor: 'pointer', fontFamily: 'inherit', letterSpacing: '-0.01em',
                transition: 'opacity 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
              onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
            >
              Get Started →
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Steps 1 & 2: centered card ────────────────────────────────────────────────
  return (
    <div className="fixed inset-0 flex items-center justify-center" style={{ backgroundColor: '#FAFAF7' }}>
      <div style={{ width: '100%', maxWidth: 420, padding: '0 36px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>

        <div style={{ marginBottom: 18 }}>
          <GraceAvatar size="md" />
        </div>

        {/* ── Step 1: Name ───────────────────────────────────────────────────── */}
        {step === 1 && (
          <div style={col(18, '100%')}>
            <StepHeader n={1} total={2} title="What should Grace call you?" sub="Just a first name is fine." />
            <input
              ref={nameRef}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && name.trim()) setOnboardingStep(2); }}
              placeholder="e.g. Alex"
              style={textInput}
            />
            <BtnRow>
              <Btn onClick={() => setOnboardingStep(0)}>← Back</Btn>
              <Btn primary onClick={() => setOnboardingStep(2)} disabled={!name.trim()}>
                Continue →
              </Btn>
            </BtnRow>
          </div>
        )}

        {/* ── Step 2: Connect LLM ────────────────────────────────────────────── */}
        {step === 2 && (
          <div style={col(14, '100%')}>
            <StepHeader n={2} total={2} title="Connect your AI model" sub="Choose a provider and enter your API key." />

            <div style={col(5, '100%')}>
              <SectionLabel>API Type</SectionLabel>
              <DropdownSelect
                value={selectedProvider}
                onChange={(v) => handleProviderChange(v as LLMProvider)}
                options={PROVIDER_CONFIGS.map(p => ({ value: p.id, label: p.label }))}
              />
            </div>

            <a
              href={providerCfg.docsURL}
              target="_blank"
              rel="noreferrer"
              style={{ display: 'block', padding: '9px 13px', borderRadius: 9, backgroundColor: '#F6F3EE', fontSize: 13, color: '#666', textDecoration: 'none', lineHeight: 1.5 }}
            >
              Don't have a key?{' '}
              <span style={{ color: '#1a1a1a', fontWeight: 600, textDecoration: 'underline' }}>
                Get one at {providerCfg.docsLabel} →
              </span>
            </a>

            <div style={col(6, '100%')}>
              <SectionLabel>API Key</SectionLabel>
              <div style={{ position: 'relative' }}>
                <input
                  ref={apiKeyRef}
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => { setApiKey(e.target.value); setTestState('idle'); }}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleTestConnection(); }}
                  placeholder={providerCfg.placeholder}
                  style={{
                    width: '100%', padding: '11px 40px 11px 13px', borderRadius: 9,
                    border: `1.5px solid ${testState === 'ok' ? '#86efac' : testState === 'error' ? '#fca5a5' : '#DEDAD4'}`,
                    backgroundColor: '#F6F3EE', fontSize: 14, color: '#1a1a1a', outline: 'none',
                    fontFamily: 'ui-monospace, monospace', letterSpacing: '0.02em',
                    boxSizing: 'border-box', transition: 'border-color 0.15s',
                  }}
                />
                <button onClick={() => setShowKey(v => !v)} style={iconBtn}>
                  {showKey
                    ? <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                    : <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  }
                </button>
              </div>
              {testState === 'ok'    && <p style={{ fontSize: 12, color: '#16a34a', margin: 0 }}>✓ Connected successfully</p>}
              {testState === 'error' && <p style={{ fontSize: 12, color: '#dc2626', margin: 0 }}>✗ {testError}</p>}
              <button
                onClick={handleTestConnection}
                disabled={testState === 'testing' || !apiKey.trim()}
                style={{ alignSelf: 'flex-start', fontSize: 13, padding: '7px 14px', borderRadius: 7, border: '1.5px solid #DEDAD4', backgroundColor: 'transparent', color: '#555', cursor: 'pointer', fontFamily: 'inherit', opacity: !apiKey.trim() ? 0.4 : 1 }}
              >
                {testState === 'testing' ? 'Testing…' : 'Test Connection'}
              </button>
            </div>

            <div style={col(5, '100%')}>
              <SectionLabel>Model</SectionLabel>
              <DropdownSelect
                value={selectedModel}
                onChange={setSelectedModel}
                options={providerCfg.models.map(m => ({ value: m.id, label: m.label, description: m.description, ctxLabel: m.ctxLabel }))}
              />
              <p style={{ fontSize: 12, color: '#AAAAAA', margin: 0, lineHeight: 1.5 }}>
                💡 For large textbooks, use Claude (200k) or Gemini (1M+) — they handle long materials without cutting off.
              </p>
            </div>

            <BtnRow>
              <Btn onClick={() => setOnboardingStep(1)}>← Back</Btn>
              <Btn primary onClick={handleLLMContinue}>
                {testState === 'error' && apiKey.trim()
                  ? '⚠️ Continue anyway →'
                  : apiKey.trim() ? `Start Learning, ${name.trim() || 'there'} →` : 'Skip for now'}
              </Btn>
            </BtnRow>
          </div>
        )}

        {/* Progress dots */}
        <div style={{ display: 'flex', gap: 6, marginTop: 22 }}>
          {[1, 2].map((s) => (
            <div key={s} style={{
              width: s === step ? 20 : 6, height: 6, borderRadius: 999,
              backgroundColor: s <= step ? '#F4D35E' : '#E0DBD4',
              transition: 'all 0.25s ease',
            }} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Design tokens ──────────────────────────────────────────────────────────────

const textInput: React.CSSProperties = {
  width: '100%', padding: '13px 14px', borderRadius: 9,
  border: '1.5px solid #DEDAD4', backgroundColor: '#F6F3EE',
  fontSize: 16, color: '#1a1a1a', outline: 'none',
  letterSpacing: '-0.005em', boxSizing: 'border-box', fontFamily: 'inherit',
};
const iconBtn: React.CSSProperties = {
  position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
  background: 'none', border: 'none', cursor: 'pointer', color: '#AAA', padding: 2, display: 'flex',
};

function col(gap: number, width: string): React.CSSProperties {
  return { display: 'flex', flexDirection: 'column', gap, width };
}

// ── Dropdown ───────────────────────────────────────────────────────────────────

interface DropOption { value: string; label: string; description?: string; ctxLabel?: string; }

function DropdownSelect({ value, onChange, options }: {
  value: string; onChange: (v: string) => void; options: DropOption[];
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  const sel = options.find(o => o.value === value);

  return (
    <div ref={ref} style={{ position: 'relative', width: '100%' }}>
      <button onClick={() => setOpen(v => !v)} style={{
        width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '10px 12px', borderRadius: 9,
        border: `1.5px solid ${open ? '#C8BE50' : '#DEDAD4'}`,
        backgroundColor: open ? '#FEFBE8' : '#F6F3EE',
        cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
        transition: 'border-color 0.12s, background-color 0.12s',
      }}>
        <span style={{ fontSize: 14, color: '#1a1a1a', display: 'flex', alignItems: 'center', gap: 6 }}>
          {sel?.label ?? '—'}
          {sel?.ctxLabel && <span style={{ fontSize: 10, fontWeight: 600, color: '#7A9A6A', backgroundColor: '#EDF5E8', borderRadius: 4, padding: '2px 5px' }}>{sel.ctxLabel}</span>}
          {sel?.description && <span style={{ fontSize: 12, color: '#999' }}>{sel.description}</span>}
        </span>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="#888" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s', flexShrink: 0, marginLeft: 8 }}>
          <polyline points="2 4 6 8 10 4" />
        </svg>
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 200,
          borderRadius: 9, border: '1.5px solid #DEDAD4', backgroundColor: '#FEFEFE',
          boxShadow: '0 6px 20px rgba(0,0,0,0.09)', overflow: 'hidden',
        }}>
          {options.map((opt, i) => (
            <button key={opt.value} onClick={() => { onChange(opt.value); setOpen(false); }} style={{
              width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '10px 12px', border: 'none',
              borderBottom: i < options.length - 1 ? '1px solid #F0EBE4' : 'none',
              backgroundColor: opt.value === value ? '#FEFBE8' : 'transparent',
              cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
            }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 14, fontWeight: opt.value === value ? 500 : 400, color: '#1a1a1a' }}>{opt.label}</span>
                {opt.ctxLabel && <span style={{ fontSize: 10, fontWeight: 600, color: '#7A9A6A', backgroundColor: '#EDF5E8', borderRadius: 4, padding: '2px 5px' }}>{opt.ctxLabel}</span>}
                {opt.description && <span style={{ fontSize: 12, color: '#999' }}>{opt.description}</span>}
              </span>
              {opt.value === value && (
                <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
                  <path d="M1 5L4.5 8.5L11 1" stroke="#1a1a1a" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StepHeader({ n, total, title, sub }: { n: number; total: number; title: string; sub?: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#BBBBBB', margin: '0 0 8px' }}>
        Step {n} of {total}
      </p>
      <h2 style={{ fontSize: 21, fontWeight: 600, letterSpacing: '-0.02em', color: '#111', lineHeight: 1.3, margin: 0 }}>{title}</h2>
      {sub && <p style={{ fontSize: 14, color: '#888', lineHeight: 1.6, margin: '6px 0 0' }}>{sub}</p>}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.07em', textTransform: 'uppercase', color: '#AAAAAA', margin: 0 }}>{children}</p>;
}

function Btn({ children, primary, onClick, disabled, style }: {
  children: React.ReactNode; primary?: boolean; onClick?: () => void; disabled?: boolean; style?: React.CSSProperties;
}) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      flex: 1, padding: '13px 20px', borderRadius: 10,
      border: primary ? 'none' : '1.5px solid #DEDAD4',
      backgroundColor: primary ? '#F4D35E' : 'transparent',
      fontSize: 15, fontWeight: primary ? 600 : 400,
      color: primary ? '#1a1a1a' : '#666',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.38 : 1,
      transition: 'opacity 0.15s', fontFamily: 'inherit', letterSpacing: primary ? '-0.01em' : '0',
      ...style,
    }}>{children}</button>
  );
}

function BtnRow({ children }: { children: React.ReactNode }) {
  return <div style={{ display: 'flex', gap: 10, width: '100%' }}>{children}</div>;
}
