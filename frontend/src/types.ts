export type Side = "buy" | "sell";

export interface User {
  id: number;
  username: string;
  full_name: string;
  role: "trader" | "risk" | "admin" | "viewer";
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface MarketPrice {
  instrument_id: number;
  instrument_symbol: string;
  bid: number;
  ask: number;
  mid: number;
  spread_bps: number;
  rolling_vwap: number;
  volatility_5m: number;
  ts: string;
}

export interface RFQ {
  id: string;
  client_id: number;
  client_name: string;
  instrument_id: number;
  instrument_symbol: string;
  side: Side;
  size: number;
  quoted_price: number;
  quote_expiry: string;
  status: "pending" | "quoted" | "accepted" | "rejected" | "expired";
  created_at: string;
}

export interface Trade {
  id: number;
  client_id: number;
  client_name: string;
  instrument_id: number;
  instrument_symbol: string;
  side: Side;
  size: number;
  price: number;
  notional_usd: number;
  timestamp: string;
}

export interface TradesPage {
  items: Trade[];
  page: number;
  page_size: number;
  total: number;
}

export interface Position {
  client_id: number;
  client_name: string;
  instrument_id: number;
  instrument_symbol: string;
  net_size: number;
  avg_price: number;
  usd_exposure: number;
  updated_at: string;
}

export interface RiskLimit {
  id: number;
  client_id: number | null;
  client_name: string | null;
  instrument_id: number | null;
  instrument_symbol: string | null;
  soft_limit_usd: number;
  hard_limit_usd: number;
  leverage_limit: number;
  requires_supervisor: boolean;
  active: boolean;
}

export interface RiskAlert {
  client_id: number;
  client_name: string;
  instrument_id: number;
  instrument_symbol: string;
  exposure_usd: number;
  soft_limit_usd: number;
  hard_limit_usd: number;
  severity: "soft" | "hard";
}

export interface ClientAnalytics {
  client_id: number;
  client_name: string;
  mark_to_market_pnl: number;
  total_volume_usd: number;
  avg_spread_capture_bps: number;
  avg_rfq_response_seconds: number;
  trade_count: number;
}

export interface OptionItem {
  id: number;
  name: string;
}
