from typing import Generic, TypeVar, List, Optional, Any
from pydantic import BaseModel, Field

T = TypeVar("T")

class StandardResponse(BaseModel, Generic[T]):
    """Standard API response envelope."""
    status: str = "success"
    data: Optional[T] = None
    message: Optional[str] = None

class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated API response envelope."""
    data: List[T]
    total: int
    limit: int
    offset: int = 0
    status: str = "success"
