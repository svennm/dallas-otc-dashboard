# Dallas OTC Crypto Desk Dashboard

Institutional OTC desk dashboard with RFQ workflows, blotter, risk controls, and real-time updates.

## Stack
- Frontend: React + TypeScript + Recharts
- Backend: FastAPI + async WebSockets
- Database: PostgreSQL
- Deployment: Docker Compose

## Quick Start
```bash
docker compose up --build
```

Services:
- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Postgres: localhost:5432

## Default Credentials
- admin / `password123!`
- trader / `password123!`
- risk / `password123!`
- viewer / `password123!`

## Key API Routes
- `POST /api/auth/login`
- `POST /api/rfq`
- `GET /api/rfq/{id}`
- `POST /api/trades`
- `GET /api/trades`
- `GET /api/pricing/current`
- `GET /api/positions`
- `GET /api/clients/{id}/analytics`
- `GET /api/limits`
- `POST /api/limits/override`

## WebSocket Channels
- `prices`
- `positions`
- `rfq_updates`
- `trade_updates`

Connect to:
- `ws://localhost:8000/ws/prices?token=<JWT>`

## Notes
- `backend/sql/schema.sql` includes explicit PostgreSQL DDL and indexes.
- On startup, backend auto-creates tables and seeds sample data.

## Mock Data Script
Generate additional mock RFQs, trades, positions, and market history:

```bash
cd backend
python -m app.scripts.seed_mock_data
```<img width="1740" height="1037" alt="Screenshot 2026-02-22 at 1 26 28 PM" src="https://github.com/user-attachments/assets/5b63156a-01dc-44fb-ba56-738d1ffc93ba" />

