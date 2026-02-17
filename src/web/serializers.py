"""Shared serialization helpers for RADAR API routers.

Eliminates hand-rolled ORM-to-dict conversions. Every router should use
these instead of writing inline dict comprehensions.

Usage:
    from src.web.serializers import serialize, serialize_list

    # Single object — explicit fields
    return serialize(company, fields=["id", "name", "sector", "moat_score"])

    # Single object — all columns except internal ones
    return serialize(company, exclude=["_sa_instance_state"])

    # Single object — auto-detect all columns (default)
    return serialize(company)

    # List of objects
    return serialize_list(companies, fields=["id", "name", "sector"])

    # With extra computed fields
    return serialize(company, fields=["id", "name"], extra={"is_hub": True})
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence


def serialize(
    obj: Any,
    fields: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convert an ORM model instance to a JSON-safe dict.

    Args:
        obj: SQLAlchemy model instance.
        fields: Whitelist of field names to include. If None, auto-detects from table columns.
        exclude: Blacklist of field names to skip (only used when fields is None).
        extra: Additional key-value pairs to merge into the result.

    Returns:
        Dict with JSON-safe values (dates → ISO strings, None preserved).
    """
    if fields is None:
        # Auto-detect from SQLAlchemy table columns
        try:
            all_keys = [c.key for c in obj.__class__.__table__.columns]
        except AttributeError:
            # Fallback for non-SQLAlchemy objects
            all_keys = [k for k in obj.__dict__ if not k.startswith("_")]
        exclude_set = set(exclude or [])
        fields = [k for k in all_keys if k not in exclude_set]

    result = {}
    for field in fields:
        val = getattr(obj, field, None)
        if isinstance(val, (date, datetime)):
            val = val.isoformat()
        result[field] = val

    if extra:
        result.update(extra)

    return result


def serialize_list(
    objects: Sequence[Any],
    fields: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Serialize a list of ORM model instances.

    Args:
        objects: Iterable of SQLAlchemy model instances.
        fields: Whitelist of field names (passed to serialize).
        exclude: Blacklist of field names (passed to serialize).

    Returns:
        List of JSON-safe dicts.
    """
    return [serialize(obj, fields=fields, exclude=exclude) for obj in objects]
