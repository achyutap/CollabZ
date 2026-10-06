const intFmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 0, maximumFractionDigits: 0 });
const decFmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function MoneyText({ amount, className }: { amount: number; className?: string }) {
  const isInt = Number.isInteger(Math.round(amount * 100) / 100);
  return <span className={className ?? "tabular-nums"}>{(isInt ? intFmt : decFmt).format(amount)}</span>;
}
