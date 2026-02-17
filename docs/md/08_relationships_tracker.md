# Relationships & Tracker Module Documentation

The `src.relationships` and `src.tracker` modules provide CRM and detailed monitoring capabilities for high-priority targets.

## 1. Target Tracker (`src.tracker`)

Once a company is identified as a potential target, it is moved to the **Target Tracker** for deep-dive monitoring.

### Workflow (`update_tracked_companies`)
Runs on a schedule based on priority:
-   **High Priority**: Checked Daily.
-   **Medium Priority**: Checked every 3 days.
-   **Low Priority**: Checked Weekly.

### Event Detection
The `CompanyEnricher` scans for specific trigger events:
-   **Financial**: Revenue decline, EBITDA margin erosion (distress signals).
-   **Management**: CEO/CFO departures.
-   **News**: "Recall", "Lawsuit", "Strategic Review".

**Alerts**: Critical events generate `TrackingAlert` records which appear in the dashboard notification center.

## 2. Relationship Manager (`src.relationships`)

A lightweight CRM to manage interactions with founders, intermediaries, and investors.

### Key Features
-   **Contact Management**: Store details for individuals linked to Companies or PE Firms.
-   **Interaction Tracking**: Log emails, calls, and meetings.
-   **Email Sync**: (Stub) Workflow to pull recent email interactions via Gmail API.

### Relationship Score
The `RelationshipAnalyzer` calculates a **Strength Score (0-100)** for each contact:
-   **Recency**: Score decays over time if no contact is made.
-   **Frequency**: Regular interactions boost the score.
-   **Depth**: "Meeting" > "Email".

**Follow-up Suggestions**: The system flags contacts with high scores but low recency as "Needs Follow-up".
