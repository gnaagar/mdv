import re
import os

class FuzzySearch:
    def __init__(self, node_map):
        self._node_map = node_map

    def search(self, query, limit=10):
        query = query.strip()
        if not query or ' ' in query:
            return []
        results = []
        word = re.escape(query)
        pattern = re.compile(rf'\b{word}\b', re.IGNORECASE)
        for path, content in self.file_contents.items():

            # TODO: Find the bug due to which content is sometimes none
            # Ideally it should never be none
            lines = (content or "").splitlines()

            for idx, line in enumerate(lines):
                if pattern.search(line):
                    start = max(idx - 2, 0)
                    end = min(idx + 3, len(lines))
                    snippet = '\n'.join(lines[start:end])
                    results.append({
                        'path': path,
                        'preview': snippet,
                        'lineno': idx + 1
                    })
                    if len(results) >= limit:
                        return results
        return results

    def context_search(self, search_query, block_size=5, limit=20):
        """
        Return non-overlapping blocks of block_size lines containing ALL words (case-insensitive),
        with highlights applied to the preview.
        """
        words = [w for w in search_query.strip().split() if w]
        results = []
        word_patterns = [re.compile(re.escape(w), re.IGNORECASE) for w in words]
        for node in self._node_map.values():
            path = node.id
            content = node.raw

            lines = (content or "").splitlines()
            n = len(lines)
            i = 0
            while i <= n - block_size:
                block = lines[i:i+block_size]
                if all(any(p.search(line) for line in block) for p in word_patterns):
                    block_text = '\n'.join(block)
                    results.append({
                        'path': path,
                        'preview': block_text,
                        'lineno': i + 1
                    })
                    if len(results) >= limit:
                        return results
                    i += block_size
                else:
                    i += 1
        return results
