import { API_BASE } from "./config";

export { API_BASE };

export type UserRole = "borrower" | "analyst" | "manager";

export type AuthUser = {
  user_id: string;
  name: string;
  role: UserRole;
  borrower_id: string | null;
};

export type AlertSummary = {
  borrower_id: string;
  borrower_name: string;
  risk_category: string;
  severity: string;
  recommended_action: string;
  risk_score: number;
  key_reasons: string[];
  next_due_date: string;
  outstanding_balance: number;
  insufficient_history: boolean;
  assigned_analyst_id: string | null;
};

export type RiskSignal = {
  code: string;
  label: string;
  detail: string;
  points: number;
};

export type RiskAssessment = {
  borrower_id: string;
  assessed_at: string;
  risk_score: number;
  risk_category: string;
  severity: string;
  recommended_action: string;
  signals: RiskSignal[];
  insufficient_history: boolean;
  indicators: Record<string, string | number | boolean | null>;
};

export type ExplanationResponse = {
  borrower_id: string;
  risk_category: string;
  severity: string;
  recommended_action: string;
  key_reasons: string[];
  explanation: string;
  grounded: boolean;
  llm_used: boolean;
};

export type PortfolioSummary = {
  total_borrowers: number;
  by_category: Record<string, number>;
  by_severity: Record<string, number>;
  total_outstanding_at_risk: number;
  critical_count: number;
  high_risk_count: number;
};

export type LoanProfile = {
  loan_id: string;
  loan_amount: number;
  emi_amount: number;
  outstanding_balance: number;
  credit_limit: number;
  next_due_date: string;
  product?: string;
};

export type PaymentProfile = {
  due_date: string;
  due_amount: number;
  paid_amount: number;
  paid_date?: string | null;
  days_past_due: number;
  status: string;
  channel?: string;
  auto_debit_failed?: boolean;
};

export type BalanceSnapshot = {
  date: string;
  account_balance: number;
  credit_limit: number;
  outstanding_balance: number;
};

export type BorrowerProfile = {
  borrower_id: string;
  name: string;
  assigned_analyst_id?: string | null;
  loan: LoanProfile;
  payments: PaymentProfile[];
  balance_history: BalanceSnapshot[];
  scenario_tag?: string;
  notes?: string;
};

export type PublicConfig = {
  as_of_default: string;
  delinquency_horizon_days: number;
  llm_configured: boolean;
  api_version: string;
};

export type Session = {
  user: AuthUser;
  token: string;
  expiresAt?: number;
};

async function api<T>(
  path: string,
  options: RequestInit & { token?: string } = {},
): Promise<T> {
  const { token, headers, ...rest } = options;
  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export function listUsers() {
  return api<AuthUser[]>("/api/auth/users");
}

export function login(user_id: string) {
  return api<{ user: AuthUser; token: string; token_type: string; expires_in: number }>(
    "/api/auth/login",
    {
      method: "POST",
      body: JSON.stringify({ user_id }),
      credentials: "include",
    },
  );
}

export function getMe(token: string) {
  return api<AuthUser>("/api/auth/me", { token });
}

export function listAlerts(token: string) {
  return api<AlertSummary[]>("/api/alerts", { token });
}

export function getAssessment(token: string, borrowerId: string) {
  return api<RiskAssessment>(`/api/borrowers/${borrowerId}/assessment`, { token });
}

export function getBorrowerUpdate(token: string, borrowerId: string) {
  return api<ExplanationResponse>(`/api/borrowers/${borrowerId}/borrower-update`, { token });
}

export function getExplanation(token: string, borrowerId: string) {
  return api<ExplanationResponse>(`/api/borrowers/${borrowerId}/explanation`, {
    token,
  });
}

export function getProfile(token: string, borrowerId: string) {
  return api<BorrowerProfile>(`/api/borrowers/${borrowerId}/profile`, {
    token,
  });
}

export function getPublicConfig() {
  return api<PublicConfig>("/api/config/public");
}

export function askQuestion(token: string, borrowerId: string, question: string) {
  return api<{ borrower_id: string; question: string; answer: string; llm_used?: boolean }>(
    `/api/borrowers/${borrowerId}/qa`,
    { method: "POST", token, body: JSON.stringify({ question }) },
  );
}

export function runScenario(token: string, borrowerId: string) {
  return api<RiskAssessment>(`/api/borrowers/${borrowerId}/scenario`, {
    method: "POST",
    token,
    body: JSON.stringify({ miss_next_emi: true }),
  });
}

export function getPortfolio(token: string) {
  return api<PortfolioSummary>("/api/portfolio/summary", { token });
}

export function formatINR(n: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
}
