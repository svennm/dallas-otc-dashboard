import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Position } from "../types";

interface Props {
  positions: Position[];
}

export default function InventorySnapshot({ positions }: Props) {
  const byInstrument = new Map<string, number>();

  for (const position of positions) {
    byInstrument.set(
      position.instrument_symbol,
      (byInstrument.get(position.instrument_symbol) ?? 0) + Math.abs(position.usd_exposure)
    );
  }

  const chartData = Array.from(byInstrument.entries()).map(([symbol, exposure]) => ({
    symbol,
    exposure: Number(exposure.toFixed(2)),
  }));

  const totalExposure = chartData.reduce((sum, row) => sum + row.exposure, 0);

  return (
    <section className="panel panel-inventory">
      <div className="panel-header">
        <h3>Inventory Snapshot</h3>
        <span className="mono">Total ${totalExposure.toLocaleString()}</span>
      </div>

      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#c3d4da" />
            <XAxis dataKey="symbol" tick={{ fill: "#1d3845", fontSize: 12 }} />
            <YAxis tick={{ fill: "#1d3845", fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="exposure" fill="#0f8f7b" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
