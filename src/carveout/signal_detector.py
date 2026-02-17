"""
Signal Detector.
Calculates carveout probability based on explicit and implicit signals.
"""
from typing import List
from .database import Division, CarveoutSignal

class SignalDetector:
    """Calculates divestiture probability."""

    def calculate_probability(self, division: Division, signals: List[CarveoutSignal]) -> int:
        """
        Calculate score 0-100 based on signals.
        """
        score = 0
        
        explicit_signals = [s for s in signals if s.signal_type == 'explicit']
        implicit_signals = [s for s in signals if s.signal_type == 'implicit']
        early_signals = [s for s in signals if s.signal_type == 'early']

        # Explicit Signals
        for s in explicit_signals:
            if s.signal_category == 'strategic_review': score += 60
            elif s.signal_category == 'banker_hired': score += 50
            elif s.signal_category == 'public_spin_announced': score += 80
            elif s.signal_category == 'activist_demand': score += 40
            
            if s.confidence == 'high': score += 10

        # Implicit Signals
        for s in implicit_signals:
            if s.signal_category == 'omitted_from_strategy': score += 20
            elif s.signal_category == 'capex_reduction': score += 15
            elif s.signal_category == 'management_change_unfilled': score += 15
            
        # Early Signals
        for s in early_signals:
             if s.signal_category == 'new_ceo_simplification': score += 10
             elif s.signal_category == 'regulatory_issue': score += 15

        # Penalties (reduce probability if signals suggest it's staying)
        # Using a simplified check here, assuming negative signals are passed with negative 'increases_probability'
        # or we implement a separate logic. For now, clamping score.
        
        return min(100, max(0, score))

    def determine_timeline(self, probability: int) -> str:
        """Classify timeline based on probability."""
        if probability >= 80: return "imminent"
        if probability >= 60: return "6-12mo"
        if probability >= 40: return "12-24mo"
        if probability >= 20: return "24mo+"
        return "unlikely"
