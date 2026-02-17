"""
Discovery module for systematic company discovery from multiple sources.

Provides:
- DiscoverySource interface for all data sources
- DeduplicationEngine for multi-stage matching
- RateLimiter for free-tier API management
- SemanticEnrichment for batched LLM analysis
- ManualReviewQueue for edge cases
"""
from .base import (
    DiscoverySource,
    DiscoverySourceType,
    DiscoveredCompany,
    MoatDimension,
    EnrichmentState,
    DeduplicationEngine,
    Match,
    RateLimiter,
    rate_limiter,
    FIELD_REGISTRY,
    SOURCE_PRIORITY,
    resolve_field_conflict,
    compute_input_quality,
)

from .website_finder import (
    find_website_free,
    google_search_website,
    dns_guess_website,
)

from .semantic_enrichment import (
    SemanticScore,
    SemanticEnrichmentResult,
    enrich_batch,
    enrich_companies_batched,
    should_enrich,
    estimate_batch_cost,
)

from .manual_review import (
    ReviewTaskType,
    ReviewStatus,
    ReviewTask,
    queue_for_review,
    queue_website_review,
    queue_merge_review,
    get_pending_reviews,
    complete_review,
    get_review_stats,
)

from .migrations import (
    DISCOVERY_SCHEMA_MIGRATIONS,
    run_migrations,
)

__all__ = [
    # Core types
    "DiscoverySource",
    "DiscoverySourceType",
    "DiscoveredCompany",
    "MoatDimension",
    "EnrichmentState",
    "Match",
    
    # Deduplication
    "DeduplicationEngine",
    
    # Rate limiting
    "RateLimiter",
    "rate_limiter",
    
    # Field registry
    "FIELD_REGISTRY",
    "SOURCE_PRIORITY",
    "resolve_field_conflict",
    "compute_input_quality",
    
    # Website discovery
    "find_website_free",
    "google_search_website",
    "dns_guess_website",
    
    # Semantic enrichment
    "SemanticScore",
    "SemanticEnrichmentResult",
    "enrich_batch",
    "enrich_companies_batched",
    "should_enrich",
    "estimate_batch_cost",
    
    # Manual review
    "ReviewTaskType",
    "ReviewStatus",
    "ReviewTask",
    "queue_for_review",
    "queue_website_review",
    "queue_merge_review",
    "get_pending_reviews",
    "complete_review",
    "get_review_stats",
    
    # Migrations
    "DISCOVERY_SCHEMA_MIGRATIONS",
    "run_migrations",
]
