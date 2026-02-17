"""Response conventions for RADAR API.

This module documents the standard response shapes that all NEW endpoints
should follow. Existing endpoints are grandfathered but should converge
over time.

CONVENTIONS
-----------

1. GET single resource:
   Return the object dict directly.
   Example: {"id": 1, "name": "Acme Corp", "sector": "SaaS"}

2. GET collection (paginated):
   Return: {"data": [...], "total": int, "limit": int, "offset": int}
   Example: {"data": [{...}, {...}], "total": 42, "limit": 20, "offset": 0}

3. GET collection (unpaginated):
   Return: {"data": [...], "total": int}
   Example: {"data": [{...}], "total": 5}

4. POST/PUT/PATCH mutation:
   Return: {"status": "success", "<resource>_id": int, ...}
   Example: {"status": "success", "contact_id": 7, "message": "Contact created"}

5. DELETE:
   Return: {"status": "success", "message": "..."}

6. Background task trigger:
   Return: {"status": "accepted", "message": "..."}

ERRORS
------
All errors use standard FastAPI HTTPException, which returns:
   {"detail": "Human-readable error message"}

STATUS CODES
------------
- 200: Success (GET, PUT, PATCH, DELETE)
- 201: Created (POST) — currently not used, 200 is fine
- 400: Bad request / validation error
- 404: Resource not found
- 500: Internal server error
"""

from typing import Any, Dict, List, Optional


def paginated(data: List[Dict], total: int, limit: int, offset: int) -> Dict[str, Any]:
    """Wrap a list result in a standard paginated envelope."""
    return {
        "status": "success",
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def collection(data: List[Dict]) -> Dict[str, Any]:
    """Wrap an unpaginated list result."""
    return {
        "status": "success",
        "data": data,
        "total": len(data),
    }


def success(message: str = "OK", **extra) -> Dict[str, Any]:
    """Standard mutation response."""
    return {"status": "success", "message": message, **extra}


def accepted(message: str) -> Dict[str, Any]:
    """Standard background task response."""
    return {"status": "accepted", "message": message}
