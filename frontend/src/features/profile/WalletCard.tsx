"use client";
import { useFetch } from "@/lib/hooks";
import type { WalletOut } from "@/lib/types";
import { MoneyText, Spinner } from "@/components/common";
import { formatDate } from "@/components/common/format";
import { useErrorToast } from "./util";

export default function WalletCard() {
  const { data, error, loading } = useFetch<WalletOut>("/me/wallet");
  useErrorToast(error);
  return (
    <section className="card space-y-3 p-5" aria-label="Wallet">
      <h2 className="section-title">Wallet</h2>
      {loading && !data ? <Spinner /> : data ? (
        <>
          <p className="text-2xl font-semibold"><MoneyText amount={data.balance} /></p>
          {data.entries.length === 0 ? <p className="muted text-sm">No transactions yet.</p> : (
            <div className="overflow-x-auto">
              <table className="table-clean w-full text-sm">
                <thead><tr><th className="text-left">Type</th><th className="text-right">Amount</th><th className="text-right">Date</th></tr></thead>
                <tbody>
                  {data.entries.map((e) => (
                    <tr key={e.id}>
                      <td><span className="badge">{e.type.replace(/_/g, " ")}</span></td>
                      <td className={`text-right ${e.amount < 0 ? "text-rose-600" : "text-emerald-600"}`}><MoneyText amount={e.amount} /></td>
                      <td className="muted text-right">{formatDate(e.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </section>
  );
}
