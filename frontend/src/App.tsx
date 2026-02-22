import { useCallback, useEffect, useMemo, useState } from "react";

import {
  apiBaseUrl,
  createRfq,
  downloadTradesCsv,
  executeTradeFromRfq,
  getCurrentPrices,
  getLimits,
  getPositions,
  getRfqs,
  getRiskAlerts,
  getTrades,
  login,
} from "./api";
import ActiveRfqs from "./components/ActiveRfqs";
import ClientAnalytics from "./components/ClientAnalytics";
import ExposureHeatmap from "./components/ExposureHeatmap";
import InventorySnapshot from "./components/InventorySnapshot";
import LiveMarketGrid from "./components/LiveMarketGrid";
import RFQModal from "./components/RFQModal";
import RiskAlertsPanel from "./components/RiskAlertsPanel";
import TradeBlotter from "./components/TradeBlotter";
import { useWebSocket } from "./hooks/useWebSocket";
import type {
  MarketPrice,
  OptionItem,
  Position,
  RFQ,
  RiskAlert,
  RiskLimit,
  Trade,
  User,
} from "./types";

const wsBase = apiBaseUrl.replace(/^http/, "ws");

function upsertById<T extends { id: string | number }>(rows: T[], item: T): T[] {
  const index = rows.findIndex((row) => row.id === item.id);
  if (index === -1) {
    return [item, ...rows];
  }

  const clone = [...rows];
  clone[index] = item;
  return clone;
}

function upsertByInstrument(rows: MarketPrice[], item: MarketPrice): MarketPrice[] {
  const index = rows.findIndex((row) => row.instrument_id === item.instrument_id);
  if (index === -1) {
    return [...rows, item].sort((a, b) => a.instrument_symbol.localeCompare(b.instrument_symbol));
  }

  const clone = [...rows];
  clone[index] = item;
  return clone;
}

function uniqueOptions(limits: RiskLimit[], key: "client" | "instrument"): OptionItem[] {
  const map = new Map<number, string>();

  for (const limit of limits) {
    if (key === "client" && limit.client_id && limit.client_name) {
      map.set(limit.client_id, limit.client_name);
    }
    if (key === "instrument" && limit.instrument_id && limit.instrument_symbol) {
      map.set(limit.instrument_id, limit.instrument_symbol);
    }
  }

  return Array.from(map.entries())
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem("otc_token"));
  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    const raw = localStorage.getItem("otc_user");
    return raw ? (JSON.parse(raw) as User) : null;
  });

  const [prices, setPrices] = useState<MarketPrice[]>([]);
  const [rfqs, setRfqs] = useState<RFQ[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [limits, setLimits] = useState<RiskLimit[]>([]);
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRfqModal, setShowRfqModal] = useState(false);

  const clients = useMemo(() => uniqueOptions(limits, "client"), [limits]);
  const instruments = useMemo(() => uniqueOptions(limits, "instrument"), [limits]);

  const hydrate = useCallback(async () => {
    if (!token) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const [currentPrices, currentRfqs, currentTrades, currentPositions, currentLimits, currentAlerts] =
        await Promise.all([
          getCurrentPrices(token),
          getRfqs(token),
          getTrades(token),
          getPositions(token),
          getLimits(token),
          getRiskAlerts(token),
        ]);

      setPrices(currentPrices);
      setRfqs(currentRfqs);
      setTrades(currentTrades.items);
      setPositions(currentPositions);
      setLimits(currentLimits);
      setAlerts(currentAlerts.alerts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useWebSocket(
    wsBase,
    "prices",
    token,
    useCallback((message) => {
      const data = message.data as MarketPrice;
      if (!data || typeof data.instrument_id !== "number") {
        return;
      }
      setPrices((prev) => upsertByInstrument(prev, data));
    }, [])
  );

  useWebSocket(
    wsBase,
    "rfq_updates",
    token,
    useCallback((message) => {
      const data = message.data as RFQ;
      if (!data || typeof data.id !== "string") {
        return;
      }
      setRfqs((prev) => upsertById(prev, data));
    }, [])
  );

  useWebSocket(
    wsBase,
    "trade_updates",
    token,
    useCallback((message) => {
      const data = message.data as Trade;
      if (!data || typeof data.id !== "number") {
        return;
      }
      setTrades((prev) => upsertById(prev, data).slice(0, 200));
    }, [])
  );

  useWebSocket(
    wsBase,
    "positions",
    token,
    useCallback(() => {
      void hydrate();
    }, [hydrate])
  );

  const handleLogin = useCallback(
    async (username: string, password: string) => {
      setError(null);
      try {
        const auth = await login(username, password);
        localStorage.setItem("otc_token", auth.access_token);
        localStorage.setItem("otc_user", JSON.stringify(auth.user));
        setToken(auth.access_token);
        setCurrentUser(auth.user);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Authentication failed");
      }
    },
    []
  );

  const handleLogout = useCallback(() => {
    localStorage.removeItem("otc_token");
    localStorage.removeItem("otc_user");
    setToken(null);
    setCurrentUser(null);
    setPrices([]);
    setRfqs([]);
    setTrades([]);
    setPositions([]);
    setLimits([]);
    setAlerts([]);
  }, []);

  const handleCreateRfq = useCallback(
    async (payload: {
      client_id: number;
      instrument_id: number;
      side: "buy" | "sell";
      size: number;
      expiry_seconds: number;
    }) => {
      if (!token) {
        return;
      }
      await createRfq(token, payload);
      await hydrate();
    },
    [token, hydrate]
  );

  const handleExecuteRfq = useCallback(
    async (rfq: RFQ) => {
      if (!token) {
        return;
      }

      try {
        await executeTradeFromRfq(token, {
          rfq_id: rfq.id,
          client_id: rfq.client_id,
          instrument_id: rfq.instrument_id,
          side: rfq.side,
          size: rfq.size,
          price: rfq.quoted_price,
        });
        await hydrate();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to execute RFQ");
      }
    },
    [token, hydrate]
  );

  const handleExportCsv = useCallback(async () => {
    if (!token) {
      return;
    }

    try {
      const blob = await downloadTradesCsv(token);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "trades_export.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to export CSV");
    }
  }, [token]);

  useEffect(() => {
    if (!token) {
      return;
    }

    void hydrate();
    const timer = window.setInterval(() => {
      void hydrate();
    }, 30_000);

    return () => {
      window.clearInterval(timer);
    };
  }, [token, hydrate]);

  if (!token || !currentUser) {
    return <LoginScreen onLogin={handleLogin} error={error} />;
  }

  return (
    <main className="layout">
      <header className="topbar">
        <div>
          <h1>Dallas OTC Crypto Desk Dashboard</h1>
          <p className="subtle">
            Logged in as <strong>{currentUser.full_name}</strong> ({currentUser.role})
          </p>
        </div>

        <div className="topbar-actions">
          <button className="btn btn-secondary" onClick={() => void hydrate()}>
            {loading ? "Refreshing..." : "Refresh"}
          </button>
          <button className="btn btn-ghost" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="dashboard-grid">
        <LiveMarketGrid prices={prices} />

        <ActiveRfqs
          rfqs={rfqs.filter((rfq) => rfq.status === "quoted")}
          onCreate={() => setShowRfqModal(true)}
          onExecute={(rfq) => void handleExecuteRfq(rfq)}
        />

        <InventorySnapshot positions={positions} />

        <TradeBlotter trades={trades} onExportCsv={() => void handleExportCsv()} />

        <ExposureHeatmap positions={positions} clients={clients} instruments={instruments} />

        <RiskAlertsPanel alerts={alerts} />

        <ClientAnalytics token={token} clients={clients} />
      </section>

      <RFQModal
        open={showRfqModal}
        clients={clients}
        instruments={instruments}
        onClose={() => setShowRfqModal(false)}
        onSubmit={handleCreateRfq}
      />
    </main>
  );
}

function LoginScreen({
  onLogin,
  error,
}: {
  onLogin: (username: string, password: string) => void;
  error: string | null;
}) {
  const [username, setUsername] = useState("trader");
  const [password, setPassword] = useState("password123!");

  return (
    <main className="login-layout">
      <section className="login-card">
        <h1>Dallas OTC Desk</h1>
        <p>Institutional RFQ, execution, and exposure control.</p>

        <label>
          Username
          <input className="input" value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>

        <label>
          Password
          <input
            className="input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        {error ? <div className="error-banner">{error}</div> : null}

        <button className="btn btn-primary" onClick={() => onLogin(username, password)}>
          Sign In
        </button>

        <small className="subtle">Default users: admin / trader / risk / viewer</small>
      </section>
    </main>
  );
}
