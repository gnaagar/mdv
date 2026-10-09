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

    def test_parses_column_accent_colors(self):
        source = """---
title: Test
---
## Colors
<!-- col-start 1:1 yellow:blue -->
### Left
<!-- col-sep -->
<!-- col-color green -->
### Right
<!-- col-end -->
"""
        document = parse_slides(source)
        columns = document.slides[0][1]
        self.assertEqual(columns.column_colors, ("yellow", "green"))

        with TemporaryDirectory() as directory:
            path = Path(directory) / "colors.slides.md"
            path.write_text(source, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")
        self.assertIn(b"slide-column-yellow", response.data)
        self.assertIn(b"slide-column-green", response.data)

    def test_validates_column_colors(self):
        source = """---
title: Test
---
## Colors
<!-- col-start 1:1 purple:orange -->
Col 1
<!-- col-sep -->
Col 2
<!-- col-end -->
"""
        with self.assertRaisesRegex(SlidesParseError, "Invalid column color"):
            parse_slides(source)

    def test_renders_text_accent_colors(self):
        source = """---
title: Test
---
## Text Colors
Inline <!-- color: red -->critical<!-- /color --> status.
<!-- color: blue -->
### Blue Section
Content here
<!-- /color -->
"""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "text_colors.slides.md"
            path.write_text(source, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")
        self.assertIn(b'class="slide-text-red">critical</span>', response.data)
        self.assertIn(b'class="slide-text-blue">', response.data)

    def test_renders_blockquote_accent_colors(self):
        source = """---
title: Test
---
## Quotes
<!-- quote: green -->
> Safe and reversible deployments.

> <!-- quote: yellow -->
> Warning: Breaking change ahead.
"""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "quotes.slides.md"
            path.write_text(source, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")
        self.assertIn(b'class="slide-quote-green"', response.data)
        self.assertIn(b'class="slide-quote-yellow"', response.data)

    def test_preserves_markdown_formatting_inside_color_directives(self):
        source = """---
title: Test
---
## Markdown inside colors
<!-- color: green -->
**Orbit is available today.**
<!-- /color -->

<!-- color: red -->
*Urgent*: `code_symbol()` failed.
<!-- /color -->

<!-- quote: blue -->
> **Safety first**: Always test in staging before deploying.
"""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "formatting.slides.md"
            path.write_text(source, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")

        self.assertIn(b'<strong>Orbit is available today.</strong>', response.data)
        self.assertIn(b'class="slide-text-green"', response.data)
        self.assertIn(b'<em>Urgent</em>', response.data)
        self.assertIn(b'<code>code_symbol()</code>', response.data)
        self.assertIn(b'class="slide-text-red"', response.data)
        self.assertIn(b'class="slide-quote-blue"', response.data)
        self.assertIn(b'<strong>Safety first</strong>', response.data)

    def test_extracts_speaker_notes_and_hides_from_presentation(self):
        source = """---
title: Test
---
## Slide with notes
Slide body text.

<!-- speaker -->
# Note Heading
- Mention performance metrics
- Do not forget to thank the team
"""
        doc = parse_slides(source)
        self.assertEqual(len(doc.slides), 1)
        self.assertIn("Slide body text", doc.slides[0][0].html)
        self.assertNotIn("Mention performance metrics", doc.slides[0][0].html)
        self.assertIn("Mention performance metrics", doc.slides[0].notes_html)
        self.assertIn("Note Heading", doc.slides[0].notes_html)

        with TemporaryDirectory() as directory:
            path = Path(directory) / "notes.slides.md"
            path.write_text(source, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")

        self.assertIn(b'<div class="speaker-notes" hidden style="display: none;"', response.data)
        self.assertIn(b'Mention performance metrics', response.data)



