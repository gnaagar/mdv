import os
import tempfile
import unittest
from mdv.sv_state import MdViewerState

class TestMdViewerState(unittest.TestCase):
    def test_doc_id_indexing_and_mapping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with doc_id
            file1_path = os.path.join(tmpdir, "doc1.md")
            with open(file1_path, "w", encoding="utf-8") as f:
                f.write("---\nid: my-first-doc\ntitle: Doc 1\n---\nHello world")
                
            # Create a file without doc_id
            file2_path = os.path.join(tmpdir, "doc2.md")
            with open(file2_path, "w", encoding="utf-8") as f:
                f.write("Hello world without id")
                
            # Create a file with subfolder and doc_id
            subfolder = os.path.join(tmpdir, "sub")
            os.makedirs(subfolder, exist_ok=True)
            file3_path = os.path.join(subfolder, "doc3.md")
            with open(file3_path, "w", encoding="utf-8") as f:
                f.write("---\nid: my-third-doc\n---\nHello from subfolder")

            # Initialize state
            state = MdViewerState({"dir": tmpdir, "precache": True})
            
            # Verify indexing of doc_id
            doc_map = state.get_doc_id_map()
            self.assertEqual(doc_map.get("my-first-doc"), "doc1.md")
            self.assertEqual(doc_map.get("my-third-doc"), "sub/doc3.md")
            self.assertNotIn("doc2.md", doc_map.values())
            
            # Edit a file to change/remove doc_id
            with open(file1_path, "w", encoding="utf-8") as f:
                f.write("---\nid: my-new-first-doc\n---\nHello changed")
                
            # Trigger state refresh
            state.refresh(force=True)
            
            # Verify updated mapping
            doc_map = state.get_doc_id_map()
            self.assertEqual(doc_map.get("my-new-first-doc"), "doc1.md")
            self.assertNotIn("my-first-doc", doc_map)

    def test_server_doc_id_redirect(self):
        from werkzeug.test import Client
        from mdv.server import App
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("---\nid: my-secret-doc\n---\nSecret data")
                
            config = {
                "dir": tmpdir,
                "precache": True,
            }
            app = App(config)
            client = Client(app)
            
            # Request doc by ID
            response = client.get("/d/my-secret-doc")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers.get("Location"), "/_/test.md")

            # Request non-existent doc ID
            response = client.get("/d/non-existent-id")
            self.assertEqual(response.status_code, 404)

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
