type InputProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  id?: string;
  type?: string;
  required?: boolean;
  autoFocus?: boolean;
};

export default function Input({
  value,
  onChange,
  placeholder,
  id,
  type = 'text',
  required = false,
  autoFocus = false,
}: InputProps) {
  return (
    <input
      id={id}
      type={type}
      required={required}
      autoFocus={autoFocus}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      className="min-h-12 w-full rounded-xl border border-[var(--rr-border)] bg-white px-4 py-3 text-base text-[var(--rr-text)] placeholder:text-[var(--rr-muted)] transition focus:border-[var(--rr-purple)] focus:outline-none focus:ring-4 focus:ring-[var(--rr-purple)]/10"
    />
  );
}
