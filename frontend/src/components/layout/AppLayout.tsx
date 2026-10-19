import Navbar from './Navbar';

export default function AppLayout({
  children,
  onSignOut,
}: {
  children: React.ReactNode;
  onSignOut: () => void;
}) {
  return (
    <div className="min-h-screen text-[var(--rr-text)]">
      <Navbar onSignOut={onSignOut} />
      <main className="mx-auto w-full max-w-7xl px-4 py-7 sm:px-6 lg:px-8 lg:py-10">{children}</main>
    </div>
  );
}
