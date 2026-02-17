"""Public service interface for the Reporting module."""
from typing import List, Optional
from src.reporting.workflow import generate_report
from src.reporting.filters import ReportFilters

# Re-export key functions
__all__ = ["generate_report", "ReportFilters"]
