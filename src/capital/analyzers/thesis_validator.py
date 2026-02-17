"""
Thesis Validation Engine.
Analyzes capital flow data to validate investment theses.
"""
from typing import Dict, Any, List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.capital.database import PEInvestmentModel, StrategicAcquisitionModel, StrategicAcquirerModel

class ThesisValidator:
    """
    Validates thesis hypotheses against gathered market data.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def validate_regulatory_premium(self) -> Dict[str, Any]:
        """
        Hypothesis: Regulatory moats command a premium multiple.
        Expected: Regulatory > Network Effects > None
        """
        # Query average exit multiple by moat type
        query = (
            select(
                PEInvestmentModel.moat_type,
                func.avg(PEInvestmentModel.exit_multiple).label("avg_multiple"),
                func.count(PEInvestmentModel.id).label("count")
            )
            .where(PEInvestmentModel.exit_multiple.is_not(None))
            .group_by(PEInvestmentModel.moat_type)
            .order_by(func.avg(PEInvestmentModel.exit_multiple).desc())
        )
        
        result = await self.session.execute(query)
        results = result.fetchall()
        
        data = {row.moat_type: float(row.avg_multiple) for row in results if row.avg_multiple}
        
        # Simple validation logic
        reg_mult = data.get("regulatory", 0)
        none_mult = data.get("none", 0)
        
        supports_thesis = reg_mult > (none_mult * 1.1) # 10% premium threshold
        
        return {
            "hypothesis": "Regulatory Moat Premium",
            "supports_thesis": supports_thesis,
            "data": data,
            "premium_pct": ((reg_mult - none_mult) / none_mult * 100) if none_mult else 0
        }

    async def validate_strategic_premium(self) -> Dict[str, Any]:
        """
        Hypothesis: Strategic acquirers pay more than PE firms.
        """
        # Avg PE entry multiple
        # pe_avg = self.session.query(func.avg(PEInvestmentModel.entry_multiple)).scalar() or 0
        result_pe = await self.session.execute(select(func.avg(PEInvestmentModel.entry_multiple)))
        pe_avg = result_pe.scalar() or 0
        
        # Avg Strategic acquisition multiple
        # strat_avg = self.session.query(func.avg(StrategicAcquisitionModel.ebitda_multiple)).scalar() or 0
        result_strat = await self.session.execute(select(func.avg(StrategicAcquisitionModel.ebitda_multiple)))
        strat_avg = result_strat.scalar() or 0
        
        supports_thesis = strat_avg > (pe_avg * 1.1)
        
        return {
            "hypothesis": "Strategic Premium",
            "supports_thesis": supports_thesis,
            "metrics": {
                "pe_avg_multiple": float(pe_avg),
                "strategic_avg_multiple": float(strat_avg)
            }
        }

    async def generate_report(self) -> List[Dict[str, Any]]:
        """Run all validations"""
        return [
            await self.validate_regulatory_premium(),
            await self.validate_strategic_premium()
        ]
