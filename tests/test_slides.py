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

<!-- slide-sep -->

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
Inline <!--red-->critical<!--/red--> status.
<!--blue-->
### Blue Section
Content here
<!--/blue-->
"""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "text_colors.slides.md"
            path.write_text(source, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")
        self.assertIn(b'class="slide-text-red">critical</span>', response.data)
        self.assertIn(b'class="slide-text-blue">', response.data)

        # Test grey and gray text
        doc_grey = parse_slides("---\ntitle: T\n---\n## S\n<!--grey-->neutral<!--/grey--> and <!--gray-->slate<!--/gray-->")
        self.assertIn('class="slide-text-grey">neutral</span>', doc_grey.slides[0][0].html)
        self.assertIn('class="slide-text-gray">slate</span>', doc_grey.slides[0][0].html)

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
<!--green-->
**Orbit is available today.**
<!--/green-->

<!--red-->
*Urgent*: `code_symbol()` failed.
<!--/red-->

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

    def test_slides_css_removes_table_backgrounds(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "test.slides.md"
            path.write_text(SOURCE, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/static/slides.css")
        self.assertEqual(response.status_code, 200)
        css = response.data.decode("utf-8")
        self.assertIn(".slide-content table", css)
        self.assertIn("background-color: transparent", css)

    def test_color_hints_inside_blockquote_for_text_and_quote_styling(self):
        source = """---
title: Test
---
## Slide 1
<!-- quote: yellow -->
> <!--yellow-->
> **Guideline**: Keep slides focused; avoid clutter. <!--/yellow-->

<!-- slide-sep -->
## Slide 2
> <!-- quote: blue -->
> "Simplicity is prerequisite." — <!--green-->Edsger W. Dijkstra<!--/green-->

<!-- slide-sep -->
## Slide 3
> <!-- quote: red -->
> Critical quote with explicit quote directive.

<!-- slide-sep -->
## Slide 4
> <!--red-->
> Multiline critical warning
> <!--/red-->
"""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "quote_colors.slides.md"
            path.write_text(source, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")

        data = response.data
        # Slide 1: Quote is yellow AND text inside is yellow
        self.assertIn(b'class="slide-quote-yellow"', data)
        self.assertIn(b'class="slide-text-yellow"', data)
        self.assertIn(b'<strong>Guideline</strong>', data)

        # Slide 2: Quote is blue AND author text is green
        self.assertIn(b'class="slide-quote-blue"', data)
        self.assertIn(b'<span class="slide-text-green">Edsger W. Dijkstra</span>', data)

        # Slide 3: Quote is red
        self.assertIn(b'class="slide-quote-red"', data)
        self.assertIn(b'Critical quote with explicit quote directive.', data)

        # Slide 4: Text inside blockquote is red
        self.assertIn(b'class="slide-text-red"', data)
        self.assertIn(b'Multiline critical warning', data)

    def test_text_color_inside_columns(self):
        source = """---
title: Test
---
## Status
<!-- col-start 1:1 red:green -->
### Blocked
<!--red-->
**Database connection pool exhausted.**
<!--/red-->
<!-- col-sep -->
### Healthy
<!--green-->
All services nominal.
<!--/green-->
<!-- col-end -->
"""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "column_text_colors.slides.md"
            path.write_text(source, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")

        self.assertIn(b'slide-column-red', response.data)
        self.assertIn(b'slide-column-green', response.data)
        self.assertIn(b'class="slide-text-red"', response.data)
        self.assertIn(b'class="slide-text-green"', response.data)
        self.assertIn(b'Database connection pool exhausted.', response.data)

    def test_slide_sep_inside_code_blocks_is_ignored(self):
        source = """---
title: Test
---
## Slide 1
Here is code that demonstrates slide separation:

```markdown
## Inside Code Slide 1

Some text.

<!-- slide-sep -->

## Inside Code Slide 2
```

Still on Slide 1.

<!-- slide-sep -->
## Slide 2
Now on Slide 2.
"""
        doc = parse_slides(source)
        self.assertEqual(len(doc.slides), 2)
        self.assertIn("&lt;!-- slide-sep --&gt;", doc.slides[0][0].html)
        self.assertIn("Still on Slide 1", doc.slides[0][0].html)
        self.assertIn("Now on Slide 2", doc.slides[1][0].html)

    def test_only_canonical_color_syntax_supported(self):
        # Canonical syntax <!--red-->...<!--/red--> is converted
        source_canonical = """---
title: Test
---
## Canonical
<!--red-->Red text<!--/red-->
"""
        doc1 = parse_slides(source_canonical)
        self.assertIn('class="slide-text-red">Red text</span>', doc1.slides[0][0].html)

        # Non-canonical syntax <!-- color: red --> is not parsed as slide-text
        source_legacy = """---
title: Test
---
## Legacy
<!-- color: red -->Red text<!-- /color -->
"""
        doc2 = parse_slides(source_legacy)
        self.assertNotIn('slide-text-red', doc2.slides[0][0].html)

    def test_accent_colors_in_slides_css(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "test.slides.md"
            path.write_text(SOURCE, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/static/slides.css")
        self.assertEqual(response.status_code, 200)
        css = response.data.decode("utf-8")
        for color in ("red", "green", "blue", "yellow", "pink", "purple", "grey", "gray"):
            self.assertIn(f"--accent-{color}-bg:", css)
            self.assertIn(f"--accent-{color}-border:", css)
            self.assertIn(f"--accent-{color}-text:", css)
        self.assertIn("--accent-none-bg:", css)

    def test_uncolored_blockquote_followed_by_colored_blockquote(self):
        source = """---
title: Test
---
## Quotes
> Default neutral quote.

<!-- quote: blue -->
> Blue highlighted quote.
"""
        doc = parse_slides(source)
        html = doc.slides[0][0].html
        # First quote should NOT have slide-quote-blue
        self.assertRegex(html, r"<blockquote[^>]*>\s*<p[^>]*>Default neutral quote\.</p>\s*</blockquote>")
        # Second quote SHOULD have slide-quote-blue
        self.assertRegex(html, r"<blockquote[^>]*class=\"[^\"]*slide-quote-blue[^\"]*\"[^>]*>\s*<p[^>]*>Blue highlighted quote\.</p>\s*</blockquote>")

    def test_slides_css_borderless_styling(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "test.slides.md"
            path.write_text(SOURCE, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/static/slides.css")
        self.assertEqual(response.status_code, 200)
        css = response.data.decode("utf-8")
        self.assertIn("border: none;", css)
        self.assertIn("border-radius: 0;", css)
        self.assertIn("box-shadow: none;", css)
        self.assertIn("body.is-title-slide", css)
        self.assertIn("linear-gradient", css)

    def test_slides_js_borderless_header_sync(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "test.slides.md"
            path.write_text(SOURCE, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/static/js/slides.js")
        self.assertEqual(response.status_code, 200)
        js = response.data.decode("utf-8")
        self.assertIn("OUTER_GAP = 0;", js)
        self.assertIn("appendChild(count)", js)
        self.assertIn("updateHeaderSync", js)
        self.assertIn("--header-bottom", js)

    def test_parses_flow_unordered_list(self):
        source = """---
title: Test
---
## Flow Test
<!-- flow -->
- **Ingest**
  Raw logs
- **Process**
  Enrich data
- **Deliver**
  Real-time push
<!-- /flow -->
"""
        doc = parse_slides(source)
        self.assertEqual(len(doc.slides[0]), 2)
        block = doc.slides[0][1]
        self.assertEqual(block.kind, "flow")
        self.assertEqual(len(block.columns), 3)
        self.assertFalse(block.is_numbered)
        self.assertIn("<strong>Ingest</strong>", block.columns[0])
        self.assertIn("Raw logs", block.columns[0])

        with TemporaryDirectory() as directory:
            path = Path(directory) / "test.slides.md"
            path.write_text(source, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn('class="slide-flow"', html)
        self.assertIn('class="slide-flow-step"', html)
        self.assertIn('class="slide-flow-arrow"', html)
        self.assertNotIn('class="slide-flow-badge"', html)

    def test_parses_flow_ordered_list_with_badges(self):
        source = """---
title: Test
---
## Flow Test
<!-- flow blue:green:purple -->
1. **Discover**
   User research
2. **Design**
   Figma mockup
3. **Deploy**
   Canary release
<!-- /flow -->
"""
        doc = parse_slides(source)
        self.assertEqual(len(doc.slides[0]), 2)
        block = doc.slides[0][1]
        self.assertEqual(block.kind, "flow")
        self.assertEqual(len(block.columns), 3)
        self.assertTrue(block.is_numbered)
        self.assertEqual(block.column_colors, ("blue", "green", "purple"))

        with TemporaryDirectory() as directory:
            path = Path(directory) / "test.slides.md"
            path.write_text(source, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")
        html = response.data.decode("utf-8")
        self.assertIn('class="slide-flow-badge">1</div>', html)
        self.assertIn('class="slide-flow-badge">2</div>', html)
        self.assertIn('class="slide-flow-badge">3</div>', html)
        self.assertIn("slide-flow-step-blue", html)
        self.assertIn("slide-flow-step-green", html)
        self.assertIn("slide-flow-step-purple", html)

    def test_parses_flow_with_flow_sep_and_single_color(self):
        source = """---
title: Test
---
## Flow Test
<!-- flow yellow -->
### Step A
Alpha
<!-- flow-sep -->
### Step B
Beta
<!-- flow-end -->
"""
        doc = parse_slides(source)
        self.assertEqual(len(doc.slides[0]), 2)
        block = doc.slides[0][1]
        self.assertEqual(block.kind, "flow")
        self.assertEqual(len(block.columns), 2)
        self.assertEqual(block.column_colors, ("yellow", "yellow"))
        self.assertIn(">Step A</h3>", block.columns[0])
        self.assertIn(">Step B</h3>", block.columns[1])

    def test_parses_vertical_flow_stack(self):
        source = """---
title: Test
---
## Vertical Flow Test
<!-- flow:vertical blue:green:yellow -->
1. **Frontend**
   React app
2. **Backend**
   FastAPI
3. **Database**
   PostgreSQL
<!-- /flow -->
"""
        doc = parse_slides(source)
        self.assertEqual(len(doc.slides[0]), 2)
        block = doc.slides[0][1]
        self.assertEqual(block.kind, "flow")
        self.assertEqual(block.orientation, "vertical")
        self.assertEqual(block.column_colors, ("blue", "green", "yellow"))
        self.assertTrue(block.is_numbered)

        with TemporaryDirectory() as directory:
            path = Path(directory) / "test.slides.md"
            path.write_text(source, encoding="utf-8")
            response = Client(SlidesApp(path)).get("/")
        html = response.data.decode("utf-8")
        self.assertIn("slide-flow-vertical", html)
        self.assertIn("M12 5v14M5 13l7 7 7-7", html)

        # Test stack alias
        doc_stack = parse_slides("---\ntitle: T\n---\n## S\n<!-- stack blue:green -->\n- A\n- B\n<!-- /stack -->\n")
        self.assertEqual(doc_stack.slides[0][1].orientation, "vertical")

    def test_flow_syntax_errors(self):
        # Unclosed flow
        with self.assertRaises(SlidesParseError) as ctx:
            parse_slides("---\ntitle: T\n---\n## S\n<!-- flow -->\n- A\n")
        self.assertIn("missing its /flow directive", str(ctx.exception))

        # Flow sep outside flow
        with self.assertRaises(SlidesParseError) as ctx:
            parse_slides("---\ntitle: T\n---\n## S\n<!-- flow-sep -->\n")
        self.assertIn("Found flow-sep outside a flow block", str(ctx.exception))

        # Flow end without flow
        with self.assertRaises(SlidesParseError) as ctx:
            parse_slides("---\ntitle: T\n---\n## S\n<!-- /flow -->\n")
        self.assertIn("without a matching flow directive", str(ctx.exception))

        # Flow inside column
        with self.assertRaises(SlidesParseError) as ctx:
            parse_slides("---\ntitle: T\n---\n## S\n<!-- col-start 1:1 none -->\n<!-- flow -->\n<!-- /flow -->\n<!-- col-end -->\n")
        self.assertIn("cannot start inside a column block", str(ctx.exception))

        # Column inside flow
        with self.assertRaises(SlidesParseError) as ctx:
            parse_slides("---\ntitle: T\n---\n## S\n<!-- flow -->\n<!-- col-start 1:1 none -->\n<!-- col-end -->\n<!-- /flow -->\n")
        self.assertIn("cannot start inside a flow block", str(ctx.exception))

        # Invalid flow color
        with self.assertRaises(SlidesParseError) as ctx:
            parse_slides("---\ntitle: T\n---\n## S\n<!-- flow neon -->\n- A\n<!-- /flow -->\n")
        self.assertIn("Invalid flow color 'neon'", str(ctx.exception))

        # Mismatched color count
        with self.assertRaises(SlidesParseError) as ctx:
            parse_slides("---\ntitle: T\n---\n## S\n<!-- flow blue:green:red -->\n- A\n- B\n<!-- /flow -->\n")
        self.assertIn("declares 3 colors but contains 2 steps", str(ctx.exception))








