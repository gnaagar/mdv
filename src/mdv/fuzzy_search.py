import os
from rapidfuzz import fuzz

class FuzzySearch:
    def __init__(self, node_map):
        self._node_map = node_map

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

    def context_search(self, search_query, block_size=5, limit=20):
        """
        Return non-overlapping blocks of block_size lines containing the search words.
        Uses rapidfuzz.partial_token_set_ratio for fast, intelligent subset matching.
        """
        search_query = search_query.strip()
        if not search_query:
            return []
            
        results = []
        for node in self._node_map.values():
            path = node.id
            content = node.raw

            lines = (content or "").splitlines()
            n = len(lines)
            i = 0
            while i <= n - block_size:
                block = lines[i:i+block_size]
                block_text = '\n'.join(block)
                
                score = fuzz.partial_token_set_ratio(search_query.lower(), block_text.lower())
                if score > 80:
                    results.append({
                        'path': path,
                        'preview': block_text,
                        'lineno': i + 1,
                        'score': score
                    })
                    i += block_size
                else:
                    i += 1
                    
        # Sort by: Score (Desc) -> Path (Asc) -> Line (Asc)
        results.sort(key=lambda x: (-x['score'], x['path'], x.get('lineno', 0)))
        for r in results:
            del r['score']
            
        return results[:limit]
