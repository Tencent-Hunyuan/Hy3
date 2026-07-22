import { useEffect, useRef, useState, useCallback } from 'react';
import type { Lang } from './i18n/translations';
import ChatPanel from './components/ChatPanel';
import ResourcePanel from './components/ResourcePanel';
import TestPanel from './components/TestPanel';
import Onboarding from './components/Onboarding';
import Login from './components/Login';
import Settings from './components/Settings';
import SubjectSidebar from './components/SubjectSidebar';
import { useStore } from './store/useStore';
import { api } from './services/api';

const MIN_RIGHT_WIDTH = 200;
const MAX_RIGHT_WIDTH = 600;
const DEFAULT_RIGHT_WIDTH = 320;

export default function App() {
  const {
    onboardingComplete,
    activePanel,
    settingsOpen,
    layoutMode,
    loadFromConfig,
    loadLLMSettings,
    setUiLanguage,
    uiLanguage,
    subjects,
    activeSubjectId,
    authChecked,
    authRequired,
    authEmail,
    loadAuth,
  } = useStore();

  const [rightWidth, setRightWidth] = useState(DEFAULT_RIGHT_WIDTH);
  const isDragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Boot, step 1: resolve auth state first — local dev (no SESSION_SECRET on the
  // server) resolves to {authRequired: false} immediately, so this adds no visible
  // delay there. Never blocks on failure (offline/misconfigured server = no gate).
  useEffect(() => {
    api.auth.me()
      .then(loadAuth)
      .catch(() => loadAuth({ authRequired: false, email: null }));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Boot, step 2: load persisted config + LLM settings; detect locale from the
  // browser. Waits for auth to resolve so protected GET /config and GET /settings
  // aren't fired (and silently defaulted) before a hosted-mode visitor logs in.
  useEffect(() => {
    if (!authChecked || (authRequired && !authEmail)) return;
    const locale = navigator.language ?? 'en-US';
    Promise.all([
      api.config.load().catch(() => null),
      api.settings.load().catch(() => null),
    ]).then(([config, settings]) => {
      // Apply language: config overrides auto-detect if previously saved
      if (config) {
        loadFromConfig(config);
        if (!config.uiLanguage) {
          // Auto-detect from browser locale
          const isZh = locale.toLowerCase().startsWith('zh');
          setUiLanguage(isZh ? 'zh' : 'en');
        }
      } else {
        const isZh = locale.toLowerCase().startsWith('zh');
        setUiLanguage(isZh ? 'zh' : 'en');
      }
      if (settings) loadLLMSettings(settings);
    });
  }, [authChecked, authRequired, authEmail]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-save subjects whenever they change
  useEffect(() => {
    if (!onboardingComplete) return;
    api.config.save({ subjects, activeSubjectId }).catch(() => {});
  }, [subjects, activeSubjectId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Persist language preference whenever it changes
  useEffect(() => {
    if (!onboardingComplete) return;
    api.config.save({ uiLanguage: uiLanguage as Lang }).catch(() => {});
  }, [uiLanguage]); // eslint-disable-line react-hooks/exhaustive-deps

  // Drag-to-resize handlers
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const newWidth = rect.right - e.clientX;
    setRightWidth(Math.max(MIN_RIGHT_WIDTH, Math.min(MAX_RIGHT_WIDTH, newWidth)));
  }, []);

  const handleMouseUp = useCallback(() => {
    if (!isDragging.current) return;
    isDragging.current = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  }, [handleMouseMove]);

  const handleDividerMouseDown = useCallback(() => {
    isDragging.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [handleMouseMove, handleMouseUp]);

  if (!authChecked) return null;
  if (authRequired && !authEmail) return <Login />;
  if (!onboardingComplete) return <Onboarding />;

  return (
    <div ref={containerRef} className="flex flex-col h-screen" style={{ backgroundColor: '#FEFEFE' }}>
      {/* Full-width macOS titlebar drag strip — unifies the top edge */}
      <div style={{ height: 38, flexShrink: 0, backgroundColor: '#FEFEFE', borderBottom: '1px solid #EDE8E0', ...({ WebkitAppRegion: 'drag' } as React.CSSProperties) }} />
      <div className="flex flex-1" style={{ overflow: 'hidden' }}>
      {/* Far left: collapsible subject sidebar */}
      <SubjectSidebar />

      {/* Center: Chat — flex-1 in normal mode, 35% in cowork mode */}
      <div
        className="flex flex-col min-w-0"
        style={{
          position: 'relative',
          flex: layoutMode === 'cowork' ? '0 0 35%' : 1,
          minWidth: 280,
          transition: 'flex 0.25s ease',
        }}
      >
        <ChatPanel />
      </div>

      {/* Resize handle — hidden in cowork mode */}
      {layoutMode === 'normal' && (
        <div
          onMouseDown={handleDividerMouseDown}
          style={{
            width: 4, flexShrink: 0, cursor: 'col-resize',
            backgroundColor: 'transparent',
            borderLeft: '1px solid #E8E0D5',
            transition: 'background-color 0.15s',
            position: 'relative', zIndex: 10,
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.backgroundColor = '#F4D35E40'; }}
          onMouseLeave={(e) => { if (!isDragging.current) (e.currentTarget as HTMLDivElement).style.backgroundColor = 'transparent'; }}
          title="Drag to resize"
        />
      )}

      {/* Right: Resource Panel or Test Panel */}
      <div
        className="flex flex-col shrink-0"
        style={{
          overflow: 'hidden',
          borderLeft: '1px solid #E8E0D5',
          transition: 'flex 0.25s ease, width 0.25s ease',
          ...(layoutMode === 'cowork'
            ? { flex: 1 }
            : { width: rightWidth }
          ),
        }}
      >
        {activePanel === 'test' ? <TestPanel /> : <ResourcePanel />}
      </div>

      {/* Settings slide-in panel */}
      {settingsOpen && <Settings />}
      </div>
    </div>
  );
}
