import { useState, type FormEvent } from 'react';
import { authenticate } from '../services/auth';

export default function AuthPage({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await authenticate(mode, { email, password, full_name: fullName });
      onAuthenticated();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Authentication failed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-4 py-8">
      <form onSubmit={submit} className="w-full max-w-md space-y-5 rounded-3xl border border-[var(--rr-border)] bg-white p-6 shadow-xl shadow-purple-950/10 sm:p-8">
        <div>
          <h1 className="bg-[image:var(--rr-gradient)] bg-clip-text text-3xl font-extrabold text-transparent">ReelRecall</h1>
          <p className="mt-2 text-sm text-[var(--rr-muted)]">
            {mode === 'login' ? 'Sign in to your private video library.' : 'Create a private video library.'}
          </p>
        </div>
        {mode === 'register' && (
          <label className="block text-sm font-semibold text-[var(--rr-text)]">
            Name
            <input
              required
              maxLength={160}
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              className="mt-1 min-h-12 w-full rounded-xl border border-[var(--rr-border)] px-4 py-3 focus:border-[var(--rr-purple)] focus:outline-none focus:ring-4 focus:ring-[var(--rr-purple)]/10"
            />
          </label>
        )}
        <label className="block text-sm font-semibold text-[var(--rr-text)]">
          Email
          <input
            required
            type="email"
            maxLength={254}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-1 min-h-12 w-full rounded-xl border border-[var(--rr-border)] px-4 py-3 focus:border-[var(--rr-purple)] focus:outline-none focus:ring-4 focus:ring-[var(--rr-purple)]/10"
          />
        </label>
        <label className="block text-sm font-semibold text-[var(--rr-text)]">
          Password
          <input
            required
            type="password"
            minLength={mode === 'register' ? 12 : 1}
            maxLength={256}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1 min-h-12 w-full rounded-xl border border-[var(--rr-border)] px-4 py-3 focus:border-[var(--rr-purple)] focus:outline-none focus:ring-4 focus:ring-[var(--rr-purple)]/10"
          />
          {mode === 'register' && <span className="mt-1 block text-xs text-[var(--rr-muted)]">Use at least 12 characters.</span>}
        </label>
        {error && <p role="alert" className="text-sm text-rose-800">{error}</p>}
        <button
          disabled={submitting}
          className="min-h-12 w-full rounded-xl bg-[image:var(--rr-gradient)] px-4 py-3 font-bold text-white shadow-md shadow-purple-950/10 transition hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
        </button>
        <p className="text-center text-sm text-[var(--rr-muted)]">
          {mode === 'login' ? 'New to ReelRecall?' : 'Already have an account?'}{' '}
          <button
            type="button"
            className="font-bold text-[var(--rr-purple)] underline-offset-4 hover:underline"
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login');
              setError('');
            }}
          >
            {mode === 'login' ? 'Create an account' : 'Sign in'}
          </button>
        </p>
      </form>
    </main>
  );
}
