interface ScoreRingProps {
  value: number;
  size?: number;
  label?: string;
}

export function ScoreRing({ value, size = 64, label }: ScoreRingProps) {
  const v = Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));
  const stroke = Math.max(4, Math.round(size / 10));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const color = v >= 0.7 ? "#10b981" : v >= 0.4 ? "#f59e0b" : "#ef4444";
  const pct = Math.round(v * 100);
  return (
    <div className="inline-flex flex-col items-center gap-1" role="img" aria-label={`${label ?? "Score"} ${pct}%`}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f1f5f9" strokeWidth={stroke} />
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - v)} />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center font-semibold text-slate-800" style={{ fontSize: Math.max(10, size / 4) }}>
          {pct}%
        </span>
      </div>
      {label && <span className="text-xs text-slate-500">{label}</span>}
    </div>
  );
}
