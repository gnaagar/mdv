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
        md = "[Google](https://google.com) and [Local](/_/local.md)"
        html = MarkdownParser.parse(md)
        self.assertIn('href="https://google.com" target="_blank"', html)
        self.assertIn('href="/_/local.md"', html)
        self.assertNotIn('target="_blank" href="/_/local.md"', html)
        self.assertNotIn('href="/_/local.md" target="_blank"', html)

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

    def test_extract_frontmatter(self):
        # Empty or no frontmatter
        self.assertEqual(MarkdownParser.extract_frontmatter(""), {})
        self.assertEqual(MarkdownParser.extract_frontmatter("Hello world"), {})
        self.assertEqual(MarkdownParser.extract_frontmatter("---\n---"), {})

        # Basic frontmatter
        md = "---\nid: my-doc-1\ntitle: hello\n---\nbody content"
        meta = MarkdownParser.extract_frontmatter(md)
        self.assertEqual(meta.get("id"), "my-doc-1")
        self.assertEqual(meta.get("title"), "hello")

        # Quoted values
        md = "---\nid: \"my-doc-1\"\ntitle: 'hello world'\n---\nbody"
        meta = MarkdownParser.extract_frontmatter(md)
        self.assertEqual(meta.get("id"), "my-doc-1")
        self.assertEqual(meta.get("title"), "hello world")

    def test_rewrite_doc_id_links(self):
        doc_map = {"my-doc-1": "subfolder/another_file.md", "doc-2": "some_file.md"}
        
        # Test basic /d/ link rewriting
        html = '<a href="/d/my-doc-1">Link 1</a>'
        rewritten = MarkdownParser.rewrite_doc_id_links(html, doc_map)
        self.assertEqual(rewritten, '<a href="/_/subfolder/another_file.md">Link 1</a>')
        
        # Test basic /d/ link rewriting with another doc
        html = '<a href="/d/doc-2">Link 2</a>'
        rewritten = MarkdownParser.rewrite_doc_id_links(html, doc_map)
        self.assertEqual(rewritten, '<a href="/_/some_file.md">Link 2</a>')
        
        # Test hash/anchor preservation
        html = '<a href="/d/my-doc-1#section-title">Link 4</a>'
        rewritten = MarkdownParser.rewrite_doc_id_links(html, doc_map)
        self.assertEqual(rewritten, '<a href="/_/subfolder/another_file.md#section-title">Link 4</a>')
        
        # Test unknown ID is left unchanged
        html = '<a href="/d/unknown-id">Link 6</a>'
        rewritten = MarkdownParser.rewrite_doc_id_links(html, doc_map)
        self.assertEqual(rewritten, html)

        # Test external/non-id link remains unchanged
        html = '<a href="https://google.com">Google</a>'
        rewritten = MarkdownParser.rewrite_doc_id_links(html, doc_map)
        self.assertEqual(rewritten, html)
