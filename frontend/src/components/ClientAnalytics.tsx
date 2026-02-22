import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getClientAnalytics } from "../api";
import type { ClientAnalytics as Analytics, OptionItem } from "../types";

interface Props {
  token: string;
  clients: OptionItem[];
}

export default function ClientAnalytics({ token, clients }: Props) {
  const [selectedClientId, setSelectedClientId] = useState<number | null>(clients[0]?.id ?? null);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!clients.length) {
      setSelectedClientId(null);
      return;
    }

    if (selectedClientId === null || !clients.some((client) => client.id === selectedClientId)) {
      setSelectedClientId(clients[0].id);
    }
  }, [clients, selectedClientId]);

  useEffect(() => {
    if (!selectedClientId) {
      return;
    }

    let cancelled = false;
    setLoading(true);

    getClientAnalytics(token, selectedClientId)
      .then((response) => {
        if (!cancelled) {
          setAnalytics(response);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setAnalytics(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [token, selectedClientId]);

  const chartData = useMemo(() => {
    if (!analytics) {
      return [];
    }

    return [
      { metric: "PnL", value: analytics.mark_to_market_pnl },
      { metric: "Volume", value: analytics.total_volume_usd },
      { metric: "Spread bps", value: analytics.avg_spread_capture_bps },
      { metric: "RFQ Resp (s)", value: analytics.avg_rfq_response_seconds },
    ];
  }, [analytics]);

  return (
    <section className="panel panel-analytics">
      <div className="panel-header">
        <h3>Client Analytics</h3>
        <select
          className="select"
          value={selectedClientId ?? ""}
          onChange={(event) => setSelectedClientId(Number(event.target.value))}
        >
          {clients.map((client) => (
            <option key={client.id} value={client.id}>
              {client.name}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="empty-state">Loading analytics...</div>
      ) : analytics ? (
        <>
          <div className="metric-grid">
            <article className="metric">
              <span>PnL</span>
              <strong>${analytics.mark_to_market_pnl.toLocaleString()}</strong>
            </article>
            <article className="metric">
              <span>Volume</span>
              <strong>${analytics.total_volume_usd.toLocaleString()}</strong>
            </article>
            <article className="metric">
              <span>Spread Capture</span>
              <strong>{analytics.avg_spread_capture_bps.toFixed(2)} bps</strong>
            </article>
            <article className="metric">
              <span>Trades</span>
              <strong>{analytics.trade_count}</strong>
            </article>
          </div>

          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#c3d4da" />
                <XAxis dataKey="metric" tick={{ fill: "#1d3845", fontSize: 12 }} />
                <YAxis tick={{ fill: "#1d3845", fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#d45e23" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      ) : (
        <div className="empty-state">No analytics data</div>
      )}
    </section>
  );
}
