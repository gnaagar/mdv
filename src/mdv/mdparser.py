import re
from markdown_it import MarkdownIt

from bs4 import BeautifulSoup, Tag

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.tasklists import tasklists_plugin

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

mdparser = MarkdownIt('commonmark', {"highlight": highlight_code}).enable('table').use(anchors_plugin, max_level=3).use(dollarmath_plugin, double_inline=True).use(tasklists_plugin)

# Custom plugin to add target="_blank" only to external <a> tags
def add_target_blank(md):
    def link_open_with_target_blank(tokens, idx, options, env):
        token = tokens[idx]
        
        href = token.attrGet('href')
        if href and (href.startswith('http://') or href.startswith('https://')):
            # Ensure token.attrs exists
            if token.attrs is None:
                token.attrs = []

            # Add or overwrite 'target' attribute
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
        MarkdownParser._post_process_tasklists(dom)
        return str(dom)

    @staticmethod
    def _post_process_tasklists(dom: BeautifulSoup):
        for li in dom.find_all('li'):
            checkbox = li.find('input', type='checkbox')
            if checkbox:
                checkbox['disabled'] = ''  # Disable the checkbox
                if 'checked' in checkbox.attrs:
                    li['class'] = li.get('class', []) + ['task-completed']
