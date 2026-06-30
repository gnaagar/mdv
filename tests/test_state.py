import os
import tempfile
import unittest
from mdv.sv_state import MdViewerState

class TestMdViewerState(unittest.TestCase):


    def test_wikilink_indexing_and_mapping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1_path = os.path.join(tmpdir, "apple-pie.md")
            with open(file1_path, "w", encoding="utf-8") as f:
                f.write("Hello world")
                
            subfolder = os.path.join(tmpdir, "recipes")
            os.makedirs(subfolder, exist_ok=True)
            file2_path = os.path.join(subfolder, "banana-cake.md")
            with open(file2_path, "w", encoding="utf-8") as f:
                f.write("Banana content")
                
            state = MdViewerState({"dir": tmpdir, "precache": True})
            wikilink_map = state.get_wikilink_map()
            
            # Verify apple-pie mapping and suffixes
            self.assertIn("apple-pie", wikilink_map)
            self.assertEqual(wikilink_map["apple-pie"], ["apple-pie.md"])
            self.assertIn("apple-pie.md", wikilink_map)
            self.assertEqual(wikilink_map["apple-pie.md"], ["apple-pie.md"])
            
            # Verify banana-cake mapping and suffixes
            self.assertIn("banana-cake", wikilink_map)
            self.assertEqual(wikilink_map["banana-cake"], ["recipes/banana-cake.md"])
            self.assertIn("recipes/banana-cake", wikilink_map)
            self.assertEqual(wikilink_map["recipes/banana-cake"], ["recipes/banana-cake.md"])
            self.assertIn("recipes/banana-cake.md", wikilink_map)
            self.assertEqual(wikilink_map["recipes/banana-cake.md"], ["recipes/banana-cake.md"])

    def test_resolve_wikilink_nearest_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "a", "x"), exist_ok=True)
            os.makedirs(os.path.join(tmpdir, "b"), exist_ok=True)
            
            with open(os.path.join(tmpdir, "readme.md"), "w", encoding="utf-8") as f:
                f.write("Root readme")
            with open(os.path.join(tmpdir, "a", "readme.md"), "w", encoding="utf-8") as f:
                f.write("A readme")
            with open(os.path.join(tmpdir, "a", "setup.md"), "w", encoding="utf-8") as f:
                f.write("A setup")
            with open(os.path.join(tmpdir, "a", "x", "setup.md"), "w", encoding="utf-8") as f:
                f.write("A/X setup")
            with open(os.path.join(tmpdir, "b", "setup.md"), "w", encoding="utf-8") as f:
                f.write("B setup")
                
            state = MdViewerState({"dir": tmpdir, "precache": True})
            
            # Case 1: Sibling match (current_file = 'a/readme.md', target = 'setup')
            # 'a/setup.md' is a sibling of 'a/readme.md' (distance = (0, 0))
            # 'a/x/setup.md' is a child (distance = (0, 1))
            # 'b/setup.md' is in sibling directory of a (distance = (1, 1))
            # Unique closest match should be 'a/setup.md'
            res = state.resolve_wikilink("setup", "a/readme.md")
            self.assertEqual(res, "a/setup.md")
            
            # Case 2: Child match (current_file = 'readme.md' at root, target = 'setup')
            # 'a/setup.md' (distance = (0, 1))
            # 'b/setup.md' (distance = (0, 1))
            # 'a/x/setup.md' (distance = (0, 2))
            # Nearest distance is (0, 1), but we have two candidates at that distance ('a/setup.md' and 'b/setup.md').
            # Since min distance has a tie, it should be ambiguous (return None)
            res = state.resolve_wikilink("setup", "readme.md")
            self.assertIsNone(res)
            
            # Case 3: Unique resolution specifying longer suffix
            res = state.resolve_wikilink("b/setup", "readme.md")
            self.assertEqual(res, "b/setup.md")

    def test_server_theme_cookies(self):
        from werkzeug.test import Client
        from mdv.server import App
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "dir": tmpdir,
                "precache": True,
            }
            app = App(config)
            client = Client(app)
            
            # Default theme (empty config, no cookie) should fall back to default template rendering theme (basic)
            response = client.get("/_/")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'href="/static/themes/basic.css"', response.data)
            
            # Request with theme cookie set
            client.set_cookie("theme", "sans-dark")
            response = client.get("/_/")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'href="/static/themes/sans-dark.css"', response.data)

    def test_configure_logging(self):
        import logging
        from mdv.logger import configure_logging
        
        # Test default/False debug mode
        configure_logging(debug=False)
        self.assertEqual(logging.getLogger("werkzeug").getEffectiveLevel(), logging.WARNING)
        self.assertEqual(logging.getLogger("mdv").getEffectiveLevel(), logging.INFO)
        
        # Test True debug mode
        configure_logging(debug=True)
        self.assertEqual(logging.getLogger("werkzeug").getEffectiveLevel(), logging.INFO)
        self.assertEqual(logging.getLogger("mdv").getEffectiveLevel(), logging.DEBUG)
        
        # Restore defaults for logging
        configure_logging(debug=False)
