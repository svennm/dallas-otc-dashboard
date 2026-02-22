CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
    CREATE TYPE user_role AS ENUM ('trader', 'risk', 'admin', 'viewer');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'trade_side') THEN
    CREATE TYPE trade_side AS ENUM ('buy', 'sell');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rfq_status') THEN
    CREATE TYPE rfq_status AS ENUM ('pending', 'quoted', 'accepted', 'rejected', 'expired');
  END IF;
END
$$;

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  full_name VARCHAR(120) NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  role user_role NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS clients (
  id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  tier VARCHAR(30) NOT NULL DEFAULT 'standard',
  default_markup_bps DOUBLE PRECISION NOT NULL DEFAULT 2.5,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS instruments (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(30) NOT NULL UNIQUE,
  base_asset VARCHAR(20) NOT NULL,
  quote_asset VARCHAR(20) NOT NULL DEFAULT 'USD',
  tick_size DOUBLE PRECISION NOT NULL DEFAULT 0.01,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS market_prices (
  id BIGSERIAL PRIMARY KEY,
  instrument_id INTEGER NOT NULL REFERENCES instruments(id),
  exchange VARCHAR(30) NOT NULL,
  bid NUMERIC(20, 8) NOT NULL,
  ask NUMERIC(20, 8) NOT NULL,
  mid NUMERIC(20, 8) NOT NULL,
  spread_bps DOUBLE PRECISION NOT NULL,
  rolling_vwap NUMERIC(20, 8) NOT NULL,
  volatility_5m DOUBLE PRECISION NOT NULL,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rfq_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id INTEGER NOT NULL REFERENCES clients(id),
  instrument_id INTEGER NOT NULL REFERENCES instruments(id),
  requested_by_user_id INTEGER NOT NULL REFERENCES users(id),
  side trade_side NOT NULL,
  size NUMERIC(24, 8) NOT NULL,
  quoted_price NUMERIC(24, 8) NOT NULL,
  quote_expiry TIMESTAMPTZ NOT NULL,
  status rfq_status NOT NULL DEFAULT 'quoted',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trades (
  id BIGSERIAL PRIMARY KEY,
  rfq_id UUID NULL REFERENCES rfq_requests(id),
  client_id INTEGER NOT NULL REFERENCES clients(id),
  instrument_id INTEGER NOT NULL REFERENCES instruments(id),
  side trade_side NOT NULL,
  size NUMERIC(24, 8) NOT NULL,
  price NUMERIC(24, 8) NOT NULL,
  notional_usd NUMERIC(24, 8) NOT NULL,
  executed_by_user_id INTEGER NOT NULL REFERENCES users(id),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS positions (
  id BIGSERIAL PRIMARY KEY,
  client_id INTEGER NOT NULL REFERENCES clients(id),
  instrument_id INTEGER NOT NULL REFERENCES instruments(id),
  net_size NUMERIC(24, 8) NOT NULL DEFAULT 0,
  avg_price NUMERIC(24, 8) NOT NULL DEFAULT 0,
  usd_exposure NUMERIC(24, 8) NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_position_client_instrument UNIQUE (client_id, instrument_id)
);

CREATE TABLE IF NOT EXISTS risk_limits (
  id BIGSERIAL PRIMARY KEY,
  client_id INTEGER NULL REFERENCES clients(id),
  instrument_id INTEGER NULL REFERENCES instruments(id),
  soft_limit_usd NUMERIC(24, 8) NOT NULL,
  hard_limit_usd NUMERIC(24, 8) NOT NULL,
  leverage_limit DOUBLE PRECISION NOT NULL DEFAULT 3.0,
  requires_supervisor BOOLEAN NOT NULL DEFAULT TRUE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_limit_client_instrument UNIQUE (client_id, instrument_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  event_type VARCHAR(64) NOT NULL,
  entity_type VARCHAR(64) NOT NULL,
  entity_id VARCHAR(128) NOT NULL,
  user_id INTEGER NULL REFERENCES users(id),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  immutable_hash VARCHAR(128) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);
CREATE INDEX IF NOT EXISTS ix_market_prices_instrument_ts ON market_prices(instrument_id, ts DESC);
CREATE INDEX IF NOT EXISTS ix_rfq_requests_client_created ON rfq_requests(client_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_rfq_requests_status_expiry ON rfq_requests(status, quote_expiry);
CREATE INDEX IF NOT EXISTS ix_trades_client_instrument_ts ON trades(client_id, instrument_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_trades_timestamp ON trades(timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_positions_client_asset ON positions(client_id, instrument_id);
CREATE INDEX IF NOT EXISTS ix_risk_limits_client_asset ON risk_limits(client_id, instrument_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_event_created ON audit_logs(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_logs_entity_created ON audit_logs(entity_type, entity_id, created_at DESC);
