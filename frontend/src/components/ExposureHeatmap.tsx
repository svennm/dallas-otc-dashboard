import type { OptionItem, Position } from "../types";

interface Props {
  positions: Position[];
  clients: OptionItem[];
  instruments: OptionItem[];
}

function instrumentName(id: number, instruments: OptionItem[]) {
  const found = instruments.find((instrument) => instrument.id === id);
  return found?.name ?? `Instrument ${id}`;
}

export default function ExposureHeatmap({ positions, clients, instruments }: Props) {
  const matrix = new Map<string, number>();
  let maxExposure = 0;

  for (const position of positions) {
    const key = `${position.client_id}:${position.instrument_id}`;
    const exposure = Math.abs(position.usd_exposure);
    matrix.set(key, exposure);
    maxExposure = Math.max(maxExposure, exposure);
  }

  return (
    <section className="panel panel-heatmap">
      <div className="panel-header">
        <h3>Exposure Heatmap</h3>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Client \ Asset</th>
              {instruments.map((instrument) => (
                <th key={instrument.id}>{instrument.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {clients.map((client) => (
              <tr key={client.id}>
                <td>{client.name}</td>
                {instruments.map((instrument) => {
                  const value = matrix.get(`${client.id}:${instrument.id}`) ?? 0;
                  const ratio = maxExposure > 0 ? value / maxExposure : 0;
                  const alpha = 0.08 + ratio * 0.65;
                  return (
                    <td
                      key={`${client.id}-${instrument.id}`}
                      style={{ background: `rgba(212, 94, 35, ${alpha.toFixed(3)})` }}
                      title={`${client.name} ${instrumentName(instrument.id, instruments)} ${value.toLocaleString()}`}
                    >
                      ${Math.round(value).toLocaleString()}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
