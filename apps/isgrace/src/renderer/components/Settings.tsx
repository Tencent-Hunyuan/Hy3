import { useEffect, useRef, useState } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import type { LLMSettings, LLMProvider } from '../../types';
import { PROVIDER_CONFIGS } from '../../types';
import { useLang } from '../i18n/useLang';

export default function Settings() {
  const {
    llmSettings, saveLLMSettings, setSettingsOpen, uiLanguage, setUiLanguage, setOnboardingComplete, setOnboardingStep,
    settingsMode, hasDefaultKey, localKeyOverride, setLocalKeyOverride,
  } = useStore();
  const { t } = useLang();
  const hosted = settingsMode === 'hosted';

  const [useOwnKey, setUseOwnKey] = useState(hosted ? localKeyOverride !== null : true);
  const initial = hosted ? (localKeyOverride ?? { apiKey: '', model: PROVIDER_CONFIGS[0].models[0].id, temperature: 0.7, provider: 'openrouter' as LLMProvider }) : llmSettings;

  const [provider, setProvider] = useState<LLMProvider>(initial.provider ?? 'openrouter');
  const [apiKey, setApiKey]     = useState(initial.apiKey);
  const [model, setModel]       = useState(initial.model);
  const [temp, setTemp]         = useState(initial.temperature);
  const [showKey, setShowKey]   = useState(false);
  const [testing, setTesting]   = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [saving, setSaving]     = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (useOwnKey) inputRef.current?.focus(); }, [useOwnKey]);

  const providerCfg = PROVIDER_CONFIGS.find(p => p.id === provider)!;

  function handleProviderChange(p: LLMProvider) {
    setProvider(p);
    const cfg = PROVIDER_CONFIGS.find(c => c.id === p)!;
    setModel(cfg.models[0].id);
    setTestResult(null);
  }

  async function handleTest() {
    if (!apiKey.trim()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const testSettings: LLMSettings = { apiKey: apiKey.trim(), model, temperature: temp, provider };
      const result = await api.settings.testConnection(testSettings);
      setTestResult({ ok: result.ok, msg: result.ok ? t.settingsConnected : (result.error ?? 'Unknown error') });
    } catch (err) {
      setTestResult({ ok: false, msg: err instanceof Error ? err.message : 'Network error' });
    } finally {
      setTesting(false);
    }
  }

  async function handleSave() {
    if (hosted) {
      setLocalKeyOverride({ apiKey: apiKey.trim(), model, temperature: temp, provider });
      setSettingsOpen(false);
      return;
    }
    setSaving(true);
    try {
      // Update store immediately so llmReady=true for this session
      saveLLMSettings({ apiKey: apiKey.trim(), model, temperature: temp, provider });
      const saved = await api.settings.save({ apiKey: apiKey.trim(), model, temperature: temp, provider });
      saveLLMSettings(saved);
      setSettingsOpen(false);
    } catch (err) {
      console.error('[Settings] save failed:', err);
      setTestResult({ ok: false, msg: 'Save failed — check console for details' });
    } finally {
      setSaving(false);
    }
  }

  function handleRevertToDefault() {
    setLocalKeyOverride(null);
    setUseOwnKey(false);
    setApiKey('');
    setTestResult(null);
  }

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-end"
      style={{ backgroundColor: 'rgba(0,0,0,0.18)' }}
      onClick={(e) => { if (e.target === e.currentTarget) setSettingsOpen(false); }}
    >
      {/* Panel */}
      <div
        className="h-full flex flex-col"
        style={{ width: 380, backgroundColor: '#FEFEFE', borderLeft: '1px solid #E8E0D5', overflowY: 'auto' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-8 pb-6" style={{ borderBottom: '1px solid #F0EBE4' }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 600, letterSpacing: '-0.02em', color: '#111', margin: 0 }}>{t.settingsTitle}</h2>
            <p style={{ fontSize: 13, color: '#888', marginTop: 3 }}>{t.settingsSubtitle}</p>
          </div>
          <button
            onClick={() => setSettingsOpen(false)}
            style={{ width: 28, height: 28, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999', cursor: 'pointer', border: '1px solid #E8E0D5', backgroundColor: 'transparent', fontFamily: 'inherit' }}
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <line x1="1" y1="1" x2="11" y2="11"/><line x1="11" y1="1" x2="1" y2="11"/>
            </svg>
          </button>
        </div>

        <div className="flex flex-col gap-6 px-6 py-6" style={{ flex: 1 }}>

          {/* ── App Language ────────────────────────────────────────────────── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Label>{t.settingsLanguage}</Label>
            <div style={{ display: 'flex', gap: 8 }}>
              {(['en', 'zh'] as const).map((lang) => (
                <button
                  key={lang}
                  onClick={() => setUiLanguage(lang)}
                  style={{
                    flex: 1, padding: '9px 0', borderRadius: 9, fontFamily: 'inherit',
                    fontSize: 13, fontWeight: 500, cursor: 'pointer',
                    border: `1.5px solid ${uiLanguage === lang ? '#1a1a1a' : '#DEDAD4'}`,
                    backgroundColor: uiLanguage === lang ? '#1a1a1a' : '#F6F3EE',
                    color: uiLanguage === lang ? '#FEFEFE' : '#555',
                    transition: 'all 0.15s',
                  }}
                >
                  {lang === 'en' ? 'English' : '简体中文'}
                </button>
              ))}
            </div>
          </div>

          {/* ── Hosted mode: site default banner ───────────────────────────── */}
          {hosted && (
            <div style={{
              backgroundColor: hasDefaultKey ? '#FEFBE8' : '#FEF2F2',
              border: `1.5px solid ${hasDefaultKey ? '#F4D35E' : '#FCA5A5'}`,
              borderRadius: 10, padding: '12px 14px',
            }}>
              <p style={{ margin: '0 0 8px', fontSize: 13, color: '#1a1a1a', lineHeight: 1.5 }}>
                {hasDefaultKey
                  ? <>Site default: <strong>Tencent Hy3</strong> (OpenRouter) — shared, no key needed to start chatting.</>
                  : <>No site default key is configured — you'll need to enter your own key below to use the app.</>}
              </p>
              {!useOwnKey && hasDefaultKey && (
                <button
                  onClick={() => setUseOwnKey(true)}
                  style={{ fontSize: 12.5, color: '#1a1a1a', border: '1.5px solid #DEDAD4', borderRadius: 7, padding: '6px 12px', cursor: 'pointer', backgroundColor: 'transparent', fontFamily: 'inherit', fontWeight: 500 }}
                >
                  Use my own key instead
                </button>
              )}
              {useOwnKey && localKeyOverride && (
                <button
                  onClick={handleRevertToDefault}
                  style={{ fontSize: 12.5, color: '#888', border: '1.5px solid #DEDAD4', borderRadius: 7, padding: '6px 12px', cursor: 'pointer', backgroundColor: 'transparent', fontFamily: 'inherit' }}
                >
                  Revert to site default
                </button>
              )}
            </div>
          )}

          {(!hosted || useOwnKey) && (
          <>
          {/* ── API Type ────────────────────────────────────────────────────── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Label>{t.settingsApiType}</Label>
            <DropdownSelect
              value={provider}
              onChange={(v) => handleProviderChange(v as LLMProvider)}
              options={PROVIDER_CONFIGS.map(p => ({ value: p.id, label: p.label }))}
            />
          </div>

          {/* ── Docs link (provider-specific) ──────────────────────────────── */}
          <div style={{ backgroundColor: '#F6F3EE', borderRadius: 10, padding: '11px 13px', fontSize: 13, color: '#666', lineHeight: 1.6 }}>
            {t.settingsGetKey}{' '}
            <a
              href={providerCfg.docsURL}
              target="_blank"
              rel="noreferrer"
              style={{ color: '#1a1a1a', fontWeight: 500, textDecoration: 'underline' }}
            >
              {providerCfg.docsLabel}
            </a>.
          </div>

          {/* ── API Key ─────────────────────────────────────────────────────── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Label>{t.settingsApiKey}</Label>
            <div style={{ position: 'relative' }}>
              <input
                ref={inputRef}
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => { setApiKey(e.target.value); setTestResult(null); }}
                placeholder={providerCfg.placeholder}
                style={{
                  width: '100%', padding: '11px 40px 11px 13px', borderRadius: 9,
                  border: '1.5px solid #DEDAD4', backgroundColor: '#F6F3EE',
                  fontSize: 14, color: '#1a1a1a', outline: 'none',
                  fontFamily: 'ui-monospace, monospace', letterSpacing: '0.02em',
                  boxSizing: 'border-box',
                }}
              />
              <button
                onClick={() => setShowKey(v => !v)}
                style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', color: '#AAA', background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}
                title={showKey ? 'Hide' : 'Show'}
              >
                {showKey
                  ? <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                  : <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                }
              </button>
            </div>

            {testResult && (
              <p style={{ fontSize: 12, color: testResult.ok ? '#16a34a' : '#dc2626', marginTop: 2 }}>
                {testResult.msg}
              </p>
            )}

            <button
              onClick={handleTest}
              disabled={testing || !apiKey.trim()}
              style={{ alignSelf: 'flex-start', fontSize: 13, color: testing ? '#AAA' : '#1a1a1a', border: '1.5px solid #DEDAD4', borderRadius: 7, padding: '7px 14px', cursor: testing ? 'wait' : 'pointer', backgroundColor: 'transparent', fontFamily: 'inherit', opacity: !apiKey.trim() ? 0.4 : 1 }}
            >
              {testing ? t.settingsTesting : t.settingsTestConn}
            </button>
          </div>

          {/* ── Model ───────────────────────────────────────────────────────── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Label>{t.settingsModel}</Label>
            <DropdownSelect
              value={model}
              onChange={setModel}
              options={providerCfg.models.map(m => ({
                value: m.id,
                label: m.label,
                description: m.description,
                badge: m.fast ? 'fast' : undefined,
                ctxLabel: m.ctxLabel,
              }))}
            />
            <p style={{ fontSize: 12, color: '#AAAAAA', margin: 0, lineHeight: 1.5 }}>
              💡 For large textbooks, use a model with a big context window — Claude (200k) or Gemini (1M+) recommended.
            </p>
          </div>

          {/* ── Temperature ─────────────────────────────────────────────────── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <Label>{t.settingsTemp}</Label>
              <span style={{ fontSize: 13, color: '#666', fontVariantNumeric: 'tabular-nums' }}>{temp.toFixed(1)}</span>
            </div>
            <input
              type="range" min={0} max={1} step={0.1}
              value={temp}
              onChange={(e) => setTemp(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: '#F4D35E' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#AAA' }}>
              <span>{t.settingsTempPrecise}</span><span>{t.settingsTempBalanced}</span><span>{t.settingsTempCreative}</span>
            </div>
          </div>
          </>
          )}
        </div>

        {/* Save */}
        <div style={{ padding: '16px 24px 12px', borderTop: '1px solid #F0EBE4', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {(!hosted || useOwnKey) && (
          <button
            onClick={handleSave}
            disabled={saving || !apiKey.trim()}
            style={{
              width: '100%', padding: '13px', borderRadius: 10,
              backgroundColor: '#F4D35E', border: 'none',
              fontSize: 15, fontWeight: 600, color: '#1a1a1a',
              cursor: saving || !apiKey.trim() ? 'not-allowed' : 'pointer',
              opacity: !apiKey.trim() ? 0.5 : 1,
              fontFamily: 'inherit', letterSpacing: '-0.01em',
            }}
          >
            {saving ? t.settingsSaving : t.settingsSave}
          </button>
          )}
          <button
            onClick={() => { setOnboardingStep(0); setOnboardingComplete(false); setSettingsOpen(false); }}
            style={{
              width: '100%', padding: '9px', borderRadius: 10,
              backgroundColor: 'transparent', border: '1.5px solid #DEDAD4',
              fontSize: 13, color: '#AAAAAA',
              cursor: 'pointer', fontFamily: 'inherit',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#BBBBBB'; e.currentTarget.style.color = '#666'; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#DEDAD4'; e.currentTarget.style.color = '#AAAAAA'; }}
          >
            Preview Onboarding
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Dropdown Select ────────────────────────────────────────────────────────────

interface DropOption { value: string; label: string; description?: string; badge?: string; ctxLabel?: string; }

function DropdownSelect({ value, onChange, options }: {
  value: string;
  onChange: (v: string) => void;
  options: DropOption[];
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const selected = options.find(o => o.value === value);

  return (
    <div ref={ref} style={{ position: 'relative', width: '100%' }}>
      {/* Trigger */}
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '10px 12px', borderRadius: 9,
          border: `1.5px solid ${open ? '#C8BE50' : '#DEDAD4'}`,
          backgroundColor: open ? '#FEFBE8' : '#F6F3EE',
          cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
          transition: 'border-color 0.12s, background-color 0.12s',
        }}
      >
        <span style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 13, fontWeight: 500, color: '#1a1a1a' }}>{selected?.label ?? '—'}</span>
          {selected?.ctxLabel && (
            <span style={{ fontSize: 10, fontWeight: 600, color: '#7A9A6A', backgroundColor: '#EDF5E8', borderRadius: 4, padding: '2px 5px', letterSpacing: '0.03em', flexShrink: 0 }}>
              {selected.ctxLabel}
            </span>
          )}
          {selected?.description && (
            <span style={{ fontSize: 12, color: '#888' }}>{selected.description}</span>
          )}
        </span>
        <svg
          width="12" height="12" viewBox="0 0 12 12" fill="none"
          stroke="#888" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s', flexShrink: 0, marginLeft: 8 }}
        >
          <polyline points="2 4 6 8 10 4" />
        </svg>
      </button>

      {/* Dropdown list */}
      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 200,
          borderRadius: 9, border: '1.5px solid #DEDAD4',
          backgroundColor: '#FEFEFE',
          boxShadow: '0 6px 20px rgba(0,0,0,0.09)',
          overflow: 'hidden',
          maxHeight: 260, overflowY: 'auto',
        }}>
          {options.map((opt, i) => (
            <button
              key={opt.value}
              onClick={() => { onChange(opt.value); setOpen(false); }}
              style={{
                width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '10px 12px', border: 'none',
                borderBottom: i < options.length - 1 ? '1px solid #F0EBE4' : 'none',
                backgroundColor: opt.value === value ? '#FEFBE8' : 'transparent',
                cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
              }}
            >
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: 13, fontWeight: opt.value === value ? 500 : 400, color: '#1a1a1a' }}>
                  {opt.label}
                </span>
                {opt.description && (
                  <span style={{ fontSize: 12, color: '#999', marginLeft: 8 }}>{opt.description}</span>
                )}
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0 }}>
                {opt.ctxLabel && (
                  <span style={{ fontSize: 10, fontWeight: 600, color: '#7A9A6A', backgroundColor: '#EDF5E8', borderRadius: 4, padding: '2px 5px', letterSpacing: '0.03em' }}>
                    {opt.ctxLabel}
                  </span>
                )}
                {opt.badge && (
                  <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.05em', color: '#888', textTransform: 'uppercase', backgroundColor: '#EDEAE4', borderRadius: 4, padding: '2px 5px' }}>
                    {opt.badge}
                  </span>
                )}
                {opt.value === value && (
                  <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
                    <path d="M1 5L4.5 8.5L11 1" stroke="#1a1a1a" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.07em', textTransform: 'uppercase', color: '#AAAAAA', margin: 0 }}>
      {children}
    </p>
  );
}
