import re
from markdown_it import MarkdownIt

from bs4 import BeautifulSoup, Tag

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

# Highlighting function
def highlight_code(code, lang, attrs):
    try:
        lexer = get_lexer_by_name(lang)
    except Exception:
        lexer = get_lexer_by_name("text")
    formatter = HtmlFormatter(nowrap=True)
    return highlight(code, lexer, formatter)

mdparser = MarkdownIt('commonmark', {"highlight": highlight_code}).enable('table').use(anchors_plugin, max_level=3).use(dollarmath_plugin, double_inline=True)

# Custom plugin to add target="_blank" to all <a> tags
def add_target_blank(md):
    def link_open_with_target_blank(tokens, idx, options, env):
        token = tokens[idx]

        # Ensure token.attrs exists
        if token.attrs is None:
            token.attrs = []

        # Add or overwrite 'target' attribute
        token.attrSet('target', '_blank')

        return md.renderer.renderToken(tokens, idx, options, env)

    md.renderer.rules['link_open'] = link_open_with_target_blank

# Apply the plugin
add_target_blank(mdparser)

def wrap_tables_and_images(dom):
    # Wrap tables
    for table in dom.find_all('table'):
        wrapper = dom.new_tag('div', **{'class': 'md-table'})
        table.replace_with(wrapper)
        wrapper.append(table)

    # Wrap images
    for img in dom.find_all('img'):
        wrapper = dom.new_tag('div', **{'class': 'md-image'})
        img.replace_with(wrapper)
        wrapper.append(img)

def simplify_anchor_text(dom):
    for a in dom.find_all('a', href=True):
        href = a['href'].strip()
        text = a.get_text(strip=True)

        if text == href:
            if href.startswith('http://'):
                a.string = href[len('http://'):]
            elif href.startswith('https://'):
                a.string = href[len('https://'):]

class MarkdownParser:
    
    @staticmethod
    def _clean_math(content: str) -> str:
        # Merge all lines inside $$...$$, remove leading > and whitespace from each line
        def replacer(m):
            inner = m.group(1)
            # Remove leading > and spaces from each line
            lines = [re.sub(r'^\s*>?\s?', '', line) for line in inner.splitlines()]
            merged = ' '.join(lines)
            return '$$' + merged.replace('\\', '\\\\') + '$$'
        content = re.sub(r'\$\$(.*?)\$\$', replacer, content, flags=re.DOTALL)
        return content

    @staticmethod
    def parse(mdcontent: str) -> str:
        mdcontent = MarkdownParser._clean_math(mdcontent)
        html = mdparser.render(mdcontent)
        dom = BeautifulSoup(html, 'html.parser')
        wrap_tables_and_images(dom)
        simplify_anchor_text(dom)
        return str(dom)
