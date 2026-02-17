"""
Manual Review Queue for edge cases.

Handles:
- Website not found for high-priority companies
- Ambiguous deduplication matches
- Missing critical data
"""
import logging
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ReviewTaskType(Enum):
    """Types of manual review tasks."""
    FIND_WEBSITE = "find_website"
    CONFIRM_MERGE = "confirm_merge"
    VALIDATE_SECTOR = "validate_sector"
    VALIDATE_DATA = "validate_data"


class ReviewStatus(Enum):
    """Status of a review task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class ReviewTask:
    """A manual review task."""
    id: int
    company_id: int
    company_name: str
    task_type: ReviewTaskType
    priority: int  # Higher = more important
    context: dict  # Additional context for reviewer
    status: ReviewStatus
    created_at: datetime
    assigned_to: Optional[str] = None
    completed_at: Optional[datetime] = None
    resolution: Optional[str] = None


def queue_for_review(
    db: Session,
    company_id: int,
    task_type: ReviewTaskType,
    priority: int = 5,
    context: Optional[dict] = None,
) -> int:
    """
    Add a company to the manual review queue.
    
    Args:
        db: Database session
        company_id: ID of company needing review
        task_type: Type of review needed
        priority: 1-10, higher = more important
        context: Additional context (e.g., potential merge candidates)
        
    Returns:
        Review task ID
    """
    import json
    
    result = db.execute(
        text("""
            INSERT INTO manual_review_queue 
            (company_id, task_type, priority, context, status, created_at)
            VALUES (:company_id, :task_type, :priority, :context, :status, :created_at)
            RETURNING id
        """),
        {
            "company_id": company_id,
            "task_type": task_type.value,
            "priority": priority,
            "context": json.dumps(context or {}),
            "status": ReviewStatus.PENDING.value,
            "created_at": datetime.utcnow(),
        }
    )
    db.commit()
    
    task_id = result.fetchone()[0]
    logger.info(f"Queued review task {task_id}: {task_type.value} for company {company_id}")
    return task_id


def queue_website_review(
    db: Session,
    company_id: int,
    company_name: str,
    country: str,
    passed_thesis_filter: bool = False,
) -> int:
    """Queue a company for website discovery review."""
    priority = 8 if passed_thesis_filter else 3
    
    return queue_for_review(
        db=db,
        company_id=company_id,
        task_type=ReviewTaskType.FIND_WEBSITE,
        priority=priority,
        context={
            "company_name": company_name,
            "country": country,
            "passed_thesis_filter": passed_thesis_filter,
        },
    )


def queue_merge_review(
    db: Session,
    company_a_id: int,
    company_b_id: int,
    confidence: float,
    match_method: str,
) -> int:
    """Queue two companies for merge confirmation."""
    return queue_for_review(
        db=db,
        company_id=company_a_id,
        task_type=ReviewTaskType.CONFIRM_MERGE,
        priority=7,
        context={
            "other_company_id": company_b_id,
            "confidence": confidence,
            "match_method": match_method,
        },
    )


def get_pending_reviews(
    db: Session,
    task_type: Optional[ReviewTaskType] = None,
    limit: int = 50,
) -> List[ReviewTask]:
    """Get pending review tasks, ordered by priority."""
    import json
    
    query = """
        SELECT r.id, r.company_id, c.name, r.task_type, r.priority, 
               r.context, r.status, r.created_at, r.assigned_to, r.completed_at
        FROM manual_review_queue r
        JOIN companies c ON r.company_id = c.id
        WHERE r.status = :status
    """
    params = {"status": ReviewStatus.PENDING.value}
    
    if task_type:
        query += " AND r.task_type = :task_type"
        params["task_type"] = task_type.value
    
    query += " ORDER BY r.priority DESC, r.created_at ASC LIMIT :limit"
    params["limit"] = limit
    
    results = db.execute(text(query), params).fetchall()
    
    return [
        ReviewTask(
            id=r[0],
            company_id=r[1],
            company_name=r[2],
            task_type=ReviewTaskType(r[3]),
            priority=r[4],
            context=json.loads(r[5]) if r[5] else {},
            status=ReviewStatus(r[6]),
            created_at=r[7],
            assigned_to=r[8],
            completed_at=r[9],
        )
        for r in results
    ]


def complete_review(
    db: Session,
    task_id: int,
    resolution: str,
    data_updates: Optional[dict] = None,
) -> None:
    """
    Mark a review task as complete.
    
    Args:
        db: Database session
        task_id: Review task ID
        resolution: What was done (e.g., "website_found", "merged", "skipped")
        data_updates: Optional dict of field updates to apply to the company
    """
    import json
    
    # Update review task
    db.execute(
        text("""
            UPDATE manual_review_queue
            SET status = :status, completed_at = :completed_at, 
                resolution = :resolution
            WHERE id = :task_id
        """),
        {
            "task_id": task_id,
            "status": ReviewStatus.COMPLETED.value,
            "completed_at": datetime.utcnow(),
            "resolution": resolution,
        }
    )
    
    # Apply data updates if any
    if data_updates:
        task = db.execute(
            text("SELECT company_id FROM manual_review_queue WHERE id = :id"),
            {"id": task_id}
        ).fetchone()
        
        if task:
            company_id = task[0]
            for field, value in data_updates.items():
                # Only update known fields
                if field in ["website", "sector", "description"]:
                    db.execute(
                        text(f"UPDATE companies SET {field} = :value WHERE id = :id"),
                        {"value": value, "id": company_id}
                    )
    
    db.commit()
    logger.info(f"Completed review task {task_id}: {resolution}")


def get_review_stats(db: Session) -> dict:
    """Get statistics about the review queue."""
    result = db.execute(
        text("""
            SELECT 
                task_type,
                status,
                COUNT(*) as count
            FROM manual_review_queue
            GROUP BY task_type, status
        """)
    ).fetchall()
    
    stats = {
        "by_type": {},
        "by_status": {},
        "total_pending": 0,
    }
    
    for r in result:
        task_type, status, count = r
        
        if task_type not in stats["by_type"]:
            stats["by_type"][task_type] = 0
        stats["by_type"][task_type] += count
        
        if status not in stats["by_status"]:
            stats["by_status"][status] = 0
        stats["by_status"][status] += count
        
        if status == "pending":
            stats["total_pending"] += count
    
    return stats
