import { Link, NavLink } from 'react-router-dom';

export default function Navbar({ onSignOut }: { onSignOut: () => void }) {
  const navClass = ({ isActive }: { isActive: boolean }) => (
    `rounded-full px-4 py-2 text-sm font-semibold transition ${
      isActive
        ? 'bg-[var(--rr-lavender)] text-[var(--rr-purple)]'
        : 'text-[var(--rr-muted)] hover:bg-[var(--rr-blush)] hover:text-[var(--rr-pink)]'
    }`
  );

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--rr-border)] bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex min-h-[4.5rem] max-w-7xl flex-wrap items-center justify-between gap-x-3 gap-y-0 px-4 py-2 sm:flex-nowrap sm:px-6 sm:py-0 lg:px-8">
        <Link to="/" className="flex shrink-0 items-center gap-2.5" aria-label="ReelRecall home">
          <span className="grid size-9 place-items-center rounded-xl bg-[image:var(--rr-gradient)] text-sm font-black text-white shadow-sm">R</span>
          <span className="text-lg font-extrabold tracking-tight text-[var(--rr-text)] sm:text-xl">ReelRecall</span>
        </Link>
        <div className="flex w-full flex-wrap items-center justify-end sm:w-auto sm:flex-nowrap sm:gap-2">
          <nav aria-label="Main navigation" className="order-2 flex w-full items-center justify-between border-t border-[var(--rr-border)] pt-1 sm:order-1 sm:w-auto sm:justify-start sm:gap-2 sm:border-0 sm:pt-0">
            <NavLink to="/" end className={navClass}>Discover</NavLink>
            <NavLink to="/library" className={navClass}>Library</NavLink>
            <NavLink to="/search" className={navClass}>Search</NavLink>
          </nav>
          <button
            type="button"
            onClick={onSignOut}
            className="order-1 min-h-9 rounded-full px-3 py-1.5 text-sm font-semibold text-[var(--rr-muted)] transition hover:bg-[var(--rr-blush)] hover:text-[var(--rr-pink)] sm:order-2 sm:px-4"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
