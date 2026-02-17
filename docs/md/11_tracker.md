# Module 3: Target Tracker - Detailed Specification

## Purpose
The **Target Tracker** provides continuous monitoring of high-priority investment targets. Once a company passes initial screening (Tier 1A/1B), it is added to the tracker for deep-dive observation of key events that signal deal timing or risks.

## Core Capabilities

### 1. Event Detection
Automatically scans for critical trigger events:

**Financial Events**:
- Revenue decline (>20% QoQ or YoY)
- EBITDA margin compression
- Debt covenant breaches (if public)

**Management Events**:
- CEO/CFO departures
- Board changes
- Ownership transfers

**Operational Events**:
- Product recalls
- Regulatory violations
- Major customer losses

**News & Sentiment**:
- Negative press mentions
- "Strategic review" language
- Lawsuit filings

### 2. Alert Generation
When a critical event is detected, the system:
1. Creates a `TrackingAlert` record
2. Assigns severity (CRITICAL/HIGH/MEDIUM/LOW)
3. Surfaces in the dashboard notification center
4. Optionally triggers email/Slack notifications (future)

### 3. Scheduled Monitoring
Different priority levels have different check frequencies:

| Priority | Check Frequency | Use Case |
|----------|----------------|----------|
| **High** | Daily | Active deal pursuit |
| **Medium** | Every 3 days | Warm leads |
| **Low** | Weekly | Long-term watchlist |

## Database Schema

### `tracked_companies`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | PK |
| `company_id` | Integer | FK to `universe_companies` |
| `tracking_status` | Enum | ACTIVE, PAUSED, CLOSED |
| `priority` | String | high, medium, low |
| `tags` | JSON | Custom categorization |
| `notes` | Text | Internal memo |
| `added_date` | DateTime | When tracking started |
| `last_checked` | DateTime | Last scan timestamp |
| `next_check_due` | DateTime | Scheduled next scan |

### `company_events`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | PK |
| `tracked_company_id` | Integer | FK to `tracked_companies` |
| `event_type` | String | FINANCIAL, MANAGEMENT, NEWS, etc. |
| `severity` | Enum | CRITICAL, HIGH, MEDIUM, LOW, INFO |
| `title` | String | Event headline |
| `description` | Text | Details |
| `detected_date` | DateTime | When detected |
| `source_url` | String | Origin link |

### `tracking_alerts`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | PK |
| `tracked_company_id` | Integer | FK |
| `alert_type` | String | Event category |
| `message` | Text | Alert content |
| `is_read` | Boolean | Read status |
| `created_at` | DateTime | Alert timestamp |

## Workflow

### Adding a Company to Tracker
```bash
python -m src.tracker.workflow add <company_id> --priority high --notes "Strong regulatory moat"
```

**Process**:
1. Check if already tracked (reactivate if closed)
2. Create `TrackedCompany` record
3. Set `next_check_due` to immediate
4. Return tracking ID

### Update Workflow
```bash
python -m src.tracker.workflow update --force
```

**Process** (for each active tracked company):
1. Calculate `since` date (last_checked or 30 days ago)
2. Run `CompanyEnricher.detect_events(company_id, since)`
3. Save new events to database
4. Generate alerts for CRITICAL/HIGH events
5. Update `last_checked` and `next_check_due`

### Event Detection (`CompanyEnricher`)

**Data Sources**:
- **Financial**: Companies House API (UK), SEC Edgar (US/public)
- **Management**: LinkedIn job changes, Companies House officer filings
- **News**: RSS feeds, web mentions

**Detection Rules**:
```python
# Example: CEO departure
if "ceo" in change.role.lower() and change.resigned_on:
    event = CompanyEvent(
        event_type="MANAGEMENT",
        severity=EventSeverity.HIGH,
        title=f"CEO Departure: {change.name}",
        ...
    )
```

## API Endpoints

### `GET /api/tracker/companies`
List all tracked companies with filters.

**Query Params**:
- `priority`: Filter by priority level
- `status`: ACTIVE/PAUSED/CLOSED
- `tags`: Filter by tag

**Response**:
```json
[
  {
    "id": 1,
    "company_id": 42,
    "company_name": "Acme Aerospace Ltd",
    "priority": "high",
    "tags": ["regulatory", "aerospace"],
    "last_checked": "2024-02-10T12:00:00Z",
    "event_count": 3,
    "unread_alerts": 1
  }
]
```

### `POST /api/tracker/companies`
Add a company to tracking.

**Body**:
```json
{
  "company_id": 42,
  "priority": "high",
  "tags": ["moat", "pe-ready"],
  "notes": "Strong AS9100 portfolio"
}
```

### `GET /api/tracker/companies/{tracked_id}/events`
Get events for a specific tracked company.

### `GET /api/tracker/alerts`
Get unread alerts.

## Testing

```bash
# Unit tests
pytest tests/unit/test_tracker.py

# Integration test (requires DB)
pytest tests/integration/test_tracker_workflow.py

# Manual test
python -m src.tracker.workflow add 1 --priority high
python -m src.tracker.workflow update --force
```

## Configuration

**Environment Variables** (in `.env`):
```bash
# Check frequency override (minutes)
TRACKER_HIGH_PRIORITY_INTERVAL=1440  # 24 hours
TRACKER_MEDIUM_PRIORITY_INTERVAL=4320  # 3 days
TRACKER_LOW_PRIORITY_INTERVAL=10080  # 7 days
```

## Future Enhancements
1. **Email/Slack Integration**: Push notifications for critical alerts
2. **Automated Enrichment**: Trigger detailed data updates on high-severity events
3. **Scoring Impact**: Recalculate moat scores when major events occur
4. **Deal Flow Integration**: Auto-create deal records when certain events fire
