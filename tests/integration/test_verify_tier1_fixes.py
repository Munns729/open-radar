
import unittest
import ast
import sys
import os
from pathlib import Path

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestTier1Fixes(unittest.TestCase):

    def test_capital_eval_security(self):
        """Verify that eval() is replaced by ast.literal_eval() to prevent code injection."""
        from src.web.routers.capital import get_capital_stats
        import inspect
        
        # Read the source code of the function or file to verify ast.literal_eval usage or test logic directly
        # Since we can't easily mock the DB session in a simple script without setup, 
        # let's verify the code structure first, or better yet, verify the specific logic block if possible.
        
        # Actually, let's just inspect the file content for 'eval(' vs 'ast.literal_eval('
        with open("src/web/routers/capital.py", "r") as f:
            content = f.read()
        
        target = "ast.literal_eval(str(inv.pe_identified_moats))"
        clean_content = content.replace(" ", "").replace("\n", "").replace("\t", "")
        self.assertIn(target, clean_content, "Code should use ast.literal_eval()")
        
        # Check that 'eval' is not used without 'literal_' prefix
        # We look for 'eval(' and ensure it's preceded by 'literal_'
        import re
        eval_calls = [m.start() for m in re.finditer(r'eval\(', content)]
        literal_eval_calls = [m.start() for m in re.finditer(r'literal_eval\(', content)]
        
        # Every eval( should be a literal_eval(
        # The start index of 'eval' in 'literal_eval' is 8 chars after start of 'literal_eval'
        # So for every literal_eval at index i, there is an eval at i+8.
        # We want to make sure there are NO other eval calls.
        
        valid_eval_indices = {i + 8 for i in literal_eval_calls}
        # Also allow eval in comments or unrelated parts? No, let's be strict for this file.
        
        for idx in eval_calls:
            if idx not in valid_eval_indices:
                 # Check if it's ast.literal_eval alias?
                 # Just fail if we see bare eval.
                 self.fail(f"Found unsafe eval() at index {idx}: {content[idx-10:idx+20]}")

    def test_routers_init(self):
        """Verify that src/web/routers/__init__.py exists."""
        self.assertTrue(os.path.exists("src/web/routers/__init__.py"), "src/web/routers/__init__.py does not exist")

    def test_router_prefixes(self):
        """Verify that reports and search routers have correct prefixes."""
        from src.web.routers.reports import router as reports_router
        from src.web.routers.search import router as search_router
        
        self.assertEqual(reports_router.prefix, "/api/reports", "Reports router prefix should be /api/reports")
        self.assertEqual(search_router.prefix, "/api/search", "Search router prefix should be /api/search")

    def test_relationships_contact_default(self):
        """Verify that potentially dangerous Contact() default is removed."""
        # Inspect code to ensure .get(..., Contact()) is gone
        with open("src/web/routers/relationships.py", "r") as f:
            content = f.read()
            
        self.assertNotIn("connected_contacts.get(conn.get_other_contact(contact_id), Contact()).full_name", content, "Code still contains dangerous Contact() default")
        self.assertNotIn("connected_contacts.get(conn.get_other_contact(contact_id), Contact()).company_name", content, "Code still contains dangerous Contact() default")

if __name__ == "__main__":
    unittest.main()
