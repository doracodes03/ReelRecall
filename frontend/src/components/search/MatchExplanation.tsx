export default function MatchExplanation({ reason }: { reason: string }) {
  return (
    <div className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-900">
      {reason}
    </div>
  );
}
