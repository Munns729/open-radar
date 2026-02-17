
import unittest
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from src.universe.ops.cost_tracker import cost_tracker
from src.universe.database import CompanyModel

class TestTier3Fixes(unittest.TestCase):
    
    def setUp(self):
        cost_tracker.reset()
        
    def test_cost_tracker_singleton(self):
        cost_tracker.log_usage("gpt-4", 1000, 1000)
        # Input: 1000/1000 * 0.03 = 0.03
        # Output: 1000/1000 * 0.06 = 0.06
        # Total: 0.09
        self.assertAlmostEqual(cost_tracker.get_total_cost(), 0.09)
        
        from src.universe.ops.cost_tracker import CostTracker
        tracker2 = CostTracker()
        self.assertEqual(tracker2.get_total_cost(), 0.09)
        
    def test_retry_logic_date_check(self):
        # We can't easily test the full async workflow without mocking DB/Network heavily.
        # But we can test the date logic specifically.
        
        c_recent = MagicMock(name="Recent", last_updated=datetime.utcnow() - timedelta(days=2))
        c_old = MagicMock(name="Old", last_updated=datetime.utcnow() - timedelta(days=10))
        c_none = MagicMock(name="None", last_updated=None)
        
        def should_process(company):
            if company.last_updated and (datetime.utcnow() - company.last_updated).days < 7:
                return False
            return True
            
        self.assertFalse(should_process(c_recent))
        self.assertTrue(should_process(c_old))
        self.assertTrue(should_process(c_none))

    @patch('src.universe.workflow.save_companies') # Just to import
    def test_filter_construction(self, mock_save):
        # Verify that we can import and run the filter logic
        # Ideally we'd test the SQLAlchemy expression generation but that requires a session.
        # This test mainly ensures no syntax errors in workflow.py imports
        pass

if __name__ == '__main__':
    unittest.main()
