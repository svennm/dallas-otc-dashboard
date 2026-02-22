from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import RFQStatus, TradeSide, UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RFQCreate(BaseModel):
    client_id: int
    instrument_id: int
    side: TradeSide
    size: float = Field(gt=0)
    expiry_seconds: int = Field(default=20, ge=10, le=60)


class RFQOut(BaseModel):
    id: UUID
    client_id: int
    client_name: str
    instrument_id: int
    instrument_symbol: str
    side: TradeSide
    size: float
    quoted_price: float
    quote_expiry: datetime
    status: RFQStatus
    created_at: datetime


class TradeCreate(BaseModel):
    client_id: int
    instrument_id: int
    side: TradeSide
    size: float = Field(gt=0)
    price: float = Field(gt=0)
    rfq_id: UUID | None = None


class TradeOut(BaseModel):
    id: int
    client_id: int
    client_name: str
    instrument_id: int
    instrument_symbol: str
    side: TradeSide
    size: float
    price: float
    notional_usd: float
    timestamp: datetime


class TradesPage(BaseModel):
    items: list[TradeOut]
    page: int
    page_size: int
    total: int


class MarketPriceOut(BaseModel):
    instrument_id: int
    instrument_symbol: str
    bid: float
    ask: float
    mid: float
    spread_bps: float
    rolling_vwap: float
    volatility_5m: float
    ts: datetime


class PositionOut(BaseModel):
    client_id: int
    client_name: str
    instrument_id: int
    instrument_symbol: str
    net_size: float
    avg_price: float
    usd_exposure: float
    updated_at: datetime


class ClientAnalyticsOut(BaseModel):
    client_id: int
    client_name: str
    mark_to_market_pnl: float
    total_volume_usd: float
    avg_spread_capture_bps: float
    avg_rfq_response_seconds: float
    trade_count: int


class RiskLimitOut(BaseModel):
    id: int
    client_id: int | None
    client_name: str | None
    instrument_id: int | None
    instrument_symbol: str | None
    soft_limit_usd: float
    hard_limit_usd: float
    leverage_limit: float
    requires_supervisor: bool
    active: bool


class RiskOverrideRequest(BaseModel):
    client_id: int
    instrument_id: int
    proposed_notional_usd: float = Field(gt=0)
    reason: str = Field(min_length=5, max_length=500)


class RiskOverrideResponse(BaseModel):
    status: str
    approved_by_role: str
    message: str


class RiskCheckResult(BaseModel):
    soft_breach: bool
    hard_breach: bool
    projected_exposure_usd: float
    soft_limit_usd: float | None = None
    hard_limit_usd: float | None = None
    message: str
