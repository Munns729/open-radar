"""Base generator class."""

from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
from pathlib import Path
from src.universe.database import CompanyModel as Company


class BaseGenerator(ABC):
    """Base class for report generators."""
    
    def __init__(self, output_dir: str = "outputs"):
        """Initialize generator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    @abstractmethod
    def generate(self, companies: List[Company], filename: str = None) -> str:
        """
        Generate report from companies.
        
        Args:
            companies: List of Company objects
            filename: Optional custom filename
        
        Returns:
            Path to generated file
        """
        pass
    
    def _get_filename(self, prefix: str, extension: str, custom_name: str = None) -> str:
        """Generate filename with timestamp."""
        if custom_name:
            return custom_name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
    
    def _format_revenue(self, revenue_gbp: float) -> str:
        """Format revenue in millions or billions."""
        if revenue_gbp is None:
            return "N/A"
        
        millions = revenue_gbp / 1_000_000
        
        if millions >= 1000:
            return f"£{millions/1000:.1f}B"
        else:
            return f"£{millions:.1f}M"
    
    def _get_sector_counts(self, companies: List[Company]) -> dict:
        """Get company counts by sector."""
        sector_counts = {}
        for company in companies:
            sector = company.sector or "Unknown"
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        return dict(sorted(sector_counts.items(), key=lambda x: x[1], reverse=True))
