# Web Application & API Documentation

The `src.web` module contains the user interface and REST API for RADAR.

## 1. Backend (`src.web.app`)

Built with **FastAPI**, the backend orchestrates all data retrieval and workflow triggering.

### Key Endpoints

#### Universe
-   `GET /api/universe/companies`: Filterable list of discovered companies. Query params include `is_scored` (true = moat_score > 0, false = moat_score NULL or 0, i.e. unscored or insufficient data).
-   `GET /api/universe/companies/{id}/scoring-history`: Scoring audit trail for a company; response includes `scoring_status` (e.g. `"insufficient_data"` when not scored due to lack of content).
-   `POST /api/universe/scan`: Trigger a new discovery workflow (Background Task).
-   `GET /api/universe/graph`: Returns nodes/links for the relationship graph visualization.

#### Dashboard
-   `GET /api/dashboard/stats`: High-level counters (Total Companies, Active Alerts).
-   `GET /api/dashboard/activity`: Combined feed of recent Events, Deals, and Competitive Threats.

#### Intelligence
-   `GET /api/intelligence/deals`: List PE transactions with multiples.
-   `GET /api/intelligence/deal/{id}`: Detail view with Comparable Analysis.

#### Competitive
-   `GET /api/competitive/feed`: Stream of VC funding announcements.

#### Thesis Validator
-   `GET /api/thesis/config`: Full thesis config (pillars, thresholds).
-   `GET /api/thesis/validate/{company_id}`: Company pillar breakdown, deal screening, scoring history.
-   `GET /api/thesis/leaderboard`: Top companies by moat score.
-   `GET /api/thesis/distribution`: Pillar score distribution across universe.

See **[thesis_validator.md](./thesis_validator.md)** for full documentation.

## 2. Frontend (`src.web.ui`)

The frontend is a **React** Single Page Application (SPA) built with **Vite**.

### Tech Stack
-   **Styling**: Tailwind CSS.
-   **Icons**: Lucide React.
-   **Visualization**: Recharts (Charts), React Force Graph (Network).
-   **State Management**: React Query (Server state), Context API (App state).

### running the App

**Backend**:
```bash
uvicorn src.web.app:app --reload --port 8000
```

**Frontend**:
```bash
cd src/web/ui
npm run dev
```
The UI is available at `http://localhost:5173`.
