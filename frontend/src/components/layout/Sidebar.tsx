export default function Sidebar() {
  return (
    <aside className="w-64 rounded-2xl bg-slate-50 p-4">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">Library</h3>
      <ul className="space-y-2 text-sm text-slate-700">
        <li>Saved Reels</li>
        <li>Search history</li>
        <li>Semantic matches</li>
      </ul>
    </aside>
  );
}
