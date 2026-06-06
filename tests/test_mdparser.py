import unittest
import re
from mdv.mdparser import MarkdownParser

class TestMarkdownParser(unittest.TestCase):
    def test_basic_parsing(self):
        # Paragraphs & Bold/Italic
        md = "Hello **world** *italic*!"
        html = MarkdownParser.parse(md)
        self.assertIn("Hello <strong>world</strong> <em>italic</em>!", html)

    def test_headings_and_anchors(self):
        # Headings should render with anchors and data-source-line
        md = "# My Heading"
        html = MarkdownParser.parse(md)
        self.assertIn('<h1 id="my-heading" data-source-line="1">My Heading</h1>', html)

    def test_tables(self):
        # Table rendering should work
        md = "| Header 1 | Header 2 |\n| --- | --- |\n| Cell 1 | Cell 2 |"
        html = MarkdownParser.parse(md)
        self.assertIn("<table", html)
        self.assertIn("<th>Header 1</th>", html)
        self.assertIn("<td>Cell 1</td>", html)

    def test_tasklists(self):
        # Task lists check
        md = "- [ ] Unchecked task\n- [x] Checked task"
        html = MarkdownParser.parse(md)
        self.assertIn('class="task-list-item"', html)
        self.assertIn('type="checkbox"', html)

    def test_front_matter(self):
        # Front matter should be ignored/hidden
        md = "---\ntitle: Test\n---\nActual content"
        html = MarkdownParser.parse(md)
        self.assertNotIn("title: Test", html)
        self.assertIn("Actual content", html)

    def test_source_line_numbers(self):
        # Source line numbers should be injected
        md = "Paragraph 1\n\nParagraph 2"
        html = MarkdownParser.parse(md)
        self.assertIn('data-source-line="1"', html)
        self.assertIn('data-source-line="3"', html)

    def test_external_links_target_blank(self):
        # HTTP/HTTPS external links should have target="_blank"
        md = "[Google](https://google.com) and [Local](/v/local.md)"
        html = MarkdownParser.parse(md)
        self.assertIn('href="https://google.com" target="_blank"', html)
        self.assertIn('href="/v/local.md"', html)
        self.assertNotIn('target="_blank" href="/v/local.md"', html)
        self.assertNotIn('href="/v/local.md" target="_blank"', html)

    def test_html_sanitization(self):
        # Dangerous tags should be stripped/sanitized
        md = "<script>alert(1)</script>Safe Text<iframe src='http://dangerous.com'></iframe>"
        html = MarkdownParser.parse(md)
        self.assertNotIn("<script>", html)
        self.assertNotIn("iframe", html)
        self.assertIn("Safe Text", html)

        # Event handlers should be removed
        md = '<img src="x" onerror="alert(1)" />'
        html = MarkdownParser.parse(md)
        self.assertNotIn("onerror", html)
        self.assertIn('<img src="x" />', html)

        # Dangerous URI schemes
        md = '[XSS Link](javascript:alert(1))'
        html = MarkdownParser.parse(md)
        # Markdown parser leaves it as text because it's javascript: scheme (validation fails by default)
        self.assertNotIn('href="javascript:', html)

    def test_math_cleaning(self):
        # Test basic math cleaning (merging lines and escaping backslashes)
        md = "$$\n\\frac{1}{2}\n$$"
        cleaned = MarkdownParser._clean_math(md)
        # _clean_math converts '\\' to '\\\\' and merges lines.
        self.assertIn("$$ \\\\frac{1}{2}$$", cleaned)

    def test_math_inside_code_blocks(self):
        # Verifies the bug fix: math blocks inside fenced code blocks must NOT be modified
        md = "```latex\n$$\n\\frac{1}{2}\n$$\n```"
        cleaned = MarkdownParser._clean_math(md)
        # Should be completely identical because it's inside a code fence!
        self.assertEqual(cleaned, md)
