"""Parsing and serving for the standalone ``mdv --slides`` viewer."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
import re
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response

from mdv.mdparser import MarkdownParser


class SlidesParseError(ValueError):
    """Raised when a document does not follow the md-slides structure."""


ALLOWED_SLIDE_COLORS = {"yellow", "red", "green", "blue", "pink", "purple", "grey", "gray", "none"}


@dataclass(frozen=True)
class SlideBlock:
    kind: str
    html: str = ""
    columns: tuple[str, ...] = ()
    ratios: tuple[float, ...] = ()
    column_colors: tuple[str, ...] = ()
    is_numbered: bool = False
    orientation: str = "horizontal"


@dataclass(frozen=True)
class Slide:
    blocks: tuple[SlideBlock, ...]
    notes_html: str = ""

    def __iter__(self):
        return iter(self.blocks)

    def __getitem__(self, index):
        return self.blocks[index]

    def __len__(self):
        return len(self.blocks)


@dataclass(frozen=True)
class SlideDocument:
    metadata: dict[str, str]
    slides: tuple[Slide, ...]


_FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<body>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
# Canonical slide separator: <!-- slide-sep -->
# The old "---" form is no longer recognised; it renders as a plain <hr> in standard viewers.
_SLIDE_SEP_RE = re.compile(r"^\s*<!--\s*slide-sep\s*-->\s*$")
_SPEAKER_RE = re.compile(r"^\s*<!--\s*speaker(?:[\s:-].*?)?\s*-->\s*$", re.IGNORECASE)
_COL_START_RE = re.compile(r"^\s*<!--\s*col-start\s+([^>]+?)\s*-->\s*$")
_COL_SEP_RE = re.compile(r"^\s*<!--\s*col-sep(?:\s+([^>]+?))?\s*-->\s*$")
_COL_END_RE = re.compile(r"^\s*<!--\s*col-end\s*-->\s*$")
_FLOW_START_RE = re.compile(
    r"^\s*<!--\s*(flow(?:-start|-vertical)?|stack(?:-start)?)(?:[:\s]+([^>]+?))?\s*-->\s*$",
    re.IGNORECASE,
)
_FLOW_SEP_RE = re.compile(r"^\s*<!--\s*(?:flow-sep|step-sep|step)(?:\s+([^>]+?))?\s*-->\s*$", re.IGNORECASE)
_FLOW_END_RE = re.compile(
    r"^\s*<!--\s*(?:/(?:flow|stack)|(?:flow|stack)-end)\s*-->\s*$",
    re.IGNORECASE,
)
_COL_COLOR_RE = re.compile(
    r"^\s*<!--\s*(?:col-color[:\s]+|col-accent[:\s]+|accent[:\s]+|col-)(yellow|red|green|blue|pink|purple|grey|gray)\s*-->\s*$",
    re.IGNORECASE,
)
_QUOTE_DIRECTIVE_RE = re.compile(
    r"^\s*<!--\s*(?:(?:quote-color|quote|blockquote-color|blockquote|quote-)[:\s]+)?(yellow|red|green|blue|pink|purple|grey|gray)\s*-->\s*$",
    re.IGNORECASE,
)
_INLINE_QUOTE_DIRECTIVE_RE = re.compile(
    r"^[ \t]*>[ \t]*<!--\s*(?:(?:quote-color|quote|blockquote-color|blockquote|color|quote-)[:\s]+)?(yellow|red|green|blue|pink|purple|grey|gray)\s*-->[ \t]*(.*)$",
    re.IGNORECASE,
)
# Canonical text-color syntax: <!--red-->text<!--/red-->  (no spaces, no "color:" prefix).
# This is the ONLY supported form; all legacy aliases have been removed.
_TEXT_COLOR_RE = re.compile(
    r"<!--(yellow|red|green|blue|pink|purple|grey|gray)-->([\s\S]*?)<!--/\1-->",
    re.IGNORECASE,
)
_ATX_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+")
_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")


def _parse_front_matter(source: str) -> tuple[dict[str, str], str]:
    match = _FRONT_MATTER_RE.match(source)
    if not match:
        raise SlidesParseError("A slides document must start with a YAML frontmatter block.")

    metadata: dict[str, str] = {}
    for line in match.group("body").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            raise SlidesParseError(f"Invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        metadata[key.strip()] = value
    return metadata, source[match.end():]


_SLIDE_QUOTE_TOKEN_RE = re.compile(
    r"<blockquote([^>]*)>((?:(?!<\/blockquote>)[\s\S])*?)%%SLIDE_QUOTE_(yellow|red|green|blue|pink|purple|grey|gray)%%[ \t]*((?:(?!<\/blockquote>)[\s\S])*?)<\/blockquote>",
    re.IGNORECASE,
)
_SLIDE_TEXT_BLOCK_P_RE = re.compile(
    r"<p[^>]*>\s*%%SLIDE_TEXT_START_(yellow|red|green|blue|pink|purple|grey|gray)%%\s*<\/p>([\s\S]*?)<p[^>]*>\s*%%SLIDE_TEXT_END%%\s*<\/p>",
    re.IGNORECASE,
)
_SLIDE_TEXT_TOKEN_RE = re.compile(
    r"%%SLIDE_TEXT_START_(yellow|red|green|blue|pink|purple|grey|gray)%%([\s\S]*?)%%SLIDE_TEXT_END%%",
    re.IGNORECASE,
)


def _preprocess_slide_markdown(content: str) -> str:
    lines = content.splitlines(keepends=True)
    chunks: list[tuple[bool, str]] = []
    current: list[str] = []
    fence_char: str | None = None
    fence_len = 0
    in_code = False

    for line in lines:
        match = _FENCE_RE.match(line)
        if match:
            char = match.group(1)[0]
            length = len(match.group(1))
            if fence_char is None:
                if current:
                    chunks.append((False, "".join(current)))
                    current = []
                fence_char = char
                fence_len = length
                in_code = True
                current.append(line)
                continue
            elif char == fence_char and length >= fence_len:
                current.append(line)
                chunks.append((True, "".join(current)))
                current = []
                fence_char = None
                fence_len = 0
                in_code = False
                continue
        current.append(line)
    if current:
        chunks.append((in_code, "".join(current)))

    def text_color_replacer(match: re.Match) -> str:
        color = match.group(1).lower()
        inner = match.group(2)
        return f"%%SLIDE_TEXT_START_{color}%%{inner}%%SLIDE_TEXT_END%%"

    processed_chunks: list[str] = []
    for is_code, chunk in chunks:
        if is_code:
            processed_chunks.append(chunk)
            continue

        text = _TEXT_COLOR_RE.sub(text_color_replacer, chunk)
        chunk_lines = text.splitlines(keepends=True)
        processed_lines: list[str] = []
        pending_quote_color: str | None = None

        for line in chunk_lines:
            stripped = line.strip()

            inline_quote_match = _INLINE_QUOTE_DIRECTIVE_RE.match(line)
            if inline_quote_match:
                color = inline_quote_match.group(1).lower()
                rest = inline_quote_match.group(2)
                processed_lines.append(f"> %%SLIDE_QUOTE_{color}%% {rest}\n")
                pending_quote_color = None
                continue

            quote_match = _QUOTE_DIRECTIVE_RE.match(line)
            if quote_match and not stripped.startswith(">"):
                pending_quote_color = quote_match.group(1).lower()
                continue

            if pending_quote_color:
                if stripped.startswith(">"):
                    quote_rest = line.lstrip()[1:]
                    processed_lines.append(f"> %%SLIDE_QUOTE_{pending_quote_color}%%{quote_rest}")
                    pending_quote_color = None
                    continue
                elif not stripped:
                    processed_lines.append(line)
                    continue
                else:
                    pending_quote_color = None

            processed_lines.append(line)
        processed_chunks.append("".join(processed_lines))

    return "".join(processed_chunks)


def _render_markdown(content: str) -> str:
    if not content.strip():
        return ""
    preprocessed = _preprocess_slide_markdown(content.strip())
    raw_html = MarkdownParser.parse(preprocessed)

    def quote_replacer(match: re.Match) -> str:
        attrs = match.group(1)
        before = match.group(2)
        color = match.group(3).lower()
        after = match.group(4)
        if 'class="' in attrs:
            attrs = re.sub(r'class="([^"]*)"', rf'class="\1 slide-quote-{color}"', attrs)
        else:
            attrs = f'{attrs} class="slide-quote-{color}"'
        return f"<blockquote{attrs}>{before}{after}</blockquote>"

    html = _SLIDE_QUOTE_TOKEN_RE.sub(quote_replacer, raw_html)
    html = re.sub(r"%%SLIDE_QUOTE_(yellow|red|green|blue|pink|purple|grey|gray)%%[ \t]*", "", html)

    def block_p_replacer(match: re.Match) -> str:
        color = match.group(1).lower()
        inner = match.group(2)
        return f'<div class="slide-text-{color}">{inner}</div>'

    html = _SLIDE_TEXT_BLOCK_P_RE.sub(block_p_replacer, html)

    def text_token_replacer(match: re.Match) -> str:
        color = match.group(1).lower()
        inner = match.group(2)
        inner = re.sub(r"^(\s*<br\s*\/?>\s*)+", "", inner)
        inner = re.sub(r"(\s*<br\s*\/?>\s*)+$", "", inner)
        if re.search(r"<(?:p|h[1-6]|ul|ol|li|blockquote|table|pre|div)\b", inner):
            return f'<div class="slide-text-{color}">{inner}</div>'
        return f'<span class="slide-text-{color}">{inner}</span>'

    html = _SLIDE_TEXT_TOKEN_RE.sub(text_token_replacer, html)
    return html


def _parse_ratios(value: str) -> tuple[float, ...]:
    try:
        ratios = tuple(float(part.strip()) for part in value.split(":"))
    except ValueError as error:
        raise SlidesParseError(f"Invalid column ratio: {value}") from error
    if not ratios or any(ratio <= 0 for ratio in ratios):
        raise SlidesParseError(f"Column ratios must be positive: {value}")
    return ratios


def _parse_column_directive(value: str) -> tuple[tuple[float, ...], tuple[str, ...]]:
    tokens = value.strip().split()
    ratios = _parse_ratios(tokens[0])
    count = len(ratios)
    colors: list[str] = [""] * count
    if len(tokens) > 1:
        color_parts = [p.strip().lower() for p in tokens[1].split(":")]
        for p in color_parts:
            if p and p not in ALLOWED_SLIDE_COLORS:
                raise SlidesParseError(
                    f"Invalid column color '{p}'. Allowed colors: {', '.join(sorted(ALLOWED_SLIDE_COLORS))}."
                )
        if len(color_parts) == 1 and color_parts[0]:
            colors = [color_parts[0]] * count
        elif len(color_parts) == count:
            colors = color_parts
        else:
            raise SlidesParseError(
                f"Column block declares {count} columns but received {len(color_parts)} colors: {tokens[1]}."
            )
    return ratios, tuple(colors)


def _parse_flow_directive(keyword: str, value: str | None) -> tuple[str, list[str]]:
    kw = keyword.lower()
    orientation = "vertical" if ("stack" in kw or "-vertical" in kw) else "horizontal"
    if not value or not value.strip():
        return orientation, []

    raw = value.strip()
    if raw.startswith(":"):
        raw = raw[1:].strip()

    parts = raw.split()
    color_part = raw
    if parts:
        first = parts[0].lower().lstrip(":")
        if first in ("vertical", "v", "stack", "col", "column"):
            orientation = "vertical"
            color_part = " ".join(parts[1:])
        elif first in ("horizontal", "h", "row"):
            orientation = "horizontal"
            color_part = " ".join(parts[1:])

    color_part = color_part.strip().lstrip(":")
    if not color_part:
        return orientation, []

    color_tokens = [p.strip().lower() for p in color_part.split(":")]
    for c in color_tokens:
        if c and c not in ALLOWED_SLIDE_COLORS:
            raise SlidesParseError(
                f"Invalid flow color '{c}'. Allowed colors: {', '.join(sorted(ALLOWED_SLIDE_COLORS))}."
            )
    return orientation, color_tokens


def _split_markdown_list(content: str) -> tuple[bool, list[str]]:
    lines = content.splitlines()
    items: list[list[str]] = []
    item_re = re.compile(r"^(?:[-*+]|\d+[.)])[ \t]+(.*)$")

    first_non_empty = next((l for l in lines if l.strip()), None)
    is_numbered = bool(re.match(r"^\s*\d+[.)]", first_non_empty)) if first_non_empty else False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if items:
                items[-1].append(line)
            continue
        indent_len = len(line) - len(line.lstrip(" \t"))
        match = item_re.match(stripped)
        if indent_len <= 1 and match:
            items.append([match.group(1)])
        else:
            if items:
                items[-1].append(line)
            else:
                items.append([line])

    return is_numbered, ["\n".join(it).strip() for it in items if any(l.strip() for l in it)]


def _parse_slide(content: str) -> tuple[SlideBlock, ...]:
    blocks: list[SlideBlock] = []
    full_width: list[str] = []
    columns: list[list[str]] | None = None
    ratios: tuple[float, ...] = ()
    column_colors: list[str] = []
    default_colors: tuple[str, ...] = ()

    flow_steps: list[list[str]] | None = None
    flow_step_colors: list[str] = []
    default_flow_colors: list[str] = []
    raw_flow_colors_arg: str = ""
    flow_orientation: str = "horizontal"
    flow_has_explicit_sep: bool = False

    def flush_full_width() -> None:
        html = _render_markdown("\n".join(full_width))
        if html:
            blocks.append(SlideBlock(kind="markdown", html=html))
        full_width.clear()

    fence_char: str | None = None
    fence_len = 0

    for line in content.splitlines():
        target = columns[-1] if columns is not None else (flow_steps[-1] if flow_steps is not None else full_width)
        match = _FENCE_RE.match(line)
        if match:
            char = match.group(1)[0]
            length = len(match.group(1))
            if fence_char is None:
                fence_char = char
                fence_len = length
            elif char == fence_char and length >= fence_len:
                fence_char = None
                fence_len = 0
            target.append(line)
            continue

        if fence_char is not None:
            target.append(line)
            continue

        start = _COL_START_RE.match(line)
        if start:
            if flow_steps is not None:
                raise SlidesParseError("A column block cannot start inside a flow block.")
            if columns is not None:
                raise SlidesParseError("A column block cannot start inside another column block.")
            flush_full_width()
            ratios, default_colors = _parse_column_directive(start.group(1))
            columns = [[]]
            column_colors = [default_colors[0] if default_colors else ""]
            continue
        sep = _COL_SEP_RE.match(line)
        if sep:
            if columns is None:
                raise SlidesParseError("Found col-sep outside a column block.")
            columns.append([])
            sep_color = sep.group(1).strip().lower() if sep.group(1) else ""
            if sep_color and sep_color not in ALLOWED_SLIDE_COLORS:
                raise SlidesParseError(
                    f"Invalid column color '{sep_color}'. Allowed colors: {', '.join(sorted(ALLOWED_SLIDE_COLORS))}."
                )
            next_idx = len(columns) - 1
            color_to_use = sep_color or (default_colors[next_idx] if next_idx < len(default_colors) else "")
            column_colors.append(color_to_use)
            continue
        col_color = _COL_COLOR_RE.match(line)
        if col_color and columns is not None:
            color = col_color.group(1).lower()
            column_colors[-1] = color
            continue
        if _COL_END_RE.match(line):
            if columns is None:
                raise SlidesParseError("Found col-end without a matching col-start.")
            if len(columns) != len(ratios):
                raise SlidesParseError(
                    f"Column block declares {len(ratios)} columns but contains {len(columns)}."
                )
            blocks.append(
                SlideBlock(
                    kind="columns",
                    columns=tuple(_render_markdown("\n".join(column)) for column in columns),
                    ratios=ratios,
                    column_colors=tuple(column_colors),
                )
            )
            columns = None
            ratios = ()
            column_colors = []
            default_colors = ()
            continue

        flow_start = _FLOW_START_RE.match(line)
        if flow_start:
            if columns is not None:
                raise SlidesParseError("A flow block cannot start inside a column block.")
            if flow_steps is not None:
                raise SlidesParseError("A flow block cannot start inside another flow block.")
            flush_full_width()
            keyword = flow_start.group(1)
            raw_flow_colors_arg = flow_start.group(2) or ""
            flow_orientation, default_flow_colors = _parse_flow_directive(keyword, raw_flow_colors_arg)
            flow_steps = [[]]
            flow_step_colors = [default_flow_colors[0] if default_flow_colors else ""]
            flow_has_explicit_sep = False
            continue

        flow_sep = _FLOW_SEP_RE.match(line)
        if flow_sep:
            if flow_steps is None:
                raise SlidesParseError("Found flow-sep outside a flow block.")
            flow_has_explicit_sep = True
            flow_steps.append([])
            sep_color = flow_sep.group(1).strip().lower() if flow_sep.group(1) else ""
            if sep_color and sep_color not in ALLOWED_SLIDE_COLORS:
                raise SlidesParseError(
                    f"Invalid flow color '{sep_color}'. Allowed colors: {', '.join(sorted(ALLOWED_SLIDE_COLORS))}."
                )
            next_idx = len(flow_steps) - 1
            if len(default_flow_colors) == 1:
                color_to_use = sep_color or default_flow_colors[0]
            else:
                color_to_use = sep_color or (default_flow_colors[next_idx] if next_idx < len(default_flow_colors) else "")
            flow_step_colors.append(color_to_use)
            continue

        if _FLOW_END_RE.match(line):
            if flow_steps is None:
                raise SlidesParseError("Found flow-end without a matching flow directive.")

            if flow_has_explicit_sep:
                steps_raw = ["\n".join(step).strip() for step in flow_steps]
                steps = [s for s in steps_raw if s]
                is_numbered = False
            else:
                raw_body = "\n".join(flow_steps[0]).strip()
                is_numbered, steps = _split_markdown_list(raw_body)
                if not steps and raw_body:
                    steps = [raw_body]

            count = len(steps)
            if default_flow_colors and not flow_has_explicit_sep:
                if len(default_flow_colors) == 1:
                    resolved_colors = tuple(default_flow_colors * count)
                elif len(default_flow_colors) == count:
                    resolved_colors = tuple(default_flow_colors)
                else:
                    raise SlidesParseError(
                        f"Flow block declares {len(default_flow_colors)} colors but contains {count} steps: {raw_flow_colors_arg}."
                    )
            elif flow_has_explicit_sep and default_flow_colors:
                if len(default_flow_colors) == 1:
                    resolved_colors = tuple(
                        (flow_step_colors[i] if i < len(flow_step_colors) and flow_step_colors[i] else default_flow_colors[0])
                        for i in range(count)
                    )
                elif len(default_flow_colors) == count:
                    resolved_colors = tuple(
                        (flow_step_colors[i] if i < len(flow_step_colors) and flow_step_colors[i] else default_flow_colors[i])
                        for i in range(count)
                    )
                else:
                    raise SlidesParseError(
                        f"Flow block declares {len(default_flow_colors)} colors but contains {count} steps: {raw_flow_colors_arg}."
                    )
            elif flow_step_colors:
                resolved_colors = tuple(
                    (flow_step_colors[i] if i < len(flow_step_colors) else "") for i in range(count)
                )
            else:
                resolved_colors = ("",) * count

            blocks.append(
                SlideBlock(
                    kind="flow",
                    columns=tuple(_render_markdown(step) for step in steps),
                    column_colors=resolved_colors,
                    is_numbered=is_numbered,
                    orientation=flow_orientation,
                )
            )
            flow_steps = None
            flow_step_colors = []
            default_flow_colors = []
            raw_flow_colors_arg = ""
            flow_orientation = "horizontal"
            flow_has_explicit_sep = False
            continue

        target.append(line)

    if columns is not None:
        raise SlidesParseError("A column block is missing its col-end directive.")
    if flow_steps is not None:
        raise SlidesParseError("A flow block is missing its /flow directive.")
    flush_full_width()
    return tuple(blocks)


def _validate_slide_headings(content: str, slide_number: int) -> None:
    """Require an H2 slide title and reserve lower headings for slide content."""
    lines = content.splitlines()
    first_content = next((index for index, line in enumerate(lines) if line.strip()), None)
    if first_content is None or not re.match(r"^[ \t]*##[ \t]+", lines[first_content]):
        raise SlidesParseError(f"Slide {slide_number} must begin with a ## heading.")

    fence_char: str | None = None
    fence_len = 0
    for index, line in enumerate(lines):
        match = _FENCE_RE.match(line)
        if match:
            char = match.group(1)[0]
            length = len(match.group(1))
            if fence_char is None:
                fence_char = char
                fence_len = length
            elif char == fence_char and length >= fence_len:
                fence_char = None
                fence_len = 0
            continue
        if fence_char is not None:
            continue
        heading_match = _ATX_HEADING_RE.match(line)
        if not heading_match:
            continue
        level = len(heading_match.group(1))
        if level == 1 or (level == 2 and index != first_content):
            raise SlidesParseError(
                f"Slide {slide_number} may use ## only as its opening heading; use ### or lower afterward."
            )


def _split_slide_notes(part: str) -> tuple[str, str]:
    lines = part.splitlines()
    fence_char: str | None = None
    fence_len = 0
    for index, line in enumerate(lines):
        match = _FENCE_RE.match(line)
        if match:
            char = match.group(1)[0]
            length = len(match.group(1))
            if fence_char is None:
                fence_char = char
                fence_len = length
            elif char == fence_char and length >= fence_len:
                fence_char = None
                fence_len = 0
            continue
        if fence_char is None and _SPEAKER_RE.match(line):
            slide_content = "\n".join(lines[:index])
            notes_content = "\n".join(lines[index + 1:])
            return slide_content, notes_content
    return part, ""


def _split_slides(body: str) -> list[str]:
    parts: list[str] = []
    current_lines: list[str] = []
    fence_char: str | None = None
    fence_len = 0

    for line in body.splitlines(keepends=True):
        match = _FENCE_RE.match(line)
        if match:
            char = match.group(1)[0]
            length = len(match.group(1))
            if fence_char is None:
                fence_char = char
                fence_len = length
            elif char == fence_char and length >= fence_len:
                fence_char = None
                fence_len = 0
            current_lines.append(line)
            continue

        if fence_char is None and _SLIDE_SEP_RE.match(line):
            part = "".join(current_lines)
            if part.strip():
                parts.append(part)
            current_lines = []
        else:
            current_lines.append(line)

    part = "".join(current_lines)
    if part.strip():
        parts.append(part)
    return parts


def parse_slides(source: str) -> SlideDocument:
    """Parse an md-slides source document into renderable slides."""
    metadata, body = _parse_front_matter(source)
    parts = _split_slides(body)
    slides: list[Slide] = []
    for number, part in enumerate(parts, start=1):
        slide_body, notes_body = _split_slide_notes(part)
        _validate_slide_headings(slide_body, number)
        blocks = _parse_slide(slide_body)
        notes_html = _render_markdown(notes_body) if notes_body.strip() else ""
        slides.append(Slide(blocks=blocks, notes_html=notes_html))
    if not slides:
        raise SlidesParseError("The presentation does not contain any slide content.")
    return SlideDocument(metadata=metadata, slides=tuple(slides))


_env = Environment(loader=PackageLoader("mdv", "templates"), autoescape=select_autoescape())
_url_map = Map([Rule("/", endpoint="presentation"), Rule("/favicon.ico", endpoint="favicon")])


class SlidesApp:
    """Small WSGI app intentionally isolated from the workspace viewer."""

    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path
        self.url_map = _url_map
        static_dir = files("mdv").joinpath("static")
        self.wsgi_app = SharedDataMiddleware(self.wsgi_app, {"/static": str(static_dir)}, cache_timeout=0)

    def on_presentation(self, request: Request) -> Response:
        document = parse_slides(self.source_path.read_text(encoding="utf-8"))
        html = _env.get_template("slides.html").render(document=document, source_name=self.source_path.name)
        return Response(html, mimetype="text/html")

    def on_favicon(self, request: Request) -> Response:
        return Response(status=302, headers={"Location": "/static/favicon.svg"})

    def dispatch(self, request: Request) -> Response | HTTPException:
        try:
            endpoint, values = self.url_map.bind_to_environ(request.environ).match()
            return getattr(self, f"on_{endpoint}")(request, **values)
        except NotFound:
            return Response("Not found", status=404, mimetype="text/plain")
        except SlidesParseError as error:
            return Response(f"Invalid slides document: {error}", status=422, mimetype="text/plain")
        except FileNotFoundError:
            return Response("Slides file not found", status=404, mimetype="text/plain")

    def wsgi_app(self, environ: dict[str, Any], start_response: Any) -> Any:
        response = self.dispatch(Request(environ))
        return response(environ, start_response)

    def __call__(self, environ: dict[str, Any], start_response: Any) -> Any:
        return self.wsgi_app(environ, start_response)
