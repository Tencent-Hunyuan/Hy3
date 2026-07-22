import GraceAvatar from './GraceAvatar';
import { useStore } from '../store/useStore';

export default function Header() {
  const { courseInfo, setSettingsOpen, llmReady } = useStore();

  return (
    <header
      className="flex items-center justify-between px-4 h-12 border-b shrink-0"
      style={{ borderColor: '#E8E0D5', backgroundColor: '#FEFEFE', WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      {/* Left: logo + course */}
      <div className="flex items-center gap-2" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
        <GraceAvatar size="xs" />
        <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', letterSpacing: '-0.01em' }}>isGrace</span>
        {courseInfo.name && (
          <>
            <span style={{ color: '#DDD', fontSize: 13 }}>·</span>
            <span style={{ fontSize: 13, color: '#888' }}>{courseInfo.name}</span>
          </>
        )}
      </div>

      {/* Right: LLM status dot + settings */}
      <div className="flex items-center gap-2" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
        {/* Connection status indicator */}
        <div
          title={llmReady ? 'LLM connected' : 'No API key — click Settings'}
          style={{
            width: 6, height: 6, borderRadius: '50%',
            backgroundColor: llmReady ? '#4ade80' : '#DEDAD4',
            transition: 'background-color 0.3s',
          }}
        />

        <button
          onClick={() => setSettingsOpen(true)}
          className="w-7 h-7 rounded flex items-center justify-center transition-colors"
          style={{ WebkitAppRegion: 'no-drag', color: '#888', backgroundColor: 'transparent', border: 'none', cursor: 'pointer' } as React.CSSProperties}
          title="Settings"
        >
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
            <path d="M7.07095 0.650238C6.67391 0.650238 6.32977 0.925096 6.24198 1.31231L6.0039 2.36247C5.6249 2.47269 5.26335 2.62363 4.92436 2.81013L4.01335 2.23585C3.67748 2.02413 3.23978 2.07312 2.95903 2.35386L2.35294 2.95997C2.0722 3.24071 2.0232 3.67842 2.23493 4.01428L2.80942 4.92561C2.62307 5.2645 2.47227 5.62594 2.36216 6.00481L1.31209 6.24287C0.924883 6.33065 0.650024 6.67479 0.650024 7.07182V7.92897C0.650024 8.32601 0.924883 8.67015 1.31209 8.75794L2.36226 8.99601C2.47246 9.37485 2.62335 9.73627 2.80974 10.0752L2.23528 10.9865C2.02355 11.3224 2.07254 11.7601 2.35328 12.0408L2.95938 12.6469C3.24011 12.9277 3.67782 12.9767 4.01369 12.7649L4.92477 12.1905C5.26375 12.377 5.62516 12.5279 6.00397 12.6381L6.24198 13.6879C6.32977 14.0751 6.67391 14.35 7.07095 14.35H7.92811C8.32514 14.35 8.66928 14.0751 8.75707 13.6879L8.99507 12.638C9.37388 12.5278 9.73529 12.3769 10.0742 12.1905L10.9854 12.7649C11.3213 12.9767 11.759 12.9277 12.0397 12.6469L12.6458 12.0408C12.9266 11.7601 12.9756 11.3224 12.7638 10.9865L12.1894 10.0752C12.3758 9.73625 12.5267 9.37481 12.6369 8.99596L13.687 8.75794C14.0742 8.67015 14.3491 8.32601 14.3491 7.92897V7.07182C14.3491 6.67479 14.0742 6.33065 13.687 6.24287L12.6369 6.00485C12.5268 5.62596 12.3759 5.26448 12.1894 4.92553L12.7638 4.01428C12.9756 3.67842 12.9266 3.24071 12.6458 2.95997L12.0397 2.35386C11.759 2.07312 11.3213 2.02413 10.9854 2.23585L10.0742 2.81016C9.73523 2.62367 9.37375 2.47273 8.99488 2.36251L8.75707 1.31231C8.66928 0.925096 8.32514 0.650238 7.92811 0.650238H7.07095ZM7.49953 9.74999C8.74217 9.74999 9.74953 8.74263 9.74953 7.49999C9.74953 6.25736 8.74217 5.24999 7.49953 5.24999C6.2569 5.24999 5.24953 6.25736 5.24953 7.49999C5.24953 8.74263 6.2569 9.74999 7.49953 9.74999Z"
              fill="currentColor" fillRule="evenodd" clipRule="evenodd"/>
          </svg>
        </button>
      </div>
    </header>
  );
}
