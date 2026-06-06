export function ProgressRing({ value, label }: { value: number; label: string }) {
  const safe = Math.max(0, Math.min(100, value));
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const dash = (safe / 100) * circumference;
  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 110 110" className="h-24 w-24 shrink-0">
        <circle cx="55" cy="55" r={radius} fill="none" stroke="#dce8e3" strokeWidth="12" />
        <circle cx="55" cy="55" r={radius} fill="none" stroke="#1f7a5f" strokeLinecap="round" strokeWidth="12" strokeDasharray={`${dash} ${circumference}`} transform="rotate(-90 55 55)" />
        <text x="55" y="60" textAnchor="middle" className="fill-ink text-xl font-bold dark:fill-white">{Math.round(safe)}%</text>
      </svg>
      <div>
        <p className="text-sm uppercase tracking-[0.18em] text-ink/50 dark:text-white/60">{label}</p>
        <p className="text-2xl font-bold text-ink dark:text-white">{Math.round(safe)}%</p>
      </div>
    </div>
  );
}
