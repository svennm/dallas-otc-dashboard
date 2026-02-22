import type { RiskAlert } from "../types";

interface Props {
  alerts: RiskAlert[];
}

export default function RiskAlertsPanel({ alerts }: Props) {
  return (
    <section className="panel panel-alerts">
      <div className="panel-header">
        <h3>Risk Alerts</h3>
      </div>

      {alerts.length === 0 ? (
        <div className="empty-state">No active risk breaches</div>
      ) : (
        <ul className="alert-list">
          {alerts.map((alert) => (
            <li key={`${alert.client_id}-${alert.instrument_id}`} className={`alert alert-${alert.severity}`}>
              <p>
                <strong>{alert.client_name}</strong> / {alert.instrument_symbol}
              </p>
              <p>
                Exposure ${Math.round(alert.exposure_usd).toLocaleString()} vs soft ${Math.round(
                  alert.soft_limit_usd
                ).toLocaleString()} / hard ${Math.round(alert.hard_limit_usd).toLocaleString()}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
