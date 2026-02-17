"""
Leadership Tracker.
Specialized logic for monitoring Team/About pages to detect C-Suite changes.
"""
import logging
from src.competitive.web_monitor import WebMonitor
from src.competitive.database import MonitoringTargetModel, DetectedChangeModel

logger = logging.getLogger(__name__)

class LeadershipTracker(WebMonitor):
    """
    Specialized monitor for Team pages.
    """
    async def analyze_team_page(self, target: MonitoringTargetModel):
        # Override or extend the check_target logic with specific parsing
        # For MVP, we use the base check_target but maybe set the selector to common team wrappers
        # or use AI analysis on the screenshot if changed.
        
        # Here we just wrap the base check but add 'severity=high' logic if 'CFO' or 'CEO' 
        # is removed/added in the diff.
        
        change = await self.check_target(target)
        
        if change:
            # Post-process the change: did we lose a key role?
            # Simple keyword heuristic
            content = change.diff_content.lower()
            if "former ceo" in content or "interim" in content:
                change.severity = "critical"
                change.description = "Potential Leadership Change Detected: " + change.description
                
                # Update DB
                session = self.db.get_session()
                session.merge(change)
                session.commit()
                session.close()
        
        return change
