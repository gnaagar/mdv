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

    def test_headings_slugify_limits_and_rules(self):
        # 4 words limit, lowercase, no consecutive dashes/hyphens
        md = "# This Is A Heading With Too Many Words!"
        html = MarkdownParser.parse(md)
        self.assertIn('id="this-is-a-heading"', html)

        md = "# Hello — World!!! - Nice -- To — Meet You"
        html = MarkdownParser.parse(md)
        self.assertIn('id="hello-world-nice-to"', html)

    def test_headings_slugify_duplicates(self):
        # Duplicate resolution suffixing
        md = "# Hello World\n# Hello World\n# Hello World"
        html = MarkdownParser.parse(md)
        self.assertIn('id="hello-world"', html)
        self.assertIn('id="hello-world-1"', html)
        self.assertIn('id="hello-world-2"', html)

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



    def test_wikilink_parsing(self):
        # Normal wikilinks
        md = "See [[apple-pie]] and [[banana-cake|banana cake recipe]]"
        html = MarkdownParser.parse(md)
        self.assertIn('<a href="/w/apple-pie" class="wikilink">apple-pie</a>', html)
        self.assertIn('<a href="/w/banana-cake" class="wikilink">banana cake recipe</a>', html)

        # Wikilinks inside skip tags (code block, inline code, links) should NOT be parsed
        md_code = "```text\n[[apple-pie]]\n```\n`[[banana-cake]]`\n[link [[target]]](http://test.com)"
        html_code = MarkdownParser.parse(md_code)
        self.assertNotIn('class="wikilink"', html_code)
        self.assertIn('[[apple-pie]]', html_code)
        self.assertIn('[[banana-cake]]', html_code)

    def test_rewrite_wikilinks(self):
        wikilink_map = {
            "apple-pie": ["recipes/apple-pie.md"],
            "apple-pie.md": ["recipes/apple-pie.md"],
            "recipes/apple-pie": ["recipes/apple-pie.md"],
            "recipes/apple-pie.md": ["recipes/apple-pie.md"],
            "desserts": ["a/desserts.md", "b/desserts.md"],
            "a/desserts": ["a/desserts.md"],
            "a/desserts.md": ["a/desserts.md"],
            "b/desserts": ["b/desserts.md"],
            "b/desserts.md": ["b/desserts.md"],
        }

        # Basic rewrite
        html = '<a href="/w/apple-pie" class="wikilink">apple-pie</a>'
        rewritten = MarkdownParser.rewrite_wikilinks(html, wikilink_map)
        self.assertEqual(rewritten, '<a href="/_/recipes/apple-pie.md" class="wikilink">apple-pie</a>')

        # Custom label rewrite
        html = '<a href="/w/apple-pie" class="wikilink">Custom Label</a>'
        rewritten = MarkdownParser.rewrite_wikilinks(html, wikilink_map)
        self.assertEqual(rewritten, '<a href="/_/recipes/apple-pie.md" class="wikilink">Custom Label</a>')

        # Rewrite with anchor
        html = '<a href="/w/apple-pie#Ingredients" class="wikilink">apple-pie</a>'
        rewritten = MarkdownParser.rewrite_wikilinks(html, wikilink_map)
        self.assertEqual(rewritten, '<a href="/_/recipes/apple-pie.md#ingredients" class="wikilink">apple-pie</a>')

        # Broken link rewrite (unknown file)
        html = '<a href="/w/unknown-file" class="wikilink">unknown-file</a>'
        rewritten = MarkdownParser.rewrite_wikilinks(html, wikilink_map)
        self.assertEqual(rewritten, '<a href="#" class="wikilink broken-link" title="Page not found">unknown-file</a>')

        # Broken link rewrite (collision / ambiguous target)
        html = '<a href="/w/desserts" class="wikilink">desserts</a>'
        rewritten = MarkdownParser.rewrite_wikilinks(html, wikilink_map)
        self.assertEqual(rewritten, '<a href="#" class="wikilink broken-link" title="Page not found">desserts</a>')

        # Resolves uniquely when longer path suffix is specified
        html = '<a href="/w/a/desserts" class="wikilink">a/desserts</a>'
        rewritten = MarkdownParser.rewrite_wikilinks(html, wikilink_map)
        self.assertEqual(rewritten, '<a href="/_/a/desserts.md" class="wikilink">a/desserts</a>')

        html = '<a href="/w/b/desserts" class="wikilink">b/desserts</a>'
        rewritten = MarkdownParser.rewrite_wikilinks(html, wikilink_map)
        self.assertEqual(rewritten, '<a href="/_/b/desserts.md" class="wikilink">b/desserts</a>')

