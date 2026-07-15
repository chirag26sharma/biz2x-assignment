from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.config import settings
from app.security.input_validation import InputValidationError, sanitize_question


class RiskCategory(str, Enum):
    LOW = "Low"
    WATCHLIST = "Watchlist"
    HIGH_RISK = "High Risk"
    CRITICAL = "Critical"


class Severity(str, Enum):
    INFO = "Info"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class RecommendedAction(str, Enum):
    SOFT_REMINDER = "soft reminder"
    PAYMENT_PLAN_OFFER = "payment plan offer"
    PROACTIVE_CALL = "proactive call"
    RESTRUCTURING_REVIEW = "restructuring review"
    MANUAL_ANALYST_REVIEW = "manual analyst review"
    NO_ACTION = "no action"


class UserRole(str, Enum):
    BORROWER = "borrower"
    ANALYST = "analyst"
    MANAGER = "manager"


class PaymentRecord(BaseModel):
    due_date: date
    due_amount: float
    paid_amount: float
    paid_date: date | None = None
    days_past_due: int = 0
    status: Literal["on_time", "late", "partial", "skipped", "missed"] = "on_time"
    channel: Literal["auto_debit", "manual", "unknown"] = "unknown"
    auto_debit_failed: bool = False


class TransactionRecord(BaseModel):
    date: date
    amount: float
    type: Literal["credit", "debit"]
    category: Literal["income", "expense", "emi", "other"] = "other"
    description: str = ""


class BalanceSnapshot(BaseModel):
    date: date
    account_balance: float
    credit_limit: float
    outstanding_balance: float


class LoanRecord(BaseModel):
    loan_id: str
    loan_amount: float
    emi_amount: float
    outstanding_balance: float
    credit_limit: float
    next_due_date: date
    product: str = "term_loan"


class BorrowerRecord(BaseModel):
    borrower_id: str
    name: str
    assigned_analyst_id: str | None = None
    loan: LoanRecord
    payments: list[PaymentRecord] = Field(default_factory=list)
    transactions: list[TransactionRecord] = Field(default_factory=list)
    balance_history: list[BalanceSnapshot] = Field(default_factory=list)
    scenario_tag: str = ""
    notes: str = ""


class UserRecord(BaseModel):
    user_id: str
    name: str
    role: UserRole
    borrower_id: str | None = None  # for borrower role


class RiskSignal(BaseModel):
    code: str
    label: str
    detail: str
    points: int


class RiskAssessment(BaseModel):
    borrower_id: str
    assessed_at: datetime
    risk_score: int
    risk_category: RiskCategory
    severity: Severity
    recommended_action: RecommendedAction
    signals: list[RiskSignal]
    insufficient_history: bool = False
    indicators: dict[str, float | int | bool | str | None] = Field(default_factory=dict)


class AlertSummary(BaseModel):
    borrower_id: str
    borrower_name: str
    risk_category: RiskCategory
    severity: Severity
    recommended_action: RecommendedAction
    risk_score: int
    key_reasons: list[str]
    next_due_date: date
    outstanding_balance: float
    insufficient_history: bool = False
    assigned_analyst_id: str | None = None


class ExplanationResponse(BaseModel):
    borrower_id: str
    risk_category: RiskCategory
    severity: Severity
    recommended_action: RecommendedAction
    key_reasons: list[str]
    explanation: str
    grounded: bool = True
    llm_used: bool = True


class QARequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        try:
            return sanitize_question(value, max_length=settings.qa_max_question_length)
        except InputValidationError as exc:
            raise ValueError(str(exc)) from exc


class QAResponse(BaseModel):
    borrower_id: str
    question: str
    answer: str
    grounded: bool = True
    llm_used: bool = True


class ScenarioRequest(BaseModel):
    miss_next_emi: bool = True


class PortfolioSummary(BaseModel):
    total_borrowers: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    total_outstanding_at_risk: float
    critical_count: int
    high_risk_count: int


class LoginRequest(BaseModel):
    user_id: str


class AuthUser(BaseModel):
    user_id: str
    name: str
    role: UserRole
    borrower_id: str | None = None


class LoginResponse(BaseModel):
    user: AuthUser
    token: str
    token_type: str = "bearer"
    expires_in: int
