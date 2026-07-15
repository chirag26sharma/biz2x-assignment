"use client";

import { formatINR } from "@/lib/api";

export type PaymentRow = {
  due_date: string;
  due_amount: number;
  paid_amount: number;
  paid_date?: string | null;
  days_past_due: number;
  status: string;
  channel?: string;
  auto_debit_failed?: boolean;
};

type BalanceRow = {
  date: string;
  outstanding_balance: number;
  credit_limit: number;
};

type Props = {
  payments: PaymentRow[];
  balanceHistory?: BalanceRow[];
};

function statusClass(status: string) {
  if (status === "on_time") return "badge cat-low";
  if (status === "partial" || status === "skipped") return "badge cat-medium";
  return "badge cat-high";
}

export function PaymentHistoryTable({ payments, balanceHistory = [] }: Props) {
  const sorted = [...payments].sort((a, b) => b.due_date.localeCompare(a.due_date));
  const latestBalance = [...balanceHistory].sort((a, b) => b.date.localeCompare(a.date))[0];
  const utilization =
    latestBalance && latestBalance.credit_limit > 0
      ? Math.round((latestBalance.outstanding_balance / latestBalance.credit_limit) * 100)
      : null;

  return (
    <div className="stack" style={{ gap: "1rem" }}>
      {utilization !== null && (
        <div className="row" style={{ gap: "1.5rem", flexWrap: "wrap" }}>
          <div>
            <div className="stat-label">Latest utilization</div>
            <div className="stat-value" style={{ fontSize: "1.25rem" }}>
              {utilization}%
            </div>
          </div>
          {latestBalance && (
            <div>
              <div className="stat-label">Outstanding / limit</div>
              <div style={{ fontSize: "0.95rem" }}>
                {formatINR(latestBalance.outstanding_balance)} / {formatINR(latestBalance.credit_limit)}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="table-wrap">
        <table className="table" data-testid="payment-history-table">
          <thead>
            <tr>
              <th>Due date</th>
              <th>Due</th>
              <th>Paid</th>
              <th>DPD</th>
              <th>Status</th>
              <th>Auto-debit</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((p) => (
              <tr key={p.due_date} style={{ cursor: "default" }}>
                <td className="mono">{p.due_date}</td>
                <td>{formatINR(p.due_amount)}</td>
                <td>{formatINR(p.paid_amount)}</td>
                <td className="mono">{p.days_past_due}</td>
                <td>
                  <span className={statusClass(p.status)}>{p.status.replace("_", " ")}</span>
                </td>
                <td className="muted">{p.auto_debit_failed ? "Failed" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!sorted.length && <p className="muted" style={{ margin: 0 }}>No payment records.</p>}
    </div>
  );
}
