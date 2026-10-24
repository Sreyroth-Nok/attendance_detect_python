const TONES = {
  primary: 'bg-primary-soft text-primary',
  accent: 'bg-accent-soft text-yellow-700',
  slate: 'bg-slate-100 text-secondary',
};

export default function StatCard({ label, value, icon: Icon, tone = 'primary', hint }) {
  return (
    <div className="card flex items-start gap-4 p-5">
      {Icon && (
        <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ${TONES[tone]}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
      )}
      <div className="min-w-0">
        <p className="text-sm font-medium text-secondary">{label}</p>
        <p className="mt-1 text-2xl font-semibold tracking-tight text-ink tabular-nums">{value}</p>
        {hint && <p className="mt-1 text-xs text-secondary">{hint}</p>}
      </div>
    </div>
  );
}
