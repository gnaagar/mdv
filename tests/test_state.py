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
