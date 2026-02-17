
import unittest
from src.universe.ops.cost_tracker import cost_tracker

class TestCostTrackerFix(unittest.TestCase):
    def setUp(self):
        cost_tracker.reset()

    def test_kimi_matching(self):
        # Case insensitive and contains "kimi"
        cost_tracker.log_usage(model="kimi-latest", input_tokens=1000, output_tokens=1000, provider="Moonshot")
        # 1000 tokens input ($0.0004) + 1000 output ($0.0004) = $0.0008
        self.assertAlmostEqual(cost_tracker.get_total_cost(), 0.0008, places=5)

    def test_haiku_matching(self):
        cost_tracker.log_usage(model="claude-3-haiku-20240307", input_tokens=1000, output_tokens=1000, provider="Anthropic")
        # 1000 tokens input ($0.00025) + 1000 output ($0.00125) = $0.0015
        self.assertAlmostEqual(cost_tracker.get_total_cost(), 0.0015, places=5)

if __name__ == "__main__":
    unittest.main()
