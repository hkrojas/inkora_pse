"""Typed responses for the business dashboard analytics endpoint."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class DashboardPeriod(BaseModel):
    start: date
    end: date
    label: str


class DashboardMeta(BaseModel):
    generated_at: datetime
    currency: str = "PEN"
    period: DashboardPeriod
    comparison: DashboardPeriod
    history: DashboardPeriod
    client_id: Optional[int] = None
    product_id: Optional[int] = None


class DashboardSummary(BaseModel):
    sales_amount: Decimal
    sales_count: int
    pending_sunat_amount: Decimal
    sales_change_percent: Optional[Decimal] = None
    customers_count: int
    new_customers_count: int
    returning_customers_count: int
    average_sale: Decimal
    overdue_amount: Decimal
    overdue_customers_count: int


class DashboardHistoryPoint(BaseModel):
    year: int
    month: int = Field(ge=1, le=12)
    sales_amount: Decimal
    quoted_amount: Decimal
    is_partial: bool = False
    cutoff_day: Optional[int] = None
    previous_matched_sales: Optional[Decimal] = None


class DashboardConversion(BaseModel):
    available: bool = False
    reason: Optional[str] = None
    quote_count: Optional[int] = None
    linked_sales_count: Optional[int] = None
    rate_percent: Optional[Decimal] = None


class DashboardProductRow(BaseModel):
    id: Optional[int] = None
    name: str
    unit: str
    quantity: Decimal
    amount: Decimal
    previous_amount: Decimal
    change_percent: Optional[Decimal] = None


class DashboardClientRow(BaseModel):
    id: int
    name: str
    amount: Decimal
    purchases: int
    last_purchase: Optional[date] = None
    share_percent: Decimal
    previous_amount: Decimal
    change_percent: Optional[Decimal] = None


class DashboardFollowUpRow(BaseModel):
    quote_id: Optional[int] = None
    client_id: Optional[int] = None
    client: str
    reference: str
    amount: Decimal
    age_days: int


class DashboardFollowUpGroup(BaseModel):
    available: bool = True
    reason: Optional[str] = None
    count: int
    rows: list[DashboardFollowUpRow]


class DashboardFollowUp(BaseModel):
    quotes: DashboardFollowUpGroup
    declining: DashboardFollowUpGroup
    inactive: DashboardFollowUpGroup


class DashboardPending(BaseModel):
    low_stock_products: int
    fiscal_documents_with_errors: int


class BusinessDashboardResponse(BaseModel):
    meta: DashboardMeta
    summary: DashboardSummary
    history: list[DashboardHistoryPoint]
    conversion: DashboardConversion
    products: list[DashboardProductRow]
    clients: list[DashboardClientRow]
    follow_up: DashboardFollowUp
    pending: DashboardPending
