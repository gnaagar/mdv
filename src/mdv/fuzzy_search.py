"""
fzf-style line-based search index for markdown files.

Every non-empty line across all files is indexed with its type
(heading, code, link, list, text). Search uses fast substring
matching first, then subsequence scoring as fallback.
"""

import re

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)')
_LINK_RE = re.compile(r'\[.*?\]\(.*?\)|https?://\S+')
_LIST_RE = re.compile(r'^\s*[-*+]\s|^\s*\d+\.\s')
_FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')


def _classify_line(raw_line, in_code_fence):
    """Return (line_type, heading_level, display_text, still_in_fence)."""
    stripped = raw_line.rstrip()

    # Code fence toggle
    if _FENCE_RE.match(stripped):
        return None, 0, None, not in_code_fence

    if in_code_fence:
        return 'code', 0, stripped, True

    # Heading
    m = _HEADING_RE.match(stripped)
    if m:
        return 'heading', len(m.group(1)), m.group(2).strip(), False

    # Link
    if _LINK_RE.search(stripped):
        return 'link', 0, stripped, False

    # List item
    if _LIST_RE.match(stripped):
        return 'list', 0, stripped, False

    # Plain text
    return 'text', 0, stripped, False


def _subsequence_score(query, text):
    """
    Check if query is a subsequence of text (case-insensitive).
    Returns a score based on tightness of match, or -1 if no match.
    Higher score = tighter/better match.
    """
    q_lower = query.lower()
    t_lower = text.lower()
    q_len = len(q_lower)
    t_len = len(t_lower)

    if q_len == 0:
        return -1
    if q_len > t_len:
        return -1

    # Find first valid subsequence match (greedy left-to-right)
    qi = 0
    positions = []
    for ti in range(t_len):
        if t_lower[ti] == q_lower[qi]:
            positions.append(ti)
            qi += 1
            if qi == q_len:
                break

    if qi < q_len:
        return -1  # Not a subsequence

    # Score: tighter span = higher score
    span = positions[-1] - positions[0] + 1
    # Base score from how tight the span is relative to query length
    tightness = q_len / span  # 1.0 = perfect (contiguous), lower = spread out
    score = int(tightness * 50)  # 0-50 range

    # Bonus: match starts at word boundary
    if positions[0] == 0 or t_lower[positions[0] - 1] in ' \t_-./':
        score += 10

    return max(score, 1)


def _substring_score(query_lower, text_lower, text_original):
    """
    Score a substring match. Returns score or -1 if no substring match.
    """
    idx = text_lower.find(query_lower)
    if idx == -1:
        return -1

    score = 100  # Base score for any substring match

    # Bonus: match at start of text or word boundary
    if idx == 0 or text_lower[idx - 1] in ' \t_-./':
        score += 20

    # Bonus: case-sensitive match
    if query_lower in text_original:
        # Already lowercase match; check exact case
        pass
    if text_original.find(query_lower) != -1:
        score += 5  # Exact case match (query was already lowered, so this is just substring)

    # Bonus: query covers large portion of the line (tighter match)
    ratio = len(query_lower) / max(len(text_lower), 1)
    score += int(ratio * 30)

    return score


class LineIndex:
    """Pre-built line index for fzf-style searching."""

    def __init__(self):
        self._lines = []  # list of tuples: (path, lineno, display_text, line_type, level, text_lower)

    def build(self, node_map):
        """Build the line index from the node map."""
        lines = []
        for node in node_map.values():
            path = node.id
            raw = node.raw
            if not raw:
                continue

            in_fence = False
            for idx, raw_line in enumerate(raw.splitlines()):
                # Skip empty/whitespace lines
                if not raw_line.strip():
                    continue

                line_type, level, display, in_fence = _classify_line(raw_line, in_fence)

                # Skip fence markers themselves
                if line_type is None:
                    continue

                lines.append((
                    path,
                    idx + 1,        # 1-indexed line number
                    display,
                    line_type,
                    level,
                    display.lower(),  # Pre-computed for fast search
                ))

        self._lines = lines

    def search(self, query, limit=30):
        """
        Search the line index.
        Returns list of {path, lineno, line, line_type, level?} dicts.
        """
        query = query.strip()
        if not query:
            return []

        query_lower = query.lower()
        query_words = query_lower.split()

        results = []

        for path, lineno, display, line_type, level, text_lower in self._lines:
            # Multi-word: all words must appear as substrings
            if len(query_words) > 1:
                if not all(w in text_lower for w in query_words):
                    continue
                # Score based on total coverage
                score = 100
                for w in query_words:
                    idx = text_lower.find(w)
                    if idx == 0 or (idx > 0 and text_lower[idx - 1] in ' \t_-./'):
                        score += 10
                # Tighter lines score higher
                ratio = len(query_lower) / max(len(text_lower), 1)
                score += int(ratio * 30)
            else:
                # Single token: substring then subsequence
                score = _substring_score(query_lower, text_lower, display)
                if score == -1:
                    score = _subsequence_score(query_lower, text_lower)
                if score == -1:
                    continue

            # Heading boost: headings get a ranking bonus
            if line_type == 'heading':
                score += 15

            results.append((score, path, lineno, display, line_type, level))

        # Sort: score desc, path asc, lineno asc
        results.sort(key=lambda x: (-x[0], x[1], x[2]))

        output = []
        for score, path, lineno, display, line_type, level in results[:limit]:
            item = {
                'path': path,
                'lineno': lineno,
                'line': display,
                'line_type': line_type,
            }
            if line_type == 'heading':
                item['level'] = level
            output.append(item)

        return output
