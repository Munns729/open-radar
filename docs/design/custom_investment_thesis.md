# Custom Investment Thesis Feature - Design Document

> **Status**: Conceptual Design (Not Implemented)  
> **Created**: February 2026  
> **Purpose**: Enable PE firms to upload custom investment theses that drive personalized company scoring

---

## Overview

Allow users to upload their own investment thesis documents to determine:
1. **What types of companies are collected** (filters & criteria)
2. **How companies are scored** (moat weights, tier thresholds)
3. **Which qualitative factors matter** (custom semantic questions)

---

## Multi-Tenant Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TENANT (PE Firm)                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ Users:  Partner A │ Partner B │ Infra Team Lead        │   │
│   └────────┬──────────┴─────┬─────┴──────────┬─────────────┘   │
│            │                │                │                  │
│   ┌────────▼───────┐ ┌──────▼──────┐ ┌───────▼──────┐          │
│   │ Thesis: "Deep  │ │ Thesis:     │ │ Thesis:      │          │
│   │ Value Indus-   │ │ "Tech-      │ │ "Infra       │          │
│   │ trials 2026"   │ │ Enabled     │ │ Roll-up"     │          │
│   │                │ │ Services"   │ │              │          │
│   └────────────────┘ └─────────────┘ └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

- **Multi-tenant**: Different company instances (PE firms) with isolated data
- **Multi-user per tenant**: Sector teams, different partners
- **Multiple theses per user**: Capture different investment perspectives
- **Companies scored per thesis**: Same company can have different scores under different theses

---

## Core Data Model

```sql
-- Multi-tenant support
tenants (id, name, subdomain, created_at)  -- "Acme Capital", "Alpha PE"

users (id, tenant_id, email, name, role)  -- role: admin, partner, analyst

-- Thesis storage
investment_theses (
    id,
    tenant_id,
    owner_user_id,
    name,                   -- "Deep Value Industrials 2026"
    raw_document_url,       -- S3 path to original PDF/docx
    raw_document_text,      -- Extracted text for re-processing
    
    -- LLM-derived structured config (JSON)
    derived_criteria,       -- {"sectors": ["aerospace", "mfg"], "revenue_range": [10M, 100M], ...}
    compiled_rules,         -- Structured rules DSL (see below)
    
    -- Custom semantic questions
    custom_semantic_questions,  -- JSON array of thesis-specific questions
    
    -- Conversation refinement history
    refinement_history,     -- [{role: "user", content: "..."}, {role: "assistant", ...}]
    
    is_active,              -- Can be archived
    version,                -- For tracking iterations
    created_at,
    updated_at
)

-- Standard semantic enrichment (shared across all theses)
company_semantic_attributes (
    company_id,
    network_effects,            -- 0-10
    network_effects_reason,
    switching_costs,            -- 0-10
    switching_costs_reason,
    value_prop_strength,        -- 0-10
    value_prop_reason,
    customer_dependency,        -- 0-10 (mission-critical?)
    customer_dependency_reason,
    competitive_intensity,      -- 0-10 (crowded market?)
    competitive_intensity_reason,
    revenue_model,              -- "recurring", "transactional", "hybrid"
    customer_type,              -- "enterprise", "smb", "consumer", "gov"
    enrichment_source,
    enriched_at,
    enrichment_version
)

-- Thesis-specific custom answers
company_thesis_custom_attributes (
    company_id,
    thesis_id,
    question_id,        -- "founder_dependency"
    score,              -- 0-10
    justification,      -- "Founder is 68, has mentioned succession planning..."
    enriched_at
)

-- Link companies to which thesis scored them
company_thesis_scores (
    id,
    company_id,
    thesis_id,
    moat_score,             -- Score under THIS thesis
    tier,                   -- Tier under THIS thesis  
    moat_attributes,        -- JSON: justifications under this thesis
    
    -- Data quality tracking
    rules_evaluated,        -- How many rules could run
    rules_skipped,          -- How many skipped due to missing data
    missing_fields,         -- JSON array: ["revenue_gbp", "ebitda_margin"]
    data_completeness,      -- 0.0 - 1.0
    is_provisional,         -- True if completeness < threshold
    
    scored_at
)
```

---

## Two-Phase Architecture

### Phase 1: Thesis → Rules (LLM)

```
┌────────────────────────────────────────────────────────────────────────┐
│                    THESIS CREATION FLOW                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  1. Partner uploads PDF: "2026 Industrial Services Thesis.pdf"        │
│                              │                                         │
│                              ▼                                         │
│  2. LLM extracts criteria:                                            │
│     ┌────────────────────────────────────────────────────────┐        │
│     │ Prompt: "Extract investment criteria from this thesis  │        │
│     │ document. Identify: target sectors, revenue range,     │        │
│     │ geographic focus, moat priorities, deal-breakers..."   │        │
│     └────────────────────────────────────────────────────────┘        │
│                              │                                         │
│                              ▼                                         │
│  3. LLM returns structured output:                                    │
│     {                                                                  │
│       "target_sectors": ["industrial_services", "facilities_mgmt"],   │
│       "revenue_range_gbp": [15_000_000, 80_000_000],                  │
│       "moat_priorities": [                                            │
│         {"type": "regulatory", "importance": "critical"},             │
│         {"type": "recurring_revenue", "importance": "high"}           │
│       ],                                                              │
│       "dealbreakers": ["high_customer_concentration", "cyclical"]     │
│     }                                                                  │
│                              │                                         │
│                              ▼                                         │
│  4. Partner refines via chat:                                         │
│     User: "We actually care about manufacturing MORE than services"   │
│     LLM: "Updated. Manufacturing now weighted 1.5x vs services."      │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Phase 2: Rules → Scores (Deterministic)

```
┌────────────────────────────────────────────────────────────────────────┐
│                 RULES EXECUTION (Deterministic)                        │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Batch job / on-demand trigger                                        │
│            │                                                           │
│            ▼                                                           │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ RulesEngine.score_batch(thesis, companies)                      │   │
│  │                                                                 │   │
│  │ for company in companies:                                       │   │
│  │     if not passes_filters(company, thesis.filters):             │   │
│  │         continue  # Out of scope                                │   │
│  │                                                                 │   │
│  │     score = 0                                                   │   │
│  │     moat_attrs = {}                                             │   │
│  │     for rule in thesis.scoring_rules:                           │   │
│  │         if evaluate(rule.condition, company):                   │   │
│  │             score += rule.points                                │   │
│  │             moat_attrs[rule.moat] = True                        │   │
│  │                                                                 │   │
│  │     tier = assign_tier(score, moat_attrs, thesis.tier_thresholds)│  │
│  │     save(CompanyThesisScore(company, thesis, score, tier))      │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ✓ No LLM calls during scoring                                        │
│  ✓ Fully deterministic & reproducible                                 │
│  ✓ Can score 10,000+ companies in seconds                             │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Rules DSL (Domain-Specific Language)

The LLM outputs rules in a structured format the engine can execute:

```python
CONDITION_GRAMMAR = {
    # Field comparisons
    "field_gt":       {"field": str, "value": number},     # revenue_gbp > 15000000
    "field_lt":       {"field": str, "value": number},
    "field_between":  {"field": str, "min": number, "max": number},
    "field_in":       {"field": str, "values": list},      # sector in ["aero", "mfg"]
    "field_contains": {"field": str, "substring": str},    # description contains "platform"
    
    # Certification checks
    "has_cert":       {"cert_type": str},                  # has_cert("AS9100")
    "has_any_cert":   {"cert_types": list},
    
    # Semantic attribute checks
    "semantic_gte":   {"field": str, "value": number},     # semantic_network_effects >= 7
    "custom_field":   {"question_id": str, "op": str, "value": number},
    
    # Composite conditions
    "and":            {"conditions": list},
    "or":             {"conditions": list},
    "not":            {"condition": dict}
}
```

### Example Compiled Rule

```json
{
  "id": "reg_moat_aerospace",
  "requires_fields": ["certifications", "sector"],
  "condition": {
    "and": [
      {"type": "has_any_cert", "cert_types": ["AS9100", "Part145"]},
      {"type": "field_in", "field": "sector", "values": ["aerospace", "defence"]}
    ]
  },
  "points": 35,
  "moat_type": "regulatory",
  "justification_template": "Holds {matched_certs} in regulated {sector} sector"
}
```

---

## Thesis Completeness Validation

Before a thesis is marked "active", run completeness checks:

```python
class ThesisValidator:
    REQUIRED_ELEMENTS = [
        ("revenue_range", "What revenue range are you targeting? (e.g., £15M-100M)"),
        ("geography", "Which geographies are in scope?"),
        ("sectors", "Which sectors are you focused on?"),
        ("moat_priorities", "What moat characteristics matter most?"),
        ("tier_criteria", "What distinguishes a Tier 1A from 1B opportunity?"),
    ]
    
    def validate(self, thesis: InvestmentThesis) -> ValidationResult:
        missing = []
        for element, prompt_question in self.REQUIRED_ELEMENTS:
            if not thesis.compiled_rules.get(element):
                missing.append({
                    "element": element,
                    "question": prompt_question
                })
        
        return ValidationResult(
            is_complete=len(missing) == 0,
            missing_elements=missing,
            completeness_score=len(self.REQUIRED_ELEMENTS) - len(missing)
        )
```

### UI Flow for Completeness

```
┌─────────────────────────────────────────────────────────────┐
│  Thesis: "Industrial Services 2026"       [72% Complete]    │
├─────────────────────────────────────────────────────────────┤
│  ✓ Revenue range defined: £20M - £80M                       │
│  ✓ Sectors: industrial services, facilities management      │
│  ✓ Moat priorities: recurring revenue, regulatory           │
│  ⚠ Missing: Geographic focus                                │
│  ⚠ Missing: Tier 1A vs 1B criteria                          │
│                                                             │
│  [Chat to refine] "What geographies should we focus on?"    │
│  ─────────────────────────────────────────────────────────  │
│  Partner: "UK and Ireland primarily, Germany for scale"     │
│  AI: "Updated. Added UK, IE as primary; DE as secondary.    │
│       Companies in DE will receive 0.8x geography modifier" │
└─────────────────────────────────────────────────────────────┘
```

---

## Graceful Failure for Missing Data

### Rule-Level Data Requirements

Each rule declares what fields it needs. If those fields are null/missing, the rule is **skipped** (not failed):

```json
{
  "id": "revenue_sweet_spot",
  "requires_fields": ["revenue_gbp"],
  "condition": {"type": "field_between", "field": "revenue_gbp", "min": 15000000, "max": 100000000},
  "points": 25,
  "moat_type": "scale"
}
```

### Rules Engine with Graceful Skip

```python
class RulesEngine:
    def score(self, company: Company) -> CompanyThesisScore:
        score = 0
        moat_attrs = {}
        rules_evaluated = 0
        rules_skipped = 0
        missing_fields = set()
        
        for rule in self.thesis.scoring_rules:
            # Check data availability
            missing = self._get_missing_fields(company, rule.requires_fields)
            
            if missing:
                rules_skipped += 1
                missing_fields.update(missing)
                continue  # Skip this rule gracefully
            
            # Evaluate rule
            rules_evaluated += 1
            if self._evaluate_condition(rule.condition, company):
                score += rule.points
                moat_attrs[rule.moat_type] = MoatResult(
                    present=True,
                    justification=self._render_justification(rule, company)
                )
        
        total_rules = rules_evaluated + rules_skipped
        completeness = rules_evaluated / total_rules if total_rules > 0 else 0
        
        return CompanyThesisScore(
            score=score,
            tier=self._assign_tier(score, moat_attrs),
            data_completeness=completeness,
            is_provisional=completeness < 0.7,
            missing_fields=list(missing_fields),
            rules_evaluated=rules_evaluated,
            rules_skipped=rules_skipped
        )
```

### Filter Behavior Options

| Strategy | Behavior | Use When |
|----------|----------|----------|
| **Exclude if missing** | No revenue_gbp → excluded from results | Strict scope enforcement |
| **Include if missing** | No revenue_gbp → still included, marked | Discovery/completeness focus |
| **Configurable per filter** | Thesis author chooses | Maximum flexibility |

```json
{
  "filters": [
    {
      "field": "revenue_gbp",
      "op": "between",
      "values": [15000000, 100000000],
      "on_missing": "include"  // or "exclude"
    }
  ]
}
```

### UI: Data Quality Indicators

**In company list:**
```
┌─────────────────────────────────────────────────────────────────────┐
│ Company              │ Score │ Tier │ Moats       │ Data Quality   │
├──────────────────────┼───────┼──────┼─────────────┼────────────────┤
│ Acme Aerospace       │ 78    │ 1A   │ 🛡️ 🔗        │ ████████░░ 85% │
│ Beta Manufacturing   │ 62*   │ 1B   │ 🏭          │ ███████░░░ 70% │  ← provisional
│ Gamma Services       │ 45*   │ 2    │ 📋          │ ████░░░░░░ 40% │  ← low confidence
└─────────────────────────────────────────────────────────────────────┘
                                         * provisional score
```

**In company detail:**
```
┌─────────────────────────────────────────────────────────────────────┐
│ Beta Manufacturing                              Score: 62 (Tier 1B) │
├─────────────────────────────────────────────────────────────────────┤
│ ⚠️ Provisional Score                                                │
│ 3 of 10 scoring rules could not be evaluated due to missing data:  │
│                                                                     │
│ • Revenue growth (affects: Growth Momentum rule)                    │
│ • EBITDA margin (affects: Profitability rule)                       │
│ • Customer concentration (affects: Revenue Quality rule)            │
│                                                                     │
│ [Enrich company data] to improve score accuracy                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Gap Report

```
┌─────────────────────────────────────────────────────────────────────┐
│ Data Completeness Report for "Industrial Thesis 2026"               │
├─────────────────────────────────────────────────────────────────────┤
│ Field               │ Populated │ Missing │ Impact on Scoring       │
├─────────────────────┼───────────┼─────────┼─────────────────────────┤
│ revenue_gbp         │ 847 (92%) │ 73      │ Affects 3 rules (35 pts)│
│ ebitda_margin       │ 412 (45%) │ 508     │ Affects 2 rules (20 pts)│
│ certifications      │ 623 (68%) │ 297     │ Affects 4 rules (50 pts)│
│ customer_conc       │ 89 (10%)  │ 831     │ Affects 1 rule (10 pts) │
├─────────────────────┴───────────┴─────────┴─────────────────────────┤
│ [Prioritize enrichment for ebitda_margin – high impact, low coverage]│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Qualitative/"Vibes" Scoring via Semantic Enrichment

### The Challenge

Some attributes can't be reduced to `field > threshold`:
- Network effects
- Value proposition strength
- Switching costs
- Founder dependency

### The Solution: Pre-compute Semantic Attributes

Run LLM analysis **once per company** (not per thesis) to extract qualitative attributes as structured fields:

```
┌────────────────────────────────────────────────────────────────┐
│              COMPANY ENRICHMENT PIPELINE                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Raw Company Data                                              │
│  ├─ name: "Acme Connect"                                       │
│  ├─ description: "B2B marketplace connecting suppliers..."    │
│  ├─ website_text: (scraped)                                    │
│  └─ certifications: [...]                                      │
│                          │                                     │
│                          ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ LLM Semantic Enrichment (run once, cached)               │ │
│  │                                                          │ │
│  │ Prompt: "Analyze this company and assess:                │ │
│  │ 1. Network effects (0-10): Two-sided? Lock-in?           │ │
│  │ 2. Value prop strength (0-10): Differentiation?          │ │
│  │ 3. Switching costs (0-10): Integration depth?            │ │
│  │ 4. Customer dependency (0-10): Mission-critical?         │ │
│  │                                                          │ │
│  │ Return scores with one-sentence justifications."         │ │
│  └──────────────────────────────────────────────────────────┘ │
│                          │                                     │
│                          ▼                                     │
│  Enriched Company Data (stored in DB)                         │
│  ├─ ... original fields ...                                   │
│  ├─ semantic_network_effects: 8                                │
│  ├─ semantic_network_effects_reason: "Two-sided B2B..."       │
│  ├─ semantic_value_prop: 7                                    │
│  ├─ semantic_value_prop_reason: "Unique data asset..."        │
│  ├─ semantic_switching_costs: 6                               │
│  └─ semantic_last_enriched: 2026-02-03                        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

Now the **rules engine remains deterministic**:

```json
{
  "id": "strong_network_effects",
  "requires_fields": ["semantic_network_effects"],
  "condition": {"type": "field_gte", "field": "semantic_network_effects", "value": 7},
  "points": 25,
  "moat_type": "network"
}
```

### When to Re-enrich

| Trigger | Action |
|---------|--------|
| New company added | Enrich immediately or queue |
| Company data updated (description, website) | Re-enrich |
| Enrichment older than X days | Re-enrich on next batch |
| User requests "refresh analysis" | Re-enrich single company |
| New attributes needed by thesis | Batch re-enrich missing fields |

### UI: Show the "Why" Behind Vibes Scores

```
┌─────────────────────────────────────────────────────────────────┐
│ Acme Connect                                                    │
├─────────────────────────────────────────────────────────────────┤
│ Qualitative Assessment (AI-analyzed Feb 3, 2026)               │
│                                                                 │
│ Network Effects        ████████░░ 8/10                         │
│ └─ "Two-sided B2B marketplace with growing supplier base.       │
│     Buyers locked in via integrated procurement workflows."     │
│                                                                 │
│ Value Proposition      ███████░░░ 7/10                         │
│ └─ "Unique aggregated supplier data creates switching costs.    │
│     Competitors would need years to replicate relationships."   │
│                                                                 │
│ Switching Costs        ██████░░░░ 6/10                         │
│ └─ "ERP integrations create moderate lock-in, but standard      │
│     APIs mean migration is feasible for determined buyers."     │
│                                                                 │
│ [🔄 Refresh Analysis]                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Custom Semantic Questions

### Thesis-Specific Questions

Different investment theses may care about **different qualitative questions** not in the standard set:

**Thesis A: "Industrial Roll-up Strategy"**
```yaml
custom_semantic_questions:
  - id: "founder_dependency"
    question: "How dependent is this business on the founder? (0-10)"
    context: "We need owner-operators ready to exit, not lifestyle businesses"
    
  - id: "integration_complexity"  
    question: "How complex would it be to integrate this into a platform? (0-10)"
    context: "Assess ERP, back-office, and operational overlap potential"
```

**Thesis B: "Tech-Enabled Services"**
```yaml
custom_semantic_questions:
  - id: "automation_potential"
    question: "How much of their service delivery could be automated with AI/software? (0-10)"
    context: "We want 'software eating services' opportunities"
    
  - id: "data_asset_value"
    question: "Do they have proprietary data that creates a moat? (0-10)"
    context: "Looking for companies sitting on valuable data they haven't monetized"
```

### How Custom Questions Work

```python
async def enrich_company_for_thesis(company: Company, thesis: InvestmentThesis):
    # Standard semantic enrichment (shared)
    standard_prompt = build_standard_enrichment_prompt(company)
    standard_results = await llm.analyze(standard_prompt)
    
    # Thesis-specific custom questions
    if thesis.custom_semantic_questions:
        custom_prompt = f"""
        Analyze this company:
        {company.description}
        {company.website_text}
        
        Answer these specific questions from the investment thesis:
        {format_custom_questions(thesis.custom_semantic_questions)}
        
        Return scores 0-10 with justifications.
        """
        custom_results = await llm.analyze(custom_prompt)
        
        # Store in thesis-specific enrichment table
        await save_thesis_enrichment(company.id, thesis.id, custom_results)
```

### Rules Reference Custom Attributes

```json
{
  "id": "founder_ready_to_exit",
  "requires_fields": ["custom:founder_dependency"],
  "condition": {
    "type": "custom_field_lte",
    "question_id": "founder_dependency", 
    "value": 4
  },
  "points": 15,
  "moat_type": null,
  "justification_template": "Low founder dependency suggests smooth transition potential"
}
```

### UI: Thesis Author Defines Custom Questions

```
┌─────────────────────────────────────────────────────────────────────┐
│ Thesis: "Industrial Roll-up 2026"                                   │
├─────────────────────────────────────────────────────────────────────┤
│ Custom Scoring Questions                                            │
│                                                                     │
│ The AI will analyze each company to answer these questions:        │
│                                                                     │
│ 1. Founder Dependency                                               │
│    "How dependent is this business on the founder?"                 │
│    Context: We need owner-operators ready to exit                  │
│    [Edit] [Delete]                                                  │
│                                                                     │
│ 2. Integration Complexity                                           │
│    "How complex would platform integration be?"                     │
│    Context: Assess ERP and operational overlap                     │
│    [Edit] [Delete]                                                  │
│                                                                     │
│ [+ Add custom question]                                             │
│                                                                     │
│ ⚠️ Adding custom questions requires re-enriching 920 companies      │
│    Estimated cost: ~$18 | Time: ~15 minutes                         │
│    [Queue enrichment]                                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Batch Scoring Job

```python
async def batch_rescore_thesis(thesis_id: int):
    """Background job to re-score all companies under a thesis."""
    thesis = await get_thesis(thesis_id)
    companies = await get_companies_for_tenant(thesis.tenant_id)
    
    engine = RulesEngine(thesis.compiled_rules)
    
    # Clear old scores for this thesis
    await clear_scores_for_thesis(thesis_id)
    
    # Score in batches
    batch_size = 500
    for batch in chunked(companies, batch_size):
        scores = [engine.score(company) for company in batch]
        await bulk_insert_scores(scores)
    
    # Mark thesis as scored
    await update_thesis(thesis_id, last_scored_at=datetime.now())
```

**Triggering:**
- Manual: "Re-score universe" button
- Automatic: After thesis refinement conversation ends
- Scheduled: Nightly for active theses (if company data changes)

---

## Key Design Decisions Summary

| Aspect | Decision |
|--------|----------|
| **LLM's role** | Generates rules + enriches companies. Does NOT score directly. |
| **Scoring** | Deterministic rules engine. Fast, reproducible, auditable. |
| **Qualitative factors** | Pre-computed semantic attributes (0-10 scores with justifications). |
| **Custom questions** | Thesis authors can define their own semantic questions. |
| **Missing data** | Rules skipped gracefully. Score marked "provisional" if completeness < threshold. |
| **Company ↔ Thesis** | Many-to-many. Same company has different scores under different theses. |
| **Thesis completeness** | Validated before activation. Missing elements prompt user. |
| **Batch scoring** | On thesis creation/update, or scheduled. Not real-time per company. |

---

## Cost Estimates

| Operation | Frequency | Cost |
|-----------|-----------|------|
| Thesis parsing | Once per thesis upload | ~$0.05-0.10 |
| Thesis refinement | Per conversation turn | ~$0.02-0.05 |
| Standard semantic enrichment | Once per company | ~$0.01-0.05 |
| Custom question enrichment | Per (company, thesis) pair | ~$0.005-0.02 |
| Batch scoring | Per scoring run | Negligible (no LLM) |

---

## Future Considerations

1. **Sharing theses**: Optional visibility (private, team, tenant-wide)
2. **Thesis templates**: Pre-built theses for common strategies
3. **Score history**: Track how a company's score evolves over time
4. **Thesis comparison**: Side-by-side view of same company under different theses
5. **LLM model versioning**: Track which model version was used for enrichment
