import { useMemo, useState } from "react";

import type { Trade } from "../types";

interface Props {
  trades: Trade[];
  onExportCsv: () => void;
}

function fmt(value: number, decimals = 2) {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export default function TradeBlotter({ trades, onExportCsv }: Props) {
  const [filter, setFilter] = useState("");

  const visibleTrades = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) {
      return trades;
    }

    return trades.filter((trade) => {
      return (
        trade.client_name.toLowerCase().includes(q) ||
        trade.instrument_symbol.toLowerCase().includes(q) ||
        trade.side.toLowerCase().includes(q)
      );
    });
  }, [trades, filter]);

  return (
    <section className="panel panel-blotter">
      <div className="panel-header">
        <h3>Trade Blotter</h3>
        <div className="inline-controls">
          <input
            className="input"
            placeholder="Filter client / instrument / side"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <button className="btn btn-secondary" onClick={onExportCsv}>
            Export CSV
          </button>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Client</th>
              <th>Instrument</th>
              <th>Side</th>
              <th>Size</th>
              <th>Price</th>
              <th>Notional USD</th>
            </tr>
          </thead>
          <tbody>
            {visibleTrades.length === 0 ? (
              <tr>
                <td colSpan={7} className="empty-cell">
                  No trades found
                </td>
              </tr>
            ) : (
              visibleTrades.map((trade) => (
                <tr key={trade.id}>
                  <td>{new Date(trade.timestamp).toLocaleString()}</td>
                  <td>{trade.client_name}</td>
                  <td>{trade.instrument_symbol}</td>
                  <td>
                    <span className={`chip chip-${trade.side}`}>{trade.side.toUpperCase()}</span>
                  </td>
                  <td>{fmt(trade.size, 4)}</td>
                  <td>${fmt(trade.price, 2)}</td>
                  <td>${fmt(trade.notional_usd, 2)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
