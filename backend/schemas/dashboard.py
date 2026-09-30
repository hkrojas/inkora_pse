"""Typed responses for the business dashboard analytics endpoint."""

from __future__ import annotations

from datetime import date as CalendarDate, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DashboardPeriod(BaseModel):
    start: CalendarDate
    end: CalendarDate
    label: str


class DashboardMeta(BaseModel):
    generated_at: datetime
    currency: str = "PEN"
    activity_start: Optional[CalendarDate] = None
    group_by: Literal["day", "month"] = "month"
    history_scope: Literal["all", "period"] = "all"
    period_scope: Literal["selected", "all"] = "selected"
    overdue_as_of: Optional[CalendarDate] = None
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
    date: Optional[CalendarDate] = None
    period_start: Optional[CalendarDate] = None
    period_end: Optional[CalendarDate] = None
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
    last_purchase: Optional[CalendarDate] = None
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


class DashboardRecordsMeta(BaseModel):
    period: DashboardPeriod
    currency: str = "PEN"
    client_id: Optional[int] = None
    product_id: Optional[int] = None
    contains_product_id: Optional[int] = None
    product_unit: Optional[str] = None
    measure: Literal["document", "product"] = "document"


class DashboardRecord(BaseModel):
    document_id: int
    reference: str
    tipo_comprobante: Optional[str] = None
    document_kind: str
    issued_at: datetime
    client_name: str
    amount: Decimal
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    state: str


class DashboardRecordsResponse(BaseModel):
    meta: DashboardRecordsMeta
    total: int
    total_amount: Decimal
    items: list[DashboardRecord]
    skip: int
    limit: int
