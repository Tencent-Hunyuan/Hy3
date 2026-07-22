import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { useLang } from '../i18n/useLang';
import type { Subject } from '../../types';

export default function SubjectSidebar() {
  const {
    subjects, activeSubjectId, sidebarOpen,
    switchSubject, createNewSubject, deleteSubject, togglePinSubject,
    setSidebarOpen, setSettingsOpen,
  } = useStore();
  const { t } = useLang();

  async function handleSwitch(id: string) {
    switchSubject(id);
    const state = useStore.getState();
    api.config.save({ subjects: state.subjects, activeSubjectId: id }).catch(() => {});
  }

  async function handleNew() {
    createNewSubject();
    api.config.save({ activeSubjectId: null }).catch(() => {});
  }

  async function handleDelete(id: string) {
    deleteSubject(id);
    const state = useStore.getState();
    api.config.save({ subjects: state.subjects, activeSubjectId: state.activeSubjectId }).catch(() => {});
  }

  async function handlePin(id: string) {
    togglePinSubject(id);
    const state = useStore.getState();
    api.config.save({ subjects: state.subjects }).catch(() => {});
  }

  // Sort: pinned first (preserve insertion order within each group), then rest newest-first
  const sorted = [
    ...subjects.filter(s => s.pinned),
    ...subjects.filter(s => !s.pinned).slice().reverse(),
  ];

  const W_OPEN = 224;
  const W_CLOSED = 48;
  const w = sidebarOpen ? W_OPEN : W_CLOSED;

  return (
    <div
      style={{
        width: w, minWidth: w, maxWidth: w,
        height: '100%',
        backgroundColor: '#FAF6E8',
        borderRight: '1px solid #EDE0B8',
        display: 'flex', flexDirection: 'column',
        transition: 'width 0.2s ease, min-width 0.2s ease, max-width 0.2s ease',
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: sidebarOpen ? 'space-between' : 'center',
        padding: '2px 12px 12px',
        flexShrink: 0,
      }}>
        {sidebarOpen && (
          <span style={{
            fontSize: 11, fontWeight: 600, color: '#A09060',
            letterSpacing: '0.1em', textTransform: 'uppercase',
          }}>
            {t.sidebarSubjects}
          </span>
        )}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          title={sidebarOpen ? t.sidebarCollapse : t.sidebarExpand}
          style={iconBtn}
        >
          {sidebarOpen
            ? <ChevronLeft />
            : <ChevronRight />}
        </button>
      </div>

      {/* ── New Subject ─────────────────────────────────────────────────────── */}
      <div style={{ padding: sidebarOpen ? '0 10px 8px' : '0 8px 8px', flexShrink: 0 }}>
        <button
          onClick={handleNew}
          title={t.sidebarNewSubject}
          style={{
            width: '100%',
            display: 'flex', alignItems: 'center',
            gap: 8,
            padding: sidebarOpen ? '7px 10px' : '7px 0',
            justifyContent: sidebarOpen ? 'flex-start' : 'center',
            borderRadius: 7,
            border: '1px dashed #D8C880',
            backgroundColor: 'transparent',
            cursor: 'pointer', fontFamily: 'inherit',
            color: '#8A7A50',
            transition: 'border-color 0.12s, background-color 0.12s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = '#C8A820';
            e.currentTarget.style.backgroundColor = '#F5EDD4';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = '#D8C880';
            e.currentTarget.style.backgroundColor = 'transparent';
          }}
        >
          <PlusIcon />
          {sidebarOpen && (
            <span style={{ fontSize: 13, fontWeight: 500 }}>{t.sidebarNewSubject}</span>
          )}
        </button>
      </div>

      {/* ── Divider ────────────────────────────────────────────────────────── */}
      <div style={{ height: 1, backgroundColor: '#EDE0B8', flexShrink: 0, margin: '0 0 6px' }} />

      {/* ── Subject list ───────────────────────────────────────────────────── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: sidebarOpen ? '2px 8px' : '2px 6px' }}>
        {subjects.length === 0 ? (
          sidebarOpen ? (
            <p style={{ fontSize: 12, color: '#B8A870', padding: '10px 4px', lineHeight: 1.5 }}>
              {t.sidebarNoSubjects}
            </p>
          ) : null
        ) : (
          sorted.map((sub) => (
            <SubjectRow
              key={sub.id}
              sub={sub}
              isActive={sub.id === activeSubjectId}
              sidebarOpen={sidebarOpen}
              onSwitch={handleSwitch}
              onDelete={handleDelete}
              onPin={handlePin}
            />
          ))
        )}
      </div>

      {/* ── Settings ──────────────────────────────────────────────────────── */}
      <div style={{
        padding: sidebarOpen ? '8px 10px 14px' : '8px 6px 14px',
        borderTop: '1px solid #EDE0B8',
        flexShrink: 0,
      }}>
        <button
          onClick={() => setSettingsOpen(true)}
          title={t.sidebarSettings}
          style={{
            width: '100%',
            display: 'flex', alignItems: 'center', gap: 9,
            padding: sidebarOpen ? '7px 10px' : '7px 0',
            justifyContent: sidebarOpen ? 'flex-start' : 'center',
            borderRadius: 7, border: 'none',
            backgroundColor: 'transparent', cursor: 'pointer',
            fontFamily: 'inherit', color: '#8A7A50',
            transition: 'background-color 0.12s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#F5EDD4')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
        >
          <SettingsIcon />
          {sidebarOpen && <span style={{ fontSize: 13 }}>{t.sidebarSettings}</span>}
        </button>
      </div>
    </div>
  );
}

// ── Subject row ────────────────────────────────────────────────────────────────

interface RowProps {
  sub: Subject;
  isActive: boolean;
  sidebarOpen: boolean;
  onSwitch: (id: string) => void;
  onDelete: (id: string) => void;
  onPin: (id: string) => void;
}

function SubjectRow({ sub, isActive, sidebarOpen, onSwitch, onDelete, onPin }: RowProps) {
  const [hovered, setHovered] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const confirmTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-cancel delete confirm after 3s
  useEffect(() => {
    if (confirmDelete) {
      confirmTimer.current = setTimeout(() => setConfirmDelete(false), 3000);
    }
    return () => { if (confirmTimer.current) clearTimeout(confirmTimer.current); };
  }, [confirmDelete]);

  function handleDeleteClick(e: React.MouseEvent) {
    e.stopPropagation();
    setConfirmDelete(true);
  }

  function handleConfirmDelete(e: React.MouseEvent) {
    e.stopPropagation();
    setConfirmDelete(false);
    onDelete(sub.id);
  }

  function handleCancelDelete(e: React.MouseEvent) {
    e.stopPropagation();
    setConfirmDelete(false);
  }

  function handlePinClick(e: React.MouseEvent) {
    e.stopPropagation();
    onPin(sub.id);
  }

  const showActions = sidebarOpen && hovered;

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => { setHovered(false); setConfirmDelete(false); }}
      onClick={() => onSwitch(sub.id)}
      title={sub.name}
      style={{
        width: '100%',
        display: 'flex', alignItems: 'center', gap: 8,
        padding: sidebarOpen ? '7px 8px 7px 10px' : '8px 0',
        justifyContent: sidebarOpen ? 'flex-start' : 'center',
        borderRadius: 7,
        backgroundColor: isActive
          ? '#F0E8C0'
          : hovered ? '#F5EDD4' : 'transparent',
        cursor: 'pointer',
        marginBottom: 1,
        transition: 'background-color 0.1s',
        position: 'relative',
        boxSizing: 'border-box',
        borderLeft: isActive ? '2px solid #C8A820' : '2px solid transparent',
      }}
    >
      {/* Dot */}
      <span style={{
        width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
        backgroundColor: isActive ? '#C8A820' : sub.pinned ? '#D4B840' : '#D0C090',
        transition: 'background-color 0.15s',
      }} />

      {sidebarOpen && (
        <>
          {/* Name */}
          <span style={{
            fontSize: 13,
            color: isActive ? '#1A1200' : hovered ? '#2A2000' : '#7A6840',
            fontWeight: isActive ? 500 : 400,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            flex: 1,
            lineHeight: 1.4,
            transition: 'color 0.1s',
          }}>
            {sub.pinned && !showActions && (
              <span style={{ fontSize: 9, marginRight: 4, opacity: 0.5 }}>◆</span>
            )}
            {sub.name}
          </span>

          {/* Delete confirm bar — explicit buttons, not a silent icon-swap on the same button */}
          {confirmDelete ? (
            <div
              style={{ display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <span style={{ fontSize: 11, color: '#C0392B', fontWeight: 600, whiteSpace: 'nowrap' }}>
                Delete?
              </span>
              <button
                onClick={handleConfirmDelete}
                style={{
                  fontSize: 11, fontWeight: 600, color: '#fff',
                  backgroundColor: '#C0392B', border: 'none', borderRadius: 5,
                  padding: '4px 8px', cursor: 'pointer', fontFamily: 'inherit',
                }}
              >
                Delete
              </button>
              <button
                onClick={handleCancelDelete}
                style={{
                  fontSize: 11, fontWeight: 500, color: '#8A7A50',
                  backgroundColor: 'transparent', border: '1px solid #D8C880', borderRadius: 5,
                  padding: '4px 8px', cursor: 'pointer', fontFamily: 'inherit',
                }}
              >
                Cancel
              </button>
            </div>
          ) : showActions && (
            <div
              style={{ display: 'flex', gap: 2, flexShrink: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Pin */}
              <ActionBtn
                title={sub.pinned ? 'Unpin' : 'Pin to top'}
                active={sub.pinned}
                onClick={handlePinClick}
              >
                <PinIcon pinned={sub.pinned} />
              </ActionBtn>

              {/* Delete */}
              <ActionBtn title="Delete" onClick={handleDeleteClick}>
                <TrashIcon />
              </ActionBtn>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Small action button ────────────────────────────────────────────────────────

function ActionBtn({
  children, onClick, title, active, danger,
}: {
  children: React.ReactNode;
  onClick: (e: React.MouseEvent) => void;
  title?: string;
  active?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      style={{
        width: 22, height: 22,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        borderRadius: 5, border: 'none',
        backgroundColor: danger ? '#FDECEA' : active ? '#EEE0A0' : 'transparent',
        cursor: 'pointer',
        color: danger ? '#C0392B' : active ? '#8A6A00' : '#A09060',
        flexShrink: 0,
        transition: 'background-color 0.1s, color 0.1s',
      }}
      onMouseEnter={(e) => {
        if (!danger && !active) e.currentTarget.style.backgroundColor = '#EEE4C0';
      }}
      onMouseLeave={(e) => {
        if (!danger && !active) e.currentTarget.style.backgroundColor = 'transparent';
      }}
    >
      {children}
    </button>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────

const iconBtn: React.CSSProperties = {
  width: 26, height: 26, borderRadius: 6,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  border: 'none', backgroundColor: 'transparent', cursor: 'pointer',
  color: '#A09060', flexShrink: 0,
  // @ts-ignore
  WebkitAppRegion: 'no-drag',
};

const ChevronLeft = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <polyline points="15 18 9 12 15 6"/>
  </svg>
);
const ChevronRight = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <polyline points="9 18 15 12 9 6"/>
  </svg>
);
const PlusIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
);
const SettingsIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
);
const PinIcon = ({ pinned }: { pinned?: boolean }) => (
  <svg width="11" height="11" viewBox="0 0 24 24" fill={pinned ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="17" x2="12" y2="22"/>
    <path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/>
  </svg>
);
const TrashIcon = () => (
  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14H6L5 6"/>
    <path d="M10 11v6M14 11v6"/>
    <path d="M9 6V4h6v2"/>
  </svg>
);
