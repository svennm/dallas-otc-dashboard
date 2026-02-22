import { useEffect, useMemo, useState } from "react";

import type { OptionItem, Side } from "../types";

interface Props {
  open: boolean;
  clients: OptionItem[];
  instruments: OptionItem[];
  onClose: () => void;
  onSubmit: (payload: {
    client_id: number;
    instrument_id: number;
    side: Side;
    size: number;
    expiry_seconds: number;
  }) => Promise<void>;
}

export default function RFQModal({ open, clients, instruments, onClose, onSubmit }: Props) {
  const defaultClient = clients[0]?.id ?? 0;
  const defaultInstrument = instruments[0]?.id ?? 0;

  const [clientId, setClientId] = useState(defaultClient);
  const [instrumentId, setInstrumentId] = useState(defaultInstrument);
  const [side, setSide] = useState<Side>("buy");
  const [size, setSize] = useState(100);
  const [expirySeconds, setExpirySeconds] = useState(20);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!clients.length || !instruments.length) {
      return;
    }
    if (!clients.some((client) => client.id === clientId)) {
      setClientId(clients[0].id);
    }
    if (!instruments.some((instrument) => instrument.id === instrumentId)) {
      setInstrumentId(instruments[0].id);
    }
  }, [clients, instruments, clientId, instrumentId]);

  const canSubmit = useMemo(() => {
    return clientId > 0 && instrumentId > 0 && size > 0 && expirySeconds >= 10 && expirySeconds <= 60;
  }, [clientId, instrumentId, size, expirySeconds]);

  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <header className="panel-header">
          <h3>Create RFQ</h3>
        </header>

        <div className="form-grid">
          <label>
            Client
            <select className="select" value={clientId} onChange={(e) => setClientId(Number(e.target.value))}>
              {clients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Asset
            <select
              className="select"
              value={instrumentId}
              onChange={(e) => setInstrumentId(Number(e.target.value))}
            >
              {instruments.map((instrument) => (
                <option key={instrument.id} value={instrument.id}>
                  {instrument.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Side
            <select className="select" value={side} onChange={(e) => setSide(e.target.value as Side)}>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </label>

          <label>
            Size
            <input
              className="input"
              type="number"
              min={1}
              step={1}
              value={size}
              onChange={(e) => setSize(Number(e.target.value))}
            />
          </label>

          <label>
            Quote Expiry (seconds)
            <input
              className="input"
              type="number"
              min={10}
              max={60}
              step={1}
              value={expirySeconds}
              onChange={(e) => setExpirySeconds(Number(e.target.value))}
            />
          </label>
        </div>

        <footer className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            disabled={!canSubmit || submitting}
            onClick={async () => {
              setSubmitting(true);
              try {
                await onSubmit({
                  client_id: clientId,
                  instrument_id: instrumentId,
                  side,
                  size,
                  expiry_seconds: expirySeconds,
                });
                onClose();
              } finally {
                setSubmitting(false);
              }
            }}
          >
            {submitting ? "Submitting..." : "Quote RFQ"}
          </button>
        </footer>
      </div>
    </div>
  );
}
