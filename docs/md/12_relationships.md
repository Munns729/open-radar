# Module 5: Relationship Manager - Detailed Specification

## Purpose
The **Relationship Manager** is a lightweight CRM for tracking interactions with founders, intermediaries, and investors. It helps maintain "warm" relationships and identifies optimal timing for outreach.

## Core Capabilities

### 1. Contact Management
Store and organize contacts linked to:
- **Companies** (Founders, executives)
- **Intermediaries** (Advisors, M&A brokers)
- **Investors** (PE/VC partners)

**Fields**:
- Name, title, company, email, phone
- LinkedIn profile URL
- Tags (e.g., "founder", "warm", "gatekeeper")
- Discovery source (e.g., "LinkedIn", "Conference", "Referral")

### 2. Interaction Tracking
Log all touchpoints:

**Interaction Types**:
- Email (sent/received)
- Phone call
- Meeting (in-person or virtual)
- LinkedIn message
- Conference encounter

**Outcomes**:
- POSITIVE (warm response, interest expressed)
- NEUTRAL (acknowledged, no commitment)
- NEGATIVE (rejection, ghosted)
- SCHEDULED (follow-up meeting booked)

### 3. Relationship Scoring
Each contact receives a **Strength Score (0-100)** based on:

**Recency** (40%):
- Score decays over time since last interaction
- Formula: `max(0, 40 - days_since_contact / 2)`

**Frequency** (30%):
- More interactions = higher score
- Formula: `min(30, interaction_count * 3)`

**Depth** (30%):
- Meeting > Call > Email
- Formula: Based on interaction type weights

**Example**:
- 3 meetings in past month: ~85/100 (HOT)
- 2 emails in past 3 months: ~45/100 (WARM)
- 1 email >6 months ago: ~15/100 (COLD)

### 4. Follow-up Suggestions
The `RelationshipAnalyzer` flags contacts needing outreach:

**Criteria**:
- Relationship score >50 (was warm)
- Last contact >90 days ago
- No scheduled follow-up

**Output**: List of contacts to reach out to, sorted by priority.

### 5. Email Sync (Optional)
If Gmail API is configured, the system can:
- Auto-detect emails sent to known contacts
- Create `Interaction` records
- Update `last_contact_date`

**Status**: Currently a stub (requires OAuth setup).

## Database Schema

### `contacts`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | PK |
| `name` | String | Full name |
| `email` | String | Email address |
| `phone` | String | Phone number |
| `title` | String | Job title |
| `company` | String | Company name |
| `company_id` | Integer | FK (optional) to `universe_companies` |
| `linkedin_url` | String | LinkedIn profile |
| `contact_type` | Enum | FOUNDER, INVESTOR, INTERMEDIARY, OTHER |
| `relationship_score` | Integer | 0-100 strength |
| `relationship_strength` | Enum | COLD, WARM, HOT |
| `last_contact_date` | Date | Most recent interaction |
| `discovered_via` | Enum | LINKEDIN, CONFERENCE, REFERRAL, etc. |
| `tags` | JSON | Custom labels |

### `interactions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | PK |
| `contact_id` | Integer | FK to `contacts` |
| `interaction_type` | Enum | EMAIL, CALL, MEETING, LINKEDIN |
| `interaction_date` | Date | When it occurred |
| `subject` | String | Brief summary |
| `notes` | Text | Detailed notes |
| `outcome` | Enum | POSITIVE, NEUTRAL, NEGATIVE, SCHEDULED |

### `network_connections`

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | PK |
| `contact_a_id` | Integer | FK to `contacts` |
| `contact_b_id` | Integer | FK to `contacts` |
| `connection_type` | Enum | INTRODUCED_BY, WORKS_WITH, INVESTED_TOGETHER |
| `strength` | String | "strong", "weak" |

## Workflows

### Daily Relationship Update
```bash
python -m src.relationships.workflow
```

**Process**:
1. Sync emails (if Gmail configured)
2. Recalculate all relationship scores
3. Generate follow-up suggestions
4. Log summary stats

### Manual Logging
```bash
# Via API (see below) or database insert
```

## API Endpoints

### `GET /api/relationships/contacts`
List all contacts with filters.

**Query Params**:
- `contact_type`: Filter by type
- `relationship_strength`: COLD/WARM/HOT
- `company_id`: Filter by associated company
- `search`: Name/company search

**Response**:
```json
[
  {
    "id": 1,
    "name": "Jane Doe",
    "title": "CEO",
    "company": "Acme Ltd",
    "email": "jane@acme.com",
    "relationship_score": 82,
    "relationship_strength": "HOT",
    "last_contact_date": "2024-02-01",
    "interaction_count": 5
  }
]
```

### `POST /api/relationships/contacts`
Create a new contact.

**Body**:
```json
{
  "name": "John Smith",
  "email": "john@example.com",
  "title": "Founder",
  "company": "TechCo",
  "contact_type": "FOUNDER",
  "discovered_via": "LINKEDIN"
}
```

### `POST /api/relationships/interactions`
Log an interaction.

**Body**:
```json
{
  "contact_id": 1,
  "interaction_type": "MEETING",
  "interaction_date": "2024-02-10",
  "subject": "Initial coffee meeting",
  "notes": "Discussed growth plans, open to PE in 12-18 months",
  "outcome": "POSITIVE"
}
```

### `GET /api/relationships/follow-ups`
Get suggested follow-ups.

**Response**:
```json
[
  {
    "contact_id": 5,
    "name": "Alice Brown",
    "company": "HealthTech Inc",
    "relationship_score": 65,
    "days_since_contact": 95,
    "suggested_action": "Check in on Q4 performance"
  }
]
```

### `GET /api/relationships/network`
Get network graph data.

**Description**: Returns nodes (contacts) and edges (connections) for visualization.

## Relationship Analyzer (`src.relationships.analyzer`)

### `calculate_relationship_score(contact_id)`
Recalculates score for a single contact.

### `update_all_relationship_scores()`
Batch update all contacts.

### `suggest_follow_ups(days_threshold=90, min_strength=50)`
Returns list of contacts to reach out to.

### `get_network_stats()`
Returns summary:
- Total contacts
- HOT/WARM/COLD breakdown
- Average interaction frequency

## Testing

```bash
# Unit tests
pytest tests/unit/test_relationships.py

# Integration test
pytest tests/integration/test_relationship_workflow.py

# Manual test
python -m src.relationships.workflow
```

## Gmail Sync Setup (Optional)

1. **Enable Gmail API** in Google Cloud Console
2. **Create OAuth 2.0 Credentials** (Desktop app)
3. **Download** `credentials.json`
4. **Set Environment Variable**:
   ```bash
   GMAIL_CREDENTIALS_PATH=/path/to/credentials.json
   ```
5. **First Run**: Will open browser for OAuth consent
6. **Token Storage**: `token.json` created for future runs

**Dependencies**:
```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

## Future Enhancements
1. **LinkedIn Integration**: Auto-import connections and job changes
2. **Email Templates**: Pre-written outreach messages
3. **Calendar Sync**: Auto-log meetings from Google Calendar
4. **Deal Association**: Link contacts to specific deal opportunities
5. **Sentiment Analysis**: Parse email tone to refine outcome classification
