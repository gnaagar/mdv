import re
import html
from html.parser import HTMLParser

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.tasklists import tasklists_plugin

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

mdparser = MarkdownIt('commonmark', {"highlight": highlight_code}).enable('table').use(anchors_plugin, max_level=3).use(dollarmath_plugin, double_inline=True).use(tasklists_plugin)

# Custom plugin to add target="_blank" only to external <a> tags
def add_target_blank(md):
    def link_open_with_target_blank(tokens, idx, options, env):
        token = tokens[idx]
        
        href = token.attrGet('href')
        if href and (href.startswith('http://') or href.startswith('https://')):
            if token.attrs is None:
                token.attrs = []
            token.attrSet('target', '_blank')

        return md.renderer.renderToken(tokens, idx, options, env)

    md.renderer.rules['link_open'] = link_open_with_target_blank

# Custom plugin to add source line numbers to all block elements
def inject_line_numbers(md):
    def core_inject(state):
        for token in state.tokens:
            if getattr(token, 'map', None):
                if token.attrs is None:
                    token.attrs = []
                token.attrSet('data-source-line', str(token.map[0] + 1))
    
    md.core.ruler.push('inject_line_numbers', core_inject)

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
        if tag_lower in {'script', 'iframe', 'object', 'embed', 'applet', 'meta', 'link', 'base', 'form'}:
            self.dangerous_tag_depth += 1
            return
        if self.dangerous_tag_depth > 0:
            return

        cleaned_attrs = []
        for name, value in attrs:
            name_lower = name.lower()
            if name_lower.startswith('on'):
                continue
            if name_lower in ('href', 'src'):
                val_lower = (value or '').strip().lower()
                if val_lower.startswith('javascript:') or val_lower.startswith('vbscript:') or val_lower.startswith('data:text/html'):
                    continue
            cleaned_attrs.append((name, value))

        attr_str = ""
        if cleaned_attrs:
            attr_str = " " + " ".join(
                f'{k}="{html.escape(v)}"' if v is not None else k
                for k, v in cleaned_attrs
            )
        
        if tag_lower in {'img', 'br', 'hr', 'input', 'meta', 'link'}:
            self.result.append(f"<{tag}{attr_str} />")
        else:
            self.result.append(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in {'script', 'iframe', 'object', 'embed', 'applet', 'meta', 'link', 'base', 'form'}:
            self.dangerous_tag_depth = max(0, self.dangerous_tag_depth - 1)
            return
        if self.dangerous_tag_depth > 0:
            return

        if tag_lower not in {'img', 'br', 'hr', 'input', 'meta', 'link'}:
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
    
    @staticmethod
    def _clean_math(content: str) -> str:
        # Merge all lines inside $$...$$, remove leading > and whitespace from each line
        def replacer(m):
            inner = m.group(1)
            lines = [re.sub(r'^\s*>?\s?', '', line) for line in inner.splitlines()]
            merged = ' '.join(lines)
            return '$$' + merged.replace('\\', '\\\\') + '$$'
        content = re.sub(r'\$\$(.*?)\$\$', replacer, content, flags=re.DOTALL)
        return content

    @staticmethod
    def parse(mdcontent: str) -> str:
        mdcontent = MarkdownParser._clean_math(mdcontent)
        raw_html = mdparser.render(mdcontent)
        
        # Sanitize HTML using lightweight stdlib parser
        parser = SanitizingHTMLParser()
        parser.feed(raw_html)
        return "".join(parser.result)
