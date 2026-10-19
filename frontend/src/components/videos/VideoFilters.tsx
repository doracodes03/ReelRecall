export type VideoSourceFilter = 'all' | 'youtube' | 'instagram';

export default function VideoFilters({
  value,
  onChange,
}: {
  value: VideoSourceFilter;
  onChange: (value: VideoSourceFilter) => void;
}) {
  const filters: { value: VideoSourceFilter; label: string }[] = [
    { value: 'all', label: 'All videos' },
    { value: 'youtube', label: 'YouTube' },
    { value: 'instagram', label: 'Instagram' },
  ];
  return (
    <div className="mb-5 flex flex-wrap gap-2" aria-label="Filter library by platform">
      {filters.map((filter) => (
        <button
          key={filter.value}
          type="button"
          aria-pressed={value === filter.value}
          onClick={() => onChange(filter.value)}
          className={`min-h-10 rounded-full px-4 text-sm font-semibold transition ${
            value === filter.value
              ? 'bg-[image:var(--rr-gradient)] text-white shadow-sm'
              : 'border border-[var(--rr-border)] bg-white text-[var(--rr-muted)] hover:border-[var(--rr-purple)]/40 hover:text-[var(--rr-purple)]'
          }`}
        >
          {filter.label}
        </button>
      ))}
    </div>
  );
}
