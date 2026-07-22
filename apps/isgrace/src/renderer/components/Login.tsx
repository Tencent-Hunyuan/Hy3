import { useState, useRef, useEffect } from 'react';
import GraceAvatar from './GraceAvatar';
import { useStore } from '../store/useStore';
import { api } from '../services/api';
import { useLang } from '../i18n/useLang';

export default function Login() {
  const { loadAuth } = useStore();
  const { t } = useLang();

  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError('');
    try {
      const { email: loggedInEmail } = await api.auth.login(trimmed);
      loadAuth({ authRequired: true, email: loggedInEmail });
    } catch {
      setError(t.loginError);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="flex flex-col items-center justify-center h-screen"
      style={{ backgroundColor: '#FEFEFE' }}
    >
      <div style={{ width: '100%', maxWidth: 380, padding: '0 24px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 32 }}>
          <GraceAvatar size="md" />
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#111', letterSpacing: '-0.02em', margin: '18px 0 6px', textAlign: 'center' }}>
            {t.loginTitle}
          </h1>
          <p style={{ fontSize: 14, color: '#999', margin: 0, textAlign: 'center' }}>
            {t.loginSubtitle}
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <input
            ref={inputRef}
            type="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); setError(''); }}
            placeholder={t.loginPlaceholder}
            disabled={submitting}
            style={{
              width: '100%', padding: '13px 15px', borderRadius: 10,
              border: '1.5px solid #DEDAD4', backgroundColor: '#F6F3EE',
              fontSize: 15, color: '#1a1a1a', outline: 'none',
              fontFamily: 'inherit', boxSizing: 'border-box',
              opacity: submitting ? 0.6 : 1,
            }}
          />
          {error && (
            <p style={{ margin: 0, fontSize: 12.5, color: '#dc2626' }}>{error}</p>
          )}
          <button
            type="submit"
            disabled={submitting || !email.trim()}
            style={{
              width: '100%', padding: '13px', borderRadius: 10,
              backgroundColor: '#F4D35E', border: 'none',
              fontSize: 15, fontWeight: 600, color: '#1a1a1a',
              cursor: submitting || !email.trim() ? 'not-allowed' : 'pointer',
              opacity: !email.trim() ? 0.5 : 1,
              fontFamily: 'inherit', letterSpacing: '-0.01em',
            }}
          >
            {submitting ? t.loginSubmitting : t.loginButton}
          </button>
        </form>
      </div>
    </div>
  );
}
