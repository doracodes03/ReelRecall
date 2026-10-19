type ButtonProps = {
  children: React.ReactNode;
  variant?: 'primary' | 'ghost' | 'outline';
  onClick?: () => void;
  disabled?: boolean;
  type?: 'button' | 'submit';
  className?: string;
};

export default function Button({
  children,
  variant = 'primary',
  onClick,
  disabled = false,
  type = 'button',
  className = '',
}: ButtonProps) {
  const base = 'inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-bold transition duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-55';
  const styles = {
    primary: 'bg-[image:var(--rr-gradient)] text-white shadow-md shadow-fuchsia-900/15 hover:-translate-y-0.5 hover:shadow-lg active:translate-y-0',
    ghost: 'border border-[var(--rr-border)] bg-white text-[var(--rr-text)] hover:bg-[var(--rr-lavender)]',
    outline: 'border border-[var(--rr-purple)]/30 bg-white text-[var(--rr-purple)] hover:border-[var(--rr-purple)] hover:bg-[var(--rr-lavender)]',
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${styles[variant]} ${className}`}
    >
      {children}
    </button>
  );
}
