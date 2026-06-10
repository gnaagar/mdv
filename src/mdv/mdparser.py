import re
import html
from html.parser import HTMLParser

from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from mdit_py_plugins.front_matter import front_matter_plugin

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

_html_formatter = HtmlFormatter(nowrap=True)


# Highlighting function
def highlight_code(code, lang, attrs):
    try:
        lexer = get_lexer_by_name(lang)
    except Exception:
        lexer = get_lexer_by_name("text")
    return highlight(code, lexer, _html_formatter)


mdparser = (
    MarkdownIt("commonmark", {"highlight": highlight_code})
    .enable("table")
    .use(anchors_plugin, max_level=3)
    .use(dollarmath_plugin, double_inline=True)
    .use(tasklists_plugin)
    .use(front_matter_plugin)
)


# Custom plugin to add target="_blank" only to external <a> tags
def add_target_blank(md):
    def link_open_with_target_blank(tokens, idx, options, env):
        token = tokens[idx]

        href = token.attrGet("href")
        if href and (href.startswith("http://") or href.startswith("https://")):
            if token.attrs is None:
                token.attrs = []
            token.attrSet("target", "_blank")

        return md.renderer.renderToken(tokens, idx, options, env)

    md.renderer.rules["link_open"] = link_open_with_target_blank


# Custom plugin to add source line numbers to all block elements
def inject_line_numbers(md):
    def core_inject(state):
        for token in state.tokens:
            if getattr(token, "map", None):
                if token.attrs is None:
                    token.attrs = []
                token.attrSet("data-source-line", str(token.map[0] + 1))

    md.core.ruler.push("inject_line_numbers", core_inject)


# Apply the plugins
add_target_blank(mdparser)
inject_line_numbers(mdparser)


class SanitizingHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.dangerous_tag_depth = 0

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in {
            "script",
            "iframe",
            "object",
            "embed",
            "applet",
            "meta",
            "link",
            "base",
            "form",
        }:
            self.dangerous_tag_depth += 1
            return
        if self.dangerous_tag_depth > 0:
            return

        cleaned_attrs = []
        for name, value in attrs:
            name_lower = name.lower()
            if name_lower.startswith("on"):
                continue
            if name_lower in ("href", "src"):
                val_lower = (value or "").strip().lower()
                if (
                    val_lower.startswith("javascript:")
                    or val_lower.startswith("vbscript:")
                    or val_lower.startswith("data:text/html")
                ):
                    continue
            cleaned_attrs.append((name, value))

        attr_str = ""
        if cleaned_attrs:
            attr_str = " " + " ".join(
                f'{k}="{html.escape(v)}"' if v is not None else k
                for k, v in cleaned_attrs
            )

        if tag_lower in {"img", "br", "hr", "input", "meta", "link"}:
            self.result.append(f"<{tag}{attr_str} />")
        else:
            self.result.append(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in {
            "script",
            "iframe",
            "object",
            "embed",
            "applet",
            "meta",
            "link",
            "base",
            "form",
        }:
            self.dangerous_tag_depth = max(0, self.dangerous_tag_depth - 1)
            return
        if self.dangerous_tag_depth > 0:
            return

        if tag_lower not in {"img", "br", "hr", "input", "meta", "link"}:
            self.result.append(f"</{tag}>")

    def handle_data(self, data):
        if self.dangerous_tag_depth == 0:
            self.result.append(data)

    def handle_entityref(self, name):
        if self.dangerous_tag_depth == 0:
            self.result.append(f"&{name};")

    def handle_charref(self, name):
        if self.dangerous_tag_depth == 0:
            self.result.append(f"&#{name};")


class MarkdownParser:
    _MATH_BLOCK_RE = re.compile(
        r"(?P<code_fence>```[\s\S]*?```|~~~[\s\S]*?~~~)|\$\$(?P<math>[\s\S]*?)\$\$",
        re.MULTILINE,
    )

    @staticmethod
    def _clean_math(content: str) -> str:
        # Merge all lines inside $$...$$, remove leading > and whitespace from each line
        # Skip math block processing if it's inside fenced code blocks
        def replacer(m: re.Match) -> str:
            if m.group("code_fence"):
                return m.group(0)
            inner = m.group("math")
            lines = [re.sub(r"^\s*>?\s?", "", line) for line in inner.splitlines()]
            merged = " ".join(lines)
            return "$$" + merged.replace("\\", "\\\\") + "$$"

        return MarkdownParser._MATH_BLOCK_RE.sub(replacer, content)

    @staticmethod
    def parse(mdcontent: str) -> str:
        mdcontent = MarkdownParser._clean_math(mdcontent)
        raw_html = mdparser.render(mdcontent)

        # Sanitize HTML using lightweight stdlib parser
        parser = SanitizingHTMLParser()
        parser.feed(raw_html)
        return "".join(parser.result)

    @staticmethod
    def extract_frontmatter(content: str) -> dict[str, str]:
        # Match standard yaml frontmatter starting at the beginning of the file
        match = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n', content, re.DOTALL)
        if not match:
            return {}
        frontmatter_content = match.group(1)
        metadata = {}
        for line in frontmatter_content.splitlines():
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip()
                # Strip outer quotes if present
                if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
                    val = val[1:-1]
                metadata[key] = val
        return metadata

    @staticmethod
    def rewrite_doc_id_links(html_content: str, doc_to_file_map: dict[str, str]) -> str:
        def replacer(match: re.Match) -> str:
            quote = match.group(1)
            url = match.group(2)
            
            # The URL starts with /d/
            rest = url[3:]
                
            if "#" in rest:
                doc_id, anchor = rest.split("#", 1)
                anchor = "#" + anchor
            else:
                doc_id = rest
                anchor = ""
                
            if doc_id in doc_to_file_map:
                new_path = "/_/" + doc_to_file_map[doc_id] + anchor
                return f'href={quote}{new_path}{quote}'
                
            return match.group(0)

        pattern = r'href=(["\'])(/d/[^\s"\'>]+)\1'
        return re.sub(pattern, replacer, html_content)

