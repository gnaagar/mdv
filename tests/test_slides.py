import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mdv.slides import SlidesApp, SlidesParseError, parse_slides
from werkzeug.test import Client


SOURCE = '''---
title: "Example presentation"
author: Ada
date: 2026-10-08
---

## First slide

Welcome.

---

## Second slide

<!-- col-start 1:2 -->

### Left

<!-- col-sep -->

### Right

<!-- col-end -->
'''


class TestSlidesParser(unittest.TestCase):
    def test_parses_metadata_slides_and_columns(self):
        document = parse_slides(SOURCE)

        self.assertEqual(document.metadata["title"], "Example presentation")
        self.assertEqual(len(document.slides), 2)
        self.assertIn("First slide", document.slides[0][0].html)
        columns = document.slides[1][1]
        self.assertEqual(columns.kind, "columns")
        self.assertEqual(columns.ratios, (1.0, 2.0))
        self.assertIn("Left", columns.columns[0])
        self.assertIn("Right", columns.columns[1])

    def test_requires_front_matter(self):
        with self.assertRaises(SlidesParseError):
            parse_slides("# No front matter")

    def test_validates_column_count(self):
        source = "---\ntitle: Test\n---\n## Layout\n<!-- col-start 1:1 -->\nOnly one column\n<!-- col-end -->"
        with self.assertRaisesRegex(SlidesParseError, "declares 2 columns"):
            parse_slides(source)

    def test_requires_an_h2_slide_title_and_lower_subheadings(self):
        with self.assertRaisesRegex(SlidesParseError, "must begin with a ## heading"):
            parse_slides("---\ntitle: Test\n---\n# Invalid title")
        with self.assertRaisesRegex(SlidesParseError, "use ### or lower"):
            parse_slides("---\ntitle: Test\n---\n## Title\n\n## Invalid second heading")

    def test_standalone_app_renders_presentation(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "example.slides.md"
            path.write_text(SOURCE, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Example presentation", response.data)
        self.assertIn(b"slide-columns", response.data)
        self.assertIn(b"Author", response.data)
        self.assertIn(b"1 / 3", response.data)

    def test_marks_three_row_column_slides_as_dense(self):
        source = """---
title: Test
---
## Grid
<!-- col-start 1 -->
### One
<!-- col-end -->
<!-- col-start 1 -->
### Two
<!-- col-end -->
<!-- col-start 1 -->
### Three
<!-- col-end -->
"""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "grid.slides.md"
            path.write_text(source, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")

        self.assertIn(b"slide-dense-grid", response.data)
