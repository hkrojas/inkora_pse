from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WarehouseCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=2, max_length=120)
    location: Optional[str] = Field(default=None, max_length=500)
    is_default: bool = False

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value):
        return value.strip().upper()


class WarehouseResponse(WarehouseCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class WarehouseUpdate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    location: Optional[str] = Field(default=None, max_length=500)
    is_default: bool = False


class InventoryActivation(BaseModel):
    warehouse_name: str = "Almacen principal"
    warehouse_code: str = "PRINCIPAL"


class StockResponse(BaseModel):
    product_id: int
    product_name: str
    product_code: Optional[str] = None
    warehouse_id: int
    warehouse_name: str
    unit: str
    on_hand: Decimal
    committed: Decimal
    available: Decimal
    minimum_stock: Decimal
    status: str


class InventoryAdjustmentCreate(BaseModel):
    warehouse_id: int
    product_id: int
    quantity: Decimal
    reason: str = Field(..., min_length=3, max_length=500)
    movement_type: str = "adjustment"
    idempotency_key: Optional[str] = Field(default=None, max_length=120)
    allow_negative: bool = False


class MovementResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    warehouse_id: int
    warehouse_name: str
    movement_type: str
    quantity: Decimal
    balance_before: Decimal
    balance_after: Decimal
    source_type: str
    source_id: Optional[int] = None
    source_line_id: Optional[int] = None
    source_document_number: Optional[str] = None
    source_document_type: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime


class MovementPageResponse(BaseModel):
    items: List[MovementResponse]
    total: int
    skip: int
    limit: int


class StockPageResponse(BaseModel):
    items: List[StockResponse]
    total: int
    skip: int
    limit: int


class BulkInventoryLine(BaseModel):
    product_id: int
    quantity: Decimal = Field(..., ge=0)


class BulkInventoryAdjustmentCreate(BaseModel):
    warehouse_id: int
    mode: Literal["add", "set"]
    reason: str = Field(..., min_length=3, max_length=500)
    idempotency_key: str = Field(..., min_length=8, max_length=120)
    items: List[BulkInventoryLine] = Field(..., min_length=1, max_length=500)


class BulkInventoryAdjustmentResponse(BaseModel):
    movement_ids: List[int]
    applied: int
    skipped: int


class TransferLine(BaseModel):
    product_id: int
    quantity: Decimal = Field(..., gt=0)


class TransferCreate(BaseModel):
    source_warehouse_id: int
    destination_warehouse_id: int
    reason: str = Field(..., min_length=3, max_length=500)
    items: List[TransferLine] = Field(..., min_length=1)
    allow_negative: bool = False


class ProductInventoryConfig(BaseModel):
    item_type: str
    inventory_enabled: bool
    warehouse_id: Optional[int] = None
    opening_stock: Decimal = Decimal("0")
    minimum_stock: Decimal = Decimal("0")

    @field_validator("item_type")
    @classmethod
    def validate_type(cls, value):
        value = value.strip().lower()
        if value not in {"inventory", "service"}:
            raise ValueError("Use inventory o service")
        return value


class AvailabilityRequest(BaseModel):
    warehouse_id: Optional[int] = None
    items: List[TransferLine]


class AvailabilityLine(BaseModel):
    product_id: int
    requested: Decimal
    available: Decimal
    sufficient: bool


class ReturnReceiptLine(BaseModel):
    return_item_id: int
    quantity: Decimal = Field(..., gt=0)


class ReturnReceiptCreate(BaseModel):
    items: List[ReturnReceiptLine] = Field(..., min_length=1)
    reason: Optional[str] = Field(default="Recepcion fisica de devolucion", max_length=500)
