
import unittest
from src.core.utils import normalize_name
from src.universe.ops.filters import PreEnrichmentFilter

class TestTier1Fixes(unittest.TestCase):
    
    def test_normalize_name(self):
        # Case 1: Simple Lowercase
        self.assertEqual(normalize_name("Apple"), "apple")
        
        # Case 2: Legal Syntax
        self.assertEqual(normalize_name("Apple Inc."), "apple")
        self.assertEqual(normalize_name("Apple Inc"), "apple")
        self.assertEqual(normalize_name("Dassault Systemes SE"), "dassault systemes")
        self.assertEqual(normalize_name("Dassault Systèmes S.A."), "dassault systemes")
        
        # Case 3: Accents
        self.assertEqual(normalize_name("Café"), "cafe")
        self.assertEqual(normalize_name("François"), "francois")
        
        # Case 4: Punctuation
        self.assertEqual(normalize_name("Hello, World!"), "hello world")
        
    def test_pre_enrichment_filter(self):
        # Case 1: Revenue Filter
        self.assertFalse(PreEnrichmentFilter.should_process({"revenue": 600_000_000}))
        self.assertTrue(PreEnrichmentFilter.should_process({"revenue": 400_000_000}))
        
        # Case 2: Public Keywords
        self.assertFalse(PreEnrichmentFilter.should_process({"description": "Traded on NYSE: SHOP"}))
        # "Inc" alone isn't enough, so let's add a keyword or expect True
        self.assertTrue(PreEnrichmentFilter.should_process({"name": "Shopify Inc", "description": "Global commerce company"})) 
        
        # Test PLC exclusion
        self.assertFalse(PreEnrichmentFilter.should_process({"name": "Barclays PLC"}))
        self.assertFalse(PreEnrichmentFilter.should_process({"description": "An Accel-KKR portfolio company"}))
        
        # Case 4: Name Suffix
        self.assertFalse(PreEnrichmentFilter.should_process({"name": "Barclays PLC"}))
        self.assertTrue(PreEnrichmentFilter.should_process({"name": "Barclays Limited"})) # Limited is fine

if __name__ == '__main__':
    unittest.main()
