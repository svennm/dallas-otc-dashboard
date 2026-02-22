-- User inserts are intentionally omitted here because bcrypt hashes are generated
-- by application startup seeding (`app/seed.py`) to guarantee valid login credentials.

INSERT INTO clients (name, tier, default_markup_bps)
VALUES
  ('Lone Star Capital', 'gold', 1.8),
  ('Red River Macro', 'silver', 2.4),
  ('Bluebonnet Treasury', 'platinum', 1.2)
ON CONFLICT (name) DO NOTHING;

INSERT INTO instruments (symbol, base_asset, quote_asset, tick_size)
VALUES
  ('BTC-USD', 'BTC', 'USD', 0.01),
  ('ETH-USD', 'ETH', 'USD', 0.01),
  ('SOL-USD', 'SOL', 'USD', 0.01),
  ('ADA-USD', 'ADA', 'USD', 0.0001)
ON CONFLICT (symbol) DO NOTHING;

INSERT INTO risk_limits (client_id, instrument_id, soft_limit_usd, hard_limit_usd, leverage_limit, requires_supervisor, active)
SELECT c.id, i.id, 1500000, 2200000, 3.5, TRUE, TRUE
FROM clients c CROSS JOIN instruments i
ON CONFLICT (client_id, instrument_id) DO NOTHING;

INSERT INTO risk_limits (client_id, instrument_id, soft_limit_usd, hard_limit_usd, leverage_limit, requires_supervisor, active)
SELECT NULL, NULL, 2500000, 4000000, 3.0, TRUE, TRUE
WHERE NOT EXISTS (
  SELECT 1
  FROM risk_limits
  WHERE client_id IS NULL AND instrument_id IS NULL
);
