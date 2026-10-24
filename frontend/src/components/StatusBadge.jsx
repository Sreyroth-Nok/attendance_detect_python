export default function StatusBadge({ status }) {
  const active = status === 'Active';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
        active ? 'bg-primary-soft text-primary ring-1 ring-teal-200' : 'bg-slate-100 text-secondary ring-1 ring-slate-200'
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-primary' : 'bg-slate-400'}`}
        aria-hidden="true"
      />
      {status}
    </span>
  );
}
