import type { RetrievalMode } from '../../types/search';

const modes: RetrievalMode[] = ['hybrid', 'lexical', 'semantic', 'visual', 'metadata'];

export default function SearchFilters({
  mode,
  onChange,
}: {
  mode: RetrievalMode;
  onChange: (next: RetrievalMode) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2 text-sm">
      {modes.map((item) => (
        <button
          key={item}
          type="button"
          aria-pressed={mode === item}
          onClick={() => onChange(item)}
          className={`min-h-10 rounded-full px-4 py-2 capitalize font-semibold transition ${
            mode === item
              ? 'bg-[image:var(--rr-gradient)] text-white shadow-sm'
              : 'border border-[var(--rr-border)] bg-white text-[var(--rr-muted)] hover:border-[var(--rr-purple)]/40 hover:text-[var(--rr-purple)]'
          }`}
        >
          {item}
        </button>
      ))}
    </div>
  );
}
