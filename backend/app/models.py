import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRole(str, enum.Enum):
    trader = "trader"
    risk = "risk"
    admin = "admin"
    viewer = "viewer"


class TradeSide(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class RFQStatus(str, enum.Enum):
    pending = "pending"
    quoted = "quoted"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(30), nullable=False, default="standard")
    default_markup_bps: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    base_asset: Mapped[str] = mapped_column(String(20), nullable=False)
    quote_asset: Mapped[str] = mapped_column(String(20), nullable=False, default="USD")
    tick_size: Mapped[float] = mapped_column(Float, default=0.01, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True, nullable=False)
    exchange: Mapped[str] = mapped_column(String(30), nullable=False)
    bid: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    ask: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    mid: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    spread_bps: Mapped[float] = mapped_column(Float, nullable=False)
    rolling_vwap: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    volatility_5m: Mapped[float] = mapped_column(Float, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    instrument: Mapped[Instrument] = relationship()


class RFQRequest(Base):
    __tablename__ = "rfq_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True, nullable=False)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True, nullable=False)
    requested_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    side: Mapped[TradeSide] = mapped_column(Enum(TradeSide), nullable=False)
    size: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    quoted_price: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    quote_expiry: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[RFQStatus] = mapped_column(Enum(RFQStatus), default=RFQStatus.quoted, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    client: Mapped[Client] = relationship()
    instrument: Mapped[Instrument] = relationship()


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rfq_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rfq_requests.id"), nullable=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True, nullable=False)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True, nullable=False)
    side: Mapped[TradeSide] = mapped_column(Enum(TradeSide), nullable=False)
    size: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    notional_usd: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    executed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    client: Mapped[Client] = relationship()
    instrument: Mapped[Instrument] = relationship()


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("client_id", "instrument_id", name="uq_position_client_instrument"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    net_size: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    avg_price: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    usd_exposure: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    client: Mapped[Client] = relationship()
    instrument: Mapped[Instrument] = relationship()


class RiskLimit(Base):
    __tablename__ = "risk_limits"
    __table_args__ = (
        UniqueConstraint("client_id", "instrument_id", name="uq_limit_client_instrument"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), nullable=True, index=True)
    instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id"), nullable=True, index=True
    )
    soft_limit_usd: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    hard_limit_usd: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    leverage_limit: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)
    requires_supervisor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    client: Mapped[Client | None] = relationship()
    instrument: Mapped[Instrument | None] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    immutable_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user: Mapped[User | None] = relationship()


Index("ix_market_prices_instrument_ts", MarketPrice.instrument_id, MarketPrice.ts.desc())
Index("ix_trades_client_instrument_ts", Trade.client_id, Trade.instrument_id, Trade.timestamp.desc())
Index("ix_rfq_status_expiry", RFQRequest.status, RFQRequest.quote_expiry)
Index("ix_positions_client_asset", Position.client_id, Position.instrument_id)
Index("ix_audit_entity_created", AuditLog.entity_type, AuditLog.entity_id, AuditLog.created_at.desc())
