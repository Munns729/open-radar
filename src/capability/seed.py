"""
Idempotent seed for capability levels and signal definitions.
Run on app start (e.g. from scheduler) so tables are populated if empty.
"""
from sqlalchemy import select
from src.core.database import get_async_db
from src.capability.database import CapabilityLevel, CapabilitySignalDefinition


LEVELS = [
    {
        "level": 1,
        "label": "L1 Augmentation",
        "estimated_timeline": "2025–2026",
        "status": "active",
        "investment_implication": "AI as productivity multiplier; human oversight mandatory. Primary diligence question: does this business benefit or suffer from AI-enabled productivity gains?",
    },
    {
        "level": 2,
        "label": "L2 Agentic",
        "estimated_timeline": "2027–2029",
        "status": "active",
        "investment_implication": "Multi-step autonomous workflows at scale. Primary underwriting threshold for 2026 vintage deals: can AI agents replicate the core workflow?",
    },
    {
        "level": 3,
        "label": "L3 Cognitive Parity",
        "estimated_timeline": "2029–2033",
        "status": "active",
        "investment_implication": "AI at or above human expert level across majority of knowledge work. Determines 5-year vs 8-year hold thesis. Professional services moats erode.",
    },
    {
        "level": 4,
        "label": "L4 Physical Integration",
        "estimated_timeline": "2033–2038+",
        "status": "active",
        "investment_implication": "Robotics at commercial scale in unstructured environments. Beyond most exit horizons; informs build-to-sell vs survive-transition thesis.",
    },
]

# signal_key -> (level, weight, label)
SIGNALS = [
    ("l1_reached", 1, 1.0, "L1 baseline established — AI productivity tools mainstream"),
    ("l2_autonomous_multi_system", 2, 0.20, "Autonomous agents operating across 3+ systems without human intervention reported"),
    ("l2_swe_bench_80", 2, 0.15, "SWE-bench score exceeds 80%"),
    ("l2_arc_agi_85", 2, 0.15, "ARC-AGI score exceeds 85%"),
    ("l2_regulated_framework", 2, 0.15, "Regulated industry (finance/healthcare/legal) publishes AI agent deployment framework"),
    ("l2_ai_native_voice_service", 2, 0.10, "AI-native voice customer service deployed at >1M users without human fallback"),
    ("l2_enterprise_headcount_reduction", 2, 0.15, "Enterprise publicly attributes >5% headcount reduction to AI agents"),
    ("l2_continuous_agents_2wk", 2, 0.10, "Continuous AI agents running unsupervised >2 weeks in production publicly reported"),
    ("l3_professional_headcount_20pct", 3, 0.25, "Professional services sector reports >20% headcount reduction attributable to AI"),
    ("l3_ai_coauthorship_100_papers", 3, 0.15, "AI co-authorship credited on >100 peer-reviewed papers per year"),
    ("l3_professional_body_framework", 3, 0.15, "Major professional body (law, medicine, accounting) publishes AI practice framework"),
    ("l3_ai_native_firm_100m", 3, 0.20, "AI-native professional services firm reaches >£100M revenue"),
    ("l3_gpqa_90", 3, 0.10, "GPQA benchmark score exceeds 90%"),
    ("l3_gdp_productivity", 3, 0.15, "GDP-level productivity contribution from AI documented by national statistics body"),
    ("l4_robotics_1000_units", 4, 0.20, "Single robotics deployment of >1,000 units in unstructured commercial environment"),
    ("l4_robot_cost_parity", 4, 0.20, "Robot unit cost reaches parity with annual median wage in target market"),
    ("l4_physical_ai_liability", 4, 0.15, "Physical AI liability framework enacted in EU or UK"),
    ("l4_manufacturing_headcount_10k", 4, 0.20, "Manufacturing firm attributes >10,000 job reductions to robotics publicly"),
    ("l4_ai_drug_discovery", 4, 0.10, "AI-discovered drug or material reaches Phase III trial or commercial production"),
    ("l4_autonomous_construction", 4, 0.15, "Autonomous construction site operates >30 days without human labour"),
]


async def seed_capability_data() -> None:
    """Idempotent seed: insert levels and signal definitions only if they do not exist."""
    async with get_async_db() as session:
        for row in LEVELS:
            existing = await session.execute(
                select(CapabilityLevel).where(CapabilityLevel.level == row["level"])
            )
            if existing.scalar_one_or_none() is not None:
                continue
            session.add(CapabilityLevel(**row))
        await session.flush()

        for signal_key, level, weight, label in SIGNALS:
            existing = await session.execute(
                select(CapabilitySignalDefinition).where(
                    CapabilitySignalDefinition.signal_key == signal_key
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue
            session.add(
                CapabilitySignalDefinition(
                    level=level,
                    signal_key=signal_key,
                    label=label,
                    weight=weight,
                )
            )
        await session.commit()
