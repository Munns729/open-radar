# PROMPT 4: Scoring Audit Trail, Frontend Update & API Endpoint

## Context

You are completing a refactor of the RADAR moat scoring system. Prompts 1, 1B, 2, and 3 are done. The scorer now uses 5 Picard thesis pillars (regulatory, network, geographic, liability, physical), weighted scoring summing to 100, deal screening separated, penalties capped at 20, and full audit metadata in `moat_analysis`. All tests pass.

This prompt adds three things:

1. **ScoringEvent model + Alembic migration** — an audit trail table recording every time a company is scored, what changed, and why.
2. **Change detection in workflow.py** — before scoring overwrites a company's moat_score, snapshot the previous values and create a `ScoringEvent` with a per-pillar diff.
3. **Frontend update** — `MoatBreakdown.jsx` still renders the old 7-pillar taxonomy (including ip, financial, competitive). Update to the 5 thesis pillars with geographic added.
4. **API endpoint** — scoring history for a company, most recent first.

## Files to modify

1. `src/universe/database.py` — add `ScoringEvent` model
2. `src/universe/workflow.py` — add change detection after `score_with_llm()` call
3. `src/universe/moat_scorer.py` — snapshot previous scores before overwriting
4. `src/web/routers/universe.py` — add scoring history endpoint
5. `src/web/ui/src/components/ui/MoatBreakdown.jsx` — update to 5 pillars
6. `src/web/ui/src/components/ui/__tests__/MoatBreakdown.test.jsx` — update tests
7. `alembic/versions/` — generate migration for `scoring_events` table

---

## Part A: New database model — `ScoringEvent`

In `src/universe/database.py`, add the following model **after** the `CompanyRelationshipModel` class and **before** the late-binding relationship block at the bottom:

```python
class ScoringEvent(Base):
    """
    Records each time a company is scored/rescored, enabling audit trail.
    Stores a full snapshot of the scoring result plus a per-pillar diff
    against the previous scoring, so humans can challenge any score.
    """
    __tablename__ = 'scoring_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False, index=True)
    
    # Snapshot of the scoring result
    moat_score = Column(Integer, nullable=False)
    tier = Column(String(10), nullable=False)
    moat_attributes = Column(JSON, nullable=False)
    weights_used = Column(JSON, nullable=False)
    
    # What changed vs. previous scoring
    previous_score = Column(Integer, nullable=True)       # null on first scoring
    score_delta = Column(Integer, nullable=True)           # +/- change
    changes = Column(JSON, nullable=True)                  # Per-pillar diff
    
    # Context
    trigger = Column(String(50), nullable=False, default="rescan")
    scored_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    company = relationship("CompanyModel", backref="scoring_events")

    def __repr__(self):
        return f"<ScoringEvent(company_id={self.company_id}, score={self.moat_score}, delta={self.score_delta})>"
```

The `backref="scoring_events"` on the relationship means `CompanyModel` automatically gets a `scoring_events` attribute — no need to modify `CompanyModel` itself.

**Important**: The `ScoringEvent` model uses `Base` which is imported from `src.core.database`. Since `Base` already has `ToDictMixin`, `ScoringEvent` instances will have `.to_dict()` for API serialisation.

---

## Part B: Snapshot previous scores in `moat_scorer.py`

In `MoatScorer.score_with_llm()`, add two lines at the **very start** of the method, before any other logic. These store the current scores in transient attributes so `workflow.py` can read them after the method overwrites them:

```python
@classmethod
async def score_with_llm(cls, company, certifications, graph_signals=None, raw_website_text=""):
    """Score a company using LLM analysis combined with objective signals."""
    # Snapshot previous scores for audit trail (read by workflow.py after scoring)
    company._previous_moat_score = company.moat_score
    company._previous_moat_attributes = company.moat_attributes
    
    # 1. Gather inputs
    cert_types = [c.certification_type for c in certifications if c.certification_type]
    # ... rest of method unchanged ...
```

These are transient Python attributes (prefixed with `_`), not SQLAlchemy columns. They exist only on the in-memory object and are never persisted to the database. SQLAlchemy ignores them.

---

## Part C: Change detection in `workflow.py`

In `run_scoring_pipeline()`, find the scoring loop (currently around line 245 in the `# 3. Update Scores` section):

```python
    # 3. Update Scores
    for company in companies:
        result = await session.execute(select(CertificationModel).where(CertificationModel.company_id == company.id))
        certs = result.scalars().all()
        
        # Get Graph Signals
        graph_signals = analyzer.get_moat_signals(company.id)
        
        # Score with LLM (Enhanced Deep Logic)
        raw_website_text = company.raw_website_text or ""
        await MoatScorer.score_with_llm(company, certs, graph_signals, raw_website_text)
        await session.commit()
```

Replace with:

```python
    # 3. Update Scores
    from src.universe.database import ScoringEvent
    
    for company in companies:
        result = await session.execute(select(CertificationModel).where(CertificationModel.company_id == company.id))
        certs = result.scalars().all()
        
        # Get Graph Signals
        graph_signals = analyzer.get_moat_signals(company.id)
        
        # Score with LLM (Enhanced Deep Logic)
        raw_website_text = company.raw_website_text or ""
        await MoatScorer.score_with_llm(company, certs, graph_signals, raw_website_text)
        
        # --- Audit Trail: Record ScoringEvent ---
        previous_score = getattr(company, '_previous_moat_score', None)
        previous_attrs = getattr(company, '_previous_moat_attributes', None)
        
        # Compute per-pillar diff
        changes = {}
        for pillar in ["regulatory", "network", "geographic", "liability", "physical"]:
            old_s = (previous_attrs or {}).get(pillar, {}).get("score", 0) if isinstance(previous_attrs, dict) else 0
            new_s = (company.moat_attributes or {}).get(pillar, {}).get("score", 0) if isinstance(company.moat_attributes, dict) else 0
            if old_s != new_s:
                changes[pillar] = {
                    "old": old_s,
                    "new": new_s,
                    "delta": new_s - old_s,
                    "old_justification": (previous_attrs or {}).get(pillar, {}).get("justification", "") if isinstance(previous_attrs, dict) else "",
                    "new_justification": (company.moat_attributes or {}).get(pillar, {}).get("justification", "") if isinstance(company.moat_attributes, dict) else "",
                }
        
        # Determine trigger type
        trigger = "initial" if previous_score is None or previous_score == 0 else "rescan"
        
        event = ScoringEvent(
            company_id=company.id,
            moat_score=company.moat_score,
            tier=company.tier.value if company.tier else "waitlist",
            moat_attributes=company.moat_attributes,
            weights_used=MoatScorer.MOAT_WEIGHTS,
            previous_score=previous_score if previous_score else None,
            score_delta=(company.moat_score - previous_score) if previous_score else None,
            changes=changes if changes else None,
            trigger=trigger,
        )
        session.add(event)
        
        await session.commit()
```

**Note on safety**: The `isinstance(previous_attrs, dict)` checks handle the case where `moat_attributes` was `None` (first-ever scoring) or contained old-format data from before the refactor.

---

## Part D: API endpoint for scoring history

In `src/web/routers/universe.py`, add the following endpoint. Place it after the existing `/companies` endpoint:

```python
@router.get("/companies/{company_id}/scoring-history", summary="Get scoring audit trail")
async def get_scoring_history(
    company_id: int,
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
):
    """
    Return the scoring history for a company, most recent first.
    Each event includes the full pillar breakdown, weights used,
    and a per-pillar diff showing what changed since the previous scoring.
    """
    from src.universe.database import ScoringEvent
    
    # Verify company exists
    company = await session.get(CompanyModel, company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")
    
    stmt = (
        select(ScoringEvent)
        .where(ScoringEvent.company_id == company_id)
        .order_by(desc(ScoringEvent.scored_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    events = result.scalars().all()
    
    return {
        "company_id": company_id,
        "company_name": company.name,
        "current_score": company.moat_score,
        "current_tier": company.tier.value if company.tier else None,
        "total_events": len(events),
        "events": [e.to_dict() for e in events],
    }
```

This uses the `to_dict()` method inherited from `ToDictMixin` on `Base`, which handles datetime serialisation, Decimal conversion, and Enum values automatically.

---

## Part E: Update frontend `MoatBreakdown.jsx`

Replace the entire contents of `src/web/ui/src/components/ui/MoatBreakdown.jsx` with:

```jsx
import React from 'react';
import {
    Lock,
    Network,
    Globe,
    Award,
    Coins,
} from 'lucide-react';

// Only render the 5 Picard thesis moat pillars, in thesis hierarchy order.
// deal_screening, risk_penalty, and any legacy keys are excluded.
const MOAT_PILLARS = ['regulatory', 'network', 'geographic', 'liability', 'physical'];

const icons = {
    regulatory: Lock,
    network: Network,
    geographic: Globe,
    liability: Award,
    physical: Coins,
};

const labels = {
    regulatory: 'Regulatory',
    network: 'Network',
    geographic: 'Geographic',
    liability: 'Liability',
    physical: 'Physical',
};

const colors = {
    regulatory: 'text-blue-400',
    network: 'text-purple-400',
    geographic: 'text-cyan-400',
    liability: 'text-warning',
    physical: 'text-emerald-400',
};

export const MoatBreakdown = ({ attributes }) => {
    if (!attributes) return null;

    return (
        <div className="flex gap-2">
            {MOAT_PILLARS.map((key) => {
                const data = attributes[key];
                if (!data || !data.present || data.score === 0) return null;
                const Icon = icons[key];
                return (
                    <div
                        key={key}
                        className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-alt border border-border-subtle group relative cursor-help"
                        title={`${labels[key]}: ${data.score}% - ${data.justification}`}
                    >
                        <Icon className={`h-3 w-3 ${colors[key]}`} />
                        <span className="text-[10px] font-bold text-text-pri">{data.score}</span>

                        {/* Tooltip on hover */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-48 p-2 bg-surface-alt border border-border-subtle rounded shadow-xl z-50 pointer-events-none">
                            <p className="text-[10px] font-bold text-text-pri mb-1">{labels[key]}</p>
                            <p className="text-[9px] text-text-sec leading-tight">{data.justification}</p>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};
```

Key changes from old version:
- **Removed**: `Shield`, `TrendingUp`, `Target` imports (ip, financial, competitive icons)
- **Added**: `Globe` import (geographic icon)
- **Replaced** `Object.entries(attributes).map()` with `MOAT_PILLARS.map()` — this ensures only the 5 thesis pillars are rendered, ignoring `deal_screening`, `risk_penalty`, and any legacy keys in the data.

---

## Part F: Update frontend test `MoatBreakdown.test.jsx`

Replace the entire contents of `src/web/ui/src/components/ui/__tests__/MoatBreakdown.test.jsx` with:

```jsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MoatBreakdown } from '../MoatBreakdown';

describe('MoatBreakdown Component', () => {
    it('renders nothing when attributes are missing', () => {
        const { container } = render(<MoatBreakdown attributes={null} />);
        expect(container.firstChild).toBeNull();
    });

    it('renders present moat attributes correctly', () => {
        const attributes = {
            regulatory: { present: true, score: 80, justification: 'Has AS9100' },
            network: { present: false, score: 0, justification: '' },
            geographic: { present: true, score: 50, justification: 'SC Cleared UK defence' },
            liability: { present: false, score: 0, justification: '' },
            physical: { present: false, score: 0, justification: '' },
        };

        render(<MoatBreakdown attributes={attributes} />);

        expect(screen.getByText('80')).toBeInTheDocument();
        expect(screen.getByText('50')).toBeInTheDocument();
        expect(screen.getByTitle(/Regulatory: 80%/)).toBeInTheDocument();
        expect(screen.getByTitle(/Geographic: 50%/)).toBeInTheDocument();
    });

    it('hides attributes that are not present or have score 0', () => {
        const attributes = {
            regulatory: { present: false, score: 80, justification: 'Test' },
            network: { present: true, score: 0, justification: 'Test' },
            geographic: { present: false, score: 0, justification: '' },
            liability: { present: true, score: 50, justification: 'Testing Firm' },
            physical: { present: false, score: 0, justification: '' },
        };

        render(<MoatBreakdown attributes={attributes} />);

        expect(screen.queryByText('80')).not.toBeInTheDocument();
        expect(screen.queryByText('0')).not.toBeInTheDocument();
        expect(screen.getByText('50')).toBeInTheDocument();
    });

    it('renders correctly for all 5 thesis moat pillars', () => {
        const attributes = {
            regulatory: { present: true, score: 10, justification: 'R' },
            network: { present: true, score: 20, justification: 'N' },
            geographic: { present: true, score: 30, justification: 'G' },
            liability: { present: true, score: 40, justification: 'L' },
            physical: { present: true, score: 50, justification: 'P' },
        };

        render(<MoatBreakdown attributes={attributes} />);

        expect(screen.getByText('10')).toBeInTheDocument();
        expect(screen.getByText('20')).toBeInTheDocument();
        expect(screen.getByText('30')).toBeInTheDocument();
        expect(screen.getByText('40')).toBeInTheDocument();
        expect(screen.getByText('50')).toBeInTheDocument();
    });

    it('ignores deal_screening and risk_penalty keys', () => {
        const attributes = {
            regulatory: { present: true, score: 70, justification: 'AS9100' },
            network: { present: false, score: 0, justification: '' },
            geographic: { present: false, score: 0, justification: '' },
            liability: { present: false, score: 0, justification: '' },
            physical: { present: false, score: 0, justification: '' },
            deal_screening: {
                financial_fit: { score: 50, factors: ['Revenue fit'] },
                competitive_position: { score: 15, factors: ['Market Leader'] }
            },
            risk_penalty: { present: true, justification: 'administration', score: -10 }
        };

        render(<MoatBreakdown attributes={attributes} />);

        // Only regulatory should render
        expect(screen.getByText('70')).toBeInTheDocument();
        
        // deal_screening and risk_penalty should NOT render as pills
        expect(screen.queryByText('50')).not.toBeInTheDocument();
        expect(screen.queryByText('15')).not.toBeInTheDocument();
        expect(screen.queryByText('-10')).not.toBeInTheDocument();
    });

    it('handles legacy ip/financial/competitive keys gracefully', () => {
        const attributes = {
            regulatory: { present: true, score: 60, justification: 'R' },
            network: { present: false, score: 0, justification: '' },
            geographic: { present: false, score: 0, justification: '' },
            liability: { present: false, score: 0, justification: '' },
            physical: { present: false, score: 0, justification: '' },
            ip: { present: true, score: 45, justification: 'Legacy data' },
            financial: { present: true, score: 30, justification: 'Legacy data' },
            competitive: { present: true, score: 20, justification: 'Legacy data' },
        };

        render(<MoatBreakdown attributes={attributes} />);

        // Only regulatory should render
        expect(screen.getByText('60')).toBeInTheDocument();
        // Legacy keys should NOT render
        expect(screen.queryByText('45')).not.toBeInTheDocument();
        expect(screen.queryByText('30')).not.toBeInTheDocument();
        expect(screen.queryByText('20')).not.toBeInTheDocument();
    });
});
```

Key changes:
- **Removed** all references to `ip`, `financial`, `competitive`
- **Added** `geographic` throughout
- **Added** test for `deal_screening` and `risk_penalty` being ignored
- **Added** test for legacy keys (ip/financial/competitive from old data) being gracefully ignored
- All test data uses the 5 thesis pillars

---

## Part G: Alembic migration

Generate the migration:

```bash
cd investor_radar
alembic revision --autogenerate -m "add_scoring_events_audit_table"
```

Since `ScoringEvent` is defined on `Base` and `alembic/env.py` already imports `from src.universe import database`, autogenerate should detect the new table.

**Verify the generated migration** creates a `scoring_events` table with these columns:
- `id` (Integer, primary_key)
- `company_id` (Integer, ForeignKey to companies.id, index)
- `moat_score` (Integer, not null)
- `tier` (String(10), not null)
- `moat_attributes` (JSON, not null)
- `weights_used` (JSON, not null)
- `previous_score` (Integer, nullable)
- `score_delta` (Integer, nullable)
- `changes` (JSON, nullable)
- `trigger` (String(50), not null)
- `scored_at` (DateTime, not null)

If autogenerate doesn't detect it (unlikely but possible), write the migration manually.

Then apply:

```bash
alembic upgrade head
```

---

## What NOT to change

- Do not modify scoring weights, tier thresholds, or penalty logic in `moat_scorer.py` (beyond adding the 2 snapshot lines).
- Do not modify `llm_moat_analyzer.py`.
- Do not modify `tests/unit/test_moat_scoring.py` or `tests/unit/test_llm_moat_analyzer.py`.
- Do not modify `conftest.py`.
- Do not add new npm dependencies — `lucide-react` already includes `Globe`.

---

## Validation

```bash
# 1. Backend imports
python -c "from src.universe.database import ScoringEvent; print('ScoringEvent model OK')"
python -c "from src.universe.database import CompanyModel; print(hasattr(CompanyModel, 'scoring_events')); print('Backref OK')"

# 2. Migration
alembic upgrade head
python -c "
from src.core.database import sync_engine
from sqlalchemy import inspect
insp = inspect(sync_engine)
tables = insp.get_table_names()
assert 'scoring_events' in tables, f'scoring_events not in {tables}'
cols = [c['name'] for c in insp.get_columns('scoring_events')]
for expected in ['company_id', 'moat_score', 'tier', 'moat_attributes', 'weights_used', 'previous_score', 'score_delta', 'changes', 'trigger', 'scored_at']:
    assert expected in cols, f'Missing column: {expected}'
print(f'scoring_events table OK: {cols}')
"

# 3. API endpoint
python -c "from src.web.routers.universe import router; routes = [r.path for r in router.routes]; assert '/companies/{company_id}/scoring-history' in routes; print('Endpoint registered OK')"

# 4. Frontend build
cd src/web/ui && npm run build

# 5. Frontend tests
cd src/web/ui && npx vitest run src/components/ui/__tests__/MoatBreakdown.test.jsx

# 6. Existing backend tests still pass
cd investor_radar
python -m pytest tests/unit/test_moat_scoring.py -v --tb=short -k "not LLMIntegration"

# 7. Verify no references to old pillars in frontend
grep -rn "\"ip\"\|'ip'\|financial\|competitive\|TrendingUp\|Target\|Shield" src/web/ui/src/components/ui/MoatBreakdown.jsx && echo "FAIL: stale references" || echo "OK: clean"
```

All checks should pass. The frontend build is the most important — it confirms `Globe` is available in `lucide-react` and the JSX compiles without errors.
