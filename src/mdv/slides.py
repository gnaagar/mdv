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


@dataclass(frozen=True)
class SlideBlock:
    kind: str
    html: str = ""
    columns: tuple[str, ...] = ()
    ratios: tuple[float, ...] = ()


@dataclass(frozen=True)
class SlideDocument:
    metadata: dict[str, str]
    slides: tuple[tuple[SlideBlock, ...], ...]


_FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<body>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_SLIDE_SEPARATOR_RE = re.compile(r"^[ \t]*-{3,}[ \t]*$", re.MULTILINE)
_COL_START_RE = re.compile(r"^\s*<!--\s*col-start\s+([^>]+?)\s*-->\s*$")
_COL_SEP_RE = re.compile(r"^\s*<!--\s*col-sep\s*-->\s*$")
_COL_END_RE = re.compile(r"^\s*<!--\s*col-end\s*-->\s*$")
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


def _render_markdown(content: str) -> str:
    return MarkdownParser.parse(content.strip()) if content.strip() else ""


def _parse_ratios(value: str) -> tuple[float, ...]:
    try:
        ratios = tuple(float(part.strip()) for part in value.split(":"))
    except ValueError as error:
        raise SlidesParseError(f"Invalid column ratio: {value}") from error
    if not ratios or any(ratio <= 0 for ratio in ratios):
        raise SlidesParseError(f"Column ratios must be positive: {value}")
    return ratios


def _parse_slide(content: str) -> tuple[SlideBlock, ...]:
    blocks: list[SlideBlock] = []
    full_width: list[str] = []
    columns: list[list[str]] | None = None
    ratios: tuple[float, ...] = ()

    def flush_full_width() -> None:
        html = _render_markdown("\n".join(full_width))
        if html:
            blocks.append(SlideBlock(kind="markdown", html=html))
        full_width.clear()

    for line in content.splitlines():
        start = _COL_START_RE.match(line)
        if start:
            if columns is not None:
                raise SlidesParseError("A column block cannot start inside another column block.")
            flush_full_width()
            ratios = _parse_ratios(start.group(1))
            columns = [[]]
            continue
        if _COL_SEP_RE.match(line):
            if columns is None:
                raise SlidesParseError("Found col-sep outside a column block.")
            columns.append([])
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
                )
            )
            columns = None
            ratios = ()
            continue
        (columns[-1] if columns is not None else full_width).append(line)

    if columns is not None:
        raise SlidesParseError("A column block is missing its col-end directive.")
    flush_full_width()
    return tuple(blocks)


def _validate_slide_headings(content: str, slide_number: int) -> None:
    """Require an H2 slide title and reserve lower headings for slide content."""
    lines = content.splitlines()
    first_content = next((index for index, line in enumerate(lines) if line.strip()), None)
    if first_content is None or not re.match(r"^[ \t]*##[ \t]+", lines[first_content]):
        raise SlidesParseError(f"Slide {slide_number} must begin with a ## heading.")

    in_fence = False
    for index, line in enumerate(lines):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _ATX_HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        if level == 1 or (level == 2 and index != first_content):
            raise SlidesParseError(
                f"Slide {slide_number} may use ## only as its opening heading; use ### or lower afterward."
            )


def parse_slides(source: str) -> SlideDocument:
    """Parse an md-slides source document into renderable slides."""
    metadata, body = _parse_front_matter(source)
    parts = [part for part in _SLIDE_SEPARATOR_RE.split(body) if part.strip()]
    for number, part in enumerate(parts, start=1):
        _validate_slide_headings(part, number)
    slides = tuple(_parse_slide(part) for part in parts)
    if not slides:
        raise SlidesParseError("The presentation does not contain any slide content.")
    return SlideDocument(metadata=metadata, slides=slides)


_env = Environment(loader=PackageLoader("mdv", "templates"), autoescape=select_autoescape())
_url_map = Map([Rule("/", endpoint="presentation"), Rule("/favicon.ico", endpoint="favicon")])


class SlidesApp:
    """Small WSGI app intentionally isolated from the workspace viewer."""

    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path
        self.url_map = _url_map
        static_dir = files("mdv").joinpath("static")
        self.wsgi_app = SharedDataMiddleware(self.wsgi_app, {"/static": str(static_dir)}, cache_timeout=86400)

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
