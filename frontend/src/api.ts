import type {
  AuthResponse,
  ClientAnalytics,
  MarketPrice,
  Position,
  RFQ,
  RiskAlert,
  RiskLimit,
  Side,
  TradesPage,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers ?? {});
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed (${response.status})`);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return (await response.json()) as T;
}

export const apiBaseUrl = API_BASE;

export async function login(username: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function getCurrentPrices(token: string): Promise<MarketPrice[]> {
  return request<MarketPrice[]>("/api/pricing/current", {}, token);
}

export async function getRfqs(token: string): Promise<RFQ[]> {
  return request<RFQ[]>("/api/rfq?active_only=true&limit=200", {}, token);
}

export async function createRfq(
  token: string,
  payload: {
    client_id: number;
    instrument_id: number;
    side: Side;
    size: number;
    expiry_seconds: number;
  }
): Promise<RFQ> {
  return request<RFQ>(
    "/api/rfq",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token
  );
}

export async function executeTradeFromRfq(
  token: string,
  payload: {
    rfq_id: string;
    client_id: number;
    instrument_id: number;
    side: Side;
    size: number;
    price: number;
  }
) {
  return request(
    "/api/trades",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token
  );
}

export async function getTrades(token: string): Promise<TradesPage> {
  return request<TradesPage>("/api/trades?page=1&page_size=200", {}, token);
}

export async function getPositions(token: string): Promise<Position[]> {
  return request<Position[]>("/api/positions", {}, token);
}

export async function getLimits(token: string): Promise<RiskLimit[]> {
  return request<RiskLimit[]>("/api/limits", {}, token);
}

export async function getRiskAlerts(token: string): Promise<{ alerts: RiskAlert[] }> {
  return request<{ alerts: RiskAlert[] }>("/api/limits/alerts", {}, token);
}

export async function getClientAnalytics(token: string, clientId: number): Promise<ClientAnalytics> {
  return request<ClientAnalytics>(`/api/clients/${clientId}/analytics`, {}, token);
}

export async function downloadTradesCsv(token: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/trades/export.csv`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("Unable to download CSV export");
  }

  return response.blob();
}
