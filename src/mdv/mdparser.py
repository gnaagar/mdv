import re
import html
import urllib.parse
from html.parser import HTMLParser
from typing import Any

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


import threading

_slug_state = threading.local()


def custom_slugify(text: str, register: bool = True) -> str:
    text = text.lower()
    # Find all sequences of Unicode alphanumeric characters (excluding underscores)
    words = re.findall(r'[^\W_]+', text)
    words = words[:4]
    base_slug = "-".join(words)

    if not base_slug:
        base_slug = "heading"

    if not register:
        return base_slug

    used_slugs = getattr(_slug_state, "used_slugs", None)
    if used_slugs is None:
        used_slugs = {}
        _slug_state.used_slugs = used_slugs

    if base_slug not in used_slugs:
        used_slugs[base_slug] = 0
        slug = base_slug
    else:
        used_slugs[base_slug] += 1
        slug = f"{base_slug}-{used_slugs[base_slug]}"

    return slug


mdparser = (
    MarkdownIt("commonmark", {"highlight": highlight_code})
    .enable("table")
    .use(anchors_plugin, max_level=3, slug_func=custom_slugify)
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


WIKILINK_RE = re.compile(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]')


class SanitizingHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.dangerous_tag_depth = 0
        self.in_skip_wikilink_tag = 0
        self.skip_wikilink_tags = {"pre", "code", "a", "script", "style", "iframe", "textarea"}

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

        if tag_lower in self.skip_wikilink_tags:
            self.in_skip_wikilink_tag += 1

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

        if tag_lower in self.skip_wikilink_tags:
            self.in_skip_wikilink_tag = max(0, self.in_skip_wikilink_tag - 1)

        if tag_lower not in {"img", "br", "hr", "input", "meta", "link"}:
            self.result.append(f"</{tag}>")

    def handle_data(self, data):
        if self.dangerous_tag_depth == 0:
            if self.in_skip_wikilink_tag > 0:
                self.result.append(html.escape(data))
            else:
                last_idx = 0
                for match in WIKILINK_RE.finditer(data):
                    self.result.append(html.escape(data[last_idx:match.start()]))
                    target = match.group(1).strip()
                    if match.group(2):
                        label = match.group(2).strip()
                    else:
                        if "#" in target:
                            _, heading_part = target.split("#", 1)
                            heading_part = urllib.parse.unquote(heading_part.strip())
                            if len(heading_part) > 20:
                                heading_part = heading_part[:20] + "..."
                            label = heading_part
                        else:
                            label = target
                    safe_target = html.escape(target)
                    safe_label = html.escape(label)
                    self.result.append(f'<a href="/w/{safe_target}" class="wikilink">{safe_label}</a>')
                    last_idx = match.end()
                self.result.append(html.escape(data[last_idx:]))

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
        _slug_state.used_slugs = {}
        mdcontent = MarkdownParser._clean_math(mdcontent)
        raw_html = mdparser.render(mdcontent)

        # Sanitize HTML using lightweight stdlib parser
        parser = SanitizingHTMLParser()
        parser.feed(raw_html)
        return "".join(parser.result)



    @staticmethod
    def rewrite_wikilinks(html_content: str, resolve_func: Any) -> str:
        def replacer(match: re.Match) -> str:
            quote = match.group(1)
            target_url = match.group(2)
            label = match.group(3)
            
            # The target_url starts with /w/
            target = target_url[3:]
            
            if "#" in target:
                target_name, anchor = target.split("#", 1)
                anchor = "#" + anchor
            else:
                target_name = target
                anchor = ""
                
            target_name = html.unescape(urllib.parse.unquote(target_name))
            
            resolved_path = resolve_func(target_name)
            if not resolved_path:
                # Return styled broken link
                return f'<a href="#" class="wikilink broken-link" title="Page not found">{label}</a>'
                
            if anchor:
                decoded_anchor = html.unescape(urllib.parse.unquote(anchor[1:]))
                anchor_slug = custom_slugify(decoded_anchor, register=False)
                anchor = "#" + anchor_slug
                
            new_url = "/_/" + resolved_path + anchor
            return f'<a href="{new_url}" class="wikilink">{label}</a>'

        pattern = r'<a href=(["\'])(/w/[^"\'>]+)\1 class="wikilink">(.*?)</a>'
        return re.sub(pattern, replacer, html_content)


