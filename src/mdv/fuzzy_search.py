import re
from rapidfuzz import fuzz

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)')

class FuzzySearch:
    def __init__(self, node_map):
        self._node_map = node_map

    def heading_search(self, query, limit=20):
        """
        Search only markdown heading lines (# ... through ###### ...).
        Fast because it filters to ~5% of lines before scoring.
        """
        query = query.strip()
        if not query:
            return []

        query_lower = query.lower()
        results = []

        for node in self._node_map.values():
            path = node.id
            lines = (node.raw or "").splitlines()

            for idx, line in enumerate(lines):
                m = _HEADING_RE.match(line)
                if not m:
                    continue

                level = len(m.group(1))
                heading_text = m.group(2).strip()
                heading_lower = heading_text.lower()

                # Fast substring check first
                if query_lower not in heading_lower:
                    score = fuzz.partial_ratio(query_lower, heading_lower)
                    if score <= 60:
                        continue
                else:
                    score = 100

                results.append({
                    'path': path,
                    'heading': heading_text,
                    'lineno': idx + 1,
                    'level': level,
                    'score': score
                })

        results.sort(key=lambda x: (-x['score'], x['path'], x.get('lineno', 0)))
        for r in results:
            del r['score']

        return results[:limit]

    def search(self, query, limit=10):
        query = query.strip()
        if not query:
            return []
            
        results = []
        for path, node in self._node_map.items():
            content = node.raw
            lines = (content or "").splitlines()

            for idx, line in enumerate(lines):
                score = fuzz.partial_token_set_ratio(query.lower(), line.lower())
                if score > 85:
                    start = max(idx - 2, 0)
                    end = min(idx + 3, len(lines))
                    snippet = '\n'.join(lines[start:end])
                    results.append({
                        'path': path,
                        'preview': snippet,
                        'lineno': idx + 1,
                        'score': score
                    })

        # Sort by: Score (Descending) -> File Path (A-Z) -> Line Number (Ascending)
        results.sort(key=lambda x: (-x['score'], x['path'], x.get('lineno', 0)))
        for r in results:
            del r['score']
            
        return results[:limit]

    def context_search(self, search_query, block_size=3, limit=20):
        """
        Return non-overlapping blocks of block_size lines containing the search words.
        Two-phase: fast substring pre-filter, then fuzzy scoring on survivors.
        """
        search_query = search_query.strip()
        if not search_query:
            return []

        query_lower = search_query.lower()
        query_words = query_lower.split()

        results = []
        high_score_count = 0

        for node in self._node_map.values():
            path = node.id
            content = node.raw

            lines = (content or "").splitlines()
            n = len(lines)
            in_code_fence = False
            i = 0
            while i <= n - block_size:
                line = lines[i]
                stripped = line.lstrip()

                # Track code fences — skip content inside them
                if stripped.startswith('```'):
                    in_code_fence = not in_code_fence
                    i += 1
                    continue
                if in_code_fence:
                    i += 1
                    continue

                block = lines[i:i+block_size]
                block_text = '\n'.join(block)
                block_lower = block_text.lower()

                # Phase 1: fast substring pre-filter
                if not any(w in block_lower for w in query_words):
                    i += 1
                    continue

                # Phase 2: fuzzy scoring
                score = fuzz.partial_token_set_ratio(query_lower, block_lower)
                if score > 70:
                    results.append({
                        'path': path,
                        'preview': block_text,
                        'lineno': i + 1,
                        'score': score
                    })
                    if score >= 95:
                        high_score_count += 1
                    i += block_size
                else:
                    i += 1

            # Early termination when we have enough high-confidence results
            if high_score_count >= limit:
                break
                    
        # Sort by: Score (Desc) -> Path (Asc) -> Line (Asc)
        results.sort(key=lambda x: (-x['score'], x['path'], x.get('lineno', 0)))
        for r in results:
            del r['score']
            
        return results[:limit]
