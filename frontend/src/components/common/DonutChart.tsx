interface DonutChartProps {
  data: { label: string; value: number; color?: string }[];
  centerLabel?: string;
  centerValue?: string;
  size?: number;
  formatValue?: (n: number) => string;
}

const PALETTE = ["#6366f1", "#10b981", "#f59e0b", "#ec4899", "#0ea5e9", "#8b5cf6", "#14b8a6"];

export function DonutChart({ data, centerLabel, centerValue, size = 180, formatValue }: DonutChartProps) {
  const fmt = formatValue ?? ((n: number) => n.toLocaleString("en-IN"));
  const total = data.reduce((sum, d) => sum + Math.max(0, d.value), 0);
  const stroke = Math.round(size * 0.16);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const cx = size / 2;
  let offset = 0;
  const segments = data.map((d, i) => {
    const value = Math.max(0, d.value);
    const len = total > 0 ? (value / total) * c : 0;
    const seg = { ...d, color: d.color ?? PALETTE[i % PALETTE.length], len, offset, pct: total > 0 ? (value / total) * 100 : 0 };
    offset += len;
    return seg;
  });
  return (
    <div className="flex flex-col items-center gap-5 sm:flex-row">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={centerLabel ?? "Breakdown chart"} className="shrink-0">
        <g transform={`rotate(-90 ${cx} ${cx})`}>
          <circle cx={cx} cy={cx} r={r} fill="none" stroke="#f1f5f9" strokeWidth={stroke} />
          {segments.map((s) =>
            s.len > 0 ? (
              <circle key={s.label} cx={cx} cy={cx} r={r} fill="none" stroke={s.color} strokeWidth={stroke} strokeDasharray={`${s.len} ${c - s.len}`} strokeDashoffset={-s.offset} />
            ) : null,
          )}
        </g>
        {centerValue && (
          <text x={cx} y={centerLabel ? cx - 2 : cx + 6} textAnchor="middle" className="fill-slate-900 font-bold" style={{ fontSize: size * 0.12 }}>
            {centerValue}
          </text>
        )}
        {centerLabel && (
          <text x={cx} y={cx + size * 0.11} textAnchor="middle" className="fill-slate-500" style={{ fontSize: size * 0.07 }}>
            {centerLabel}
          </text>
        )}
      </svg>
      <ul className="w-full min-w-0 flex-1 space-y-2">
        {segments.map((s) => (
          <li key={s.label} className="flex items-center gap-2 text-sm">
            <span className="h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: s.color }} aria-hidden />
            <span className="min-w-0 flex-1 truncate text-slate-700">{s.label}</span>
            <span className="font-medium tabular-nums text-slate-900">{fmt(s.value)}</span>
            <span className="w-12 text-right text-xs tabular-nums text-slate-500">{s.pct.toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
