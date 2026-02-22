import type { MarketPrice } from "../types";

interface Props {
  prices: MarketPrice[];
}

function fmt(value: number, decimals = 2) {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export default function LiveMarketGrid({ prices }: Props) {
  return (
    <section className="panel panel-market">
      <div className="panel-header">
        <h3>Live Market Grid</h3>
        <span className="tag">WebSocket: prices</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Asset</th>
              <th>Bid</th>
              <th>Ask</th>
              <th>Mid</th>
              <th>Spread (bps)</th>
              <th>VWAP</th>
              <th>Vol 5m</th>
            </tr>
          </thead>
          <tbody>
            {prices.length === 0 ? (
              <tr>
                <td colSpan={7} className="empty-cell">
                  Waiting for market ticks...
                </td>
              </tr>
            ) : (
              prices.map((price) => (
                <tr key={price.instrument_id}>
                  <td>{price.instrument_symbol}</td>
                  <td>{fmt(price.bid, 2)}</td>
                  <td>{fmt(price.ask, 2)}</td>
                  <td>{fmt(price.mid, 2)}</td>
                  <td>{fmt(price.spread_bps, 2)}</td>
                  <td>{fmt(price.rolling_vwap, 2)}</td>
                  <td>{fmt(price.volatility_5m * 100, 2)}%</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
