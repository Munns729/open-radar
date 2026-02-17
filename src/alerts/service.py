"""Public service interface for the Alerts module."""
from src.alerts.alert_engine import alert_engine

async def check_alerts():
    """Trigger the alert engine to check for new events."""
    await alert_engine.check_alerts()

async def create_test_event():
    """Create a test event for verification."""
    await alert_engine.create_test_event()
