import { useEffect, useState } from "react";

import type { RFQ } from "../types";

interface Props {
  rfqs: RFQ[];
  onCreate: () => void;
  onExecute: (rfq: RFQ) => void;
}

export default function ActiveRfqs({ rfqs, onCreate, onExecute }: Props) {
  const [clock, setClock] = useState(Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <section className="panel panel-rfqs">
      <div className="panel-header">
        <h3>Active RFQs</h3>
        <button className="btn btn-primary" onClick={onCreate}>
          New RFQ
        </button>
      </div>

      <div className="rfq-list">
        {rfqs.length === 0 ? (
          <div className="empty-state">No active RFQs</div>
        ) : (
          rfqs.map((rfq) => {
            const secondsLeft = Math.max(
              0,
              Math.floor((new Date(rfq.quote_expiry).getTime() - clock) / 1000)
            );

            return (
              <article key={rfq.id} className="rfq-card">
                <header>
                  <strong>{rfq.instrument_symbol}</strong>
                  <span className={`chip chip-${rfq.side}`}>{rfq.side.toUpperCase()}</span>
                </header>
                <p>{rfq.client_name}</p>
                <p>
                  Size: <strong>{rfq.size.toLocaleString()}</strong>
                </p>
                <p>
                  Quote: <strong>${rfq.quoted_price.toLocaleString()}</strong>
                </p>
                <footer>
                  <span className={secondsLeft < 10 ? "timer timer-warning" : "timer"}>
                    {secondsLeft}s
                  </span>
                  <button
                    className="btn btn-secondary"
                    disabled={rfq.status !== "quoted" || secondsLeft === 0}
                    onClick={() => onExecute(rfq)}
                  >
                    Execute
                  </button>
                </footer>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}
