from mdv.fuzzy_search import LineIndex
from mdv.mdparser import MarkdownParser
from mdv.logger import get_logger
import os
from dataclasses import dataclass
import threading, time

logger = get_logger(__name__)

PATH_DELIMITER = '/'
MD_EXTENSION = '.md'
REFRESH_DEBOUNCE_SECS = 2


@dataclass
class FileNode:
    # Unique identifier for the file node
    # It is the relative path from the root directory.
    id: str

    # Raw and parsed content of the file.
    raw: str = None
    parsed: str = None
    last_updated: int = None

class MdViewerState:
    def __init__(self, cfg):
        self._cfg = cfg
        self._root_dir = cfg['dir']
        self._precache = cfg.get('precache', None)
        self._node_map = {}

        # Build ignore set: all dot-directories by default, plus user-specified dirs
        self._extra_ignore_dirs = set(cfg.get('ignore_dirs', []))

        self._last_refresh_time = 0
        self._search_index_dirty = True

        self.refresh(force=True)
        self._line_index = LineIndex()
        if self._precache:
            self._build_full_cache()
        else:
            threading.Thread(target=self._build_full_cache, daemon=True).start()

    def _should_ignore_dir(self, dirname):
        """Ignore all dot-directories and any user-specified dirs."""
        if dirname.startswith('.'):
            return True
        return dirname in self._extra_ignore_dirs

    # Refresh the last updated time of the node and invalidate
    # content if required
    def _sync_node(self, node):
        full_path = os.path.join(self._root_dir, os.path.normpath(node.id))
        try:
            last_updated = os.stat(full_path).st_mtime
        except OSError:
            return False
        if node.last_updated is None or node.last_updated < last_updated:
            if node.last_updated is not None:
                logger.debug(f"Clearing stale content of node {node.id}")
            node.raw = None  # Invalidate raw content
            node.parsed = None
            node.last_updated = last_updated
            return True  # Changed
        return False  # Unchanged

    def refresh(self, force=False):
        now = time.monotonic()
        if not force and (now - self._last_refresh_time) < REFRESH_DEBOUNCE_SECS:
            return
        self._last_refresh_time = now

        changed = False
        to_delete = set(self._node_map.keys())

        lite_file = self._cfg.get('lite_file')
        if lite_file:
            # Lite mode: only track the specific file
            id = lite_file
            if id not in self._node_map:
                logger.debug(f"Adding node: {id} to cache (Lite Mode)")
                node = FileNode(id=id)
                self._node_map[node.id] = node
                changed = True

            if self._sync_node(self._node_map[id]):
                changed = True

            if id in to_delete:
                to_delete.remove(id)
        else:
            # Normal mode: walk directory
            for root, dirs, files in os.walk(self._root_dir):
                # Modify 'dirs' in-place to skip ignored directories
                dirs[:] = [d for d in dirs if not self._should_ignore_dir(d)]
                for file in files:
                    if file.endswith(MD_EXTENSION):
                        full_path = os.path.join(root, file)
                        id = os.path.relpath(full_path, self._root_dir).replace(os.path.sep, '/')

                        if id not in self._node_map:
                            logger.debug(f"Adding node: {id} to cache")
                            node = FileNode(id=id)
                            self._node_map[node.id] = node
                            changed = True

                        if self._sync_node(self._node_map[id]):
                            changed = True

                        if id in to_delete:
                            to_delete.remove(id)

        # Remove nodes that are no longer in the file system
        if to_delete:
            changed = True
        for id in to_delete:
            logger.debug(f"Removing node: {id} from cache")
            self._node_map.pop(id, None)

        if changed:
            self._search_index_dirty = True


    def _build_full_cache(self):
        try:
            # Snapshot to avoid RuntimeError if refresh() modifies dict concurrently
            nodes = list(self._node_map.values())
            for node in nodes:
                time.sleep(0.05) # Sleep for 50ms to allow other processing
                self._refresh_node(node)

            # Build search index after all content is loaded
            self._line_index.build(self._node_map)
            self._search_index_dirty = False

            # For stats
            size = 0
            for node in list(self._node_map.values()):
                size += len(node.raw or '')
                size += len(node.parsed or '')
            logger.debug(f'Built full cache of {size} bytes worth of content')
        except Exception as e:
            logger.error(f'Error building full cache: {e}')

    def _refresh_node(self, node):
        self._sync_node(node)
        if node.raw is not None and node.parsed is not None:
            # Node is already fully loaded, no need to refresh
            return

        full_path = os.path.join(self._root_dir, os.path.normpath(node.id))
        logger.debug(f"Building node: {node.id} ")
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
                node.raw = raw_content
                node.parsed = MarkdownParser.parse(raw_content)
                node.last_updated = os.stat(full_path).st_mtime
        except Exception as e:
            logger.error(f"Error reading file {full_path}: {e}")

    def is_file(self, path):
        return path in self._node_map

    def get_content(self, id, raw=False):
        if id not in self._node_map:
            raise FileNotFoundError(f"File '{id}' not found in cache")
        node = self._node_map[id]
        self._refresh_node(node)
        result = node.raw if raw else node.parsed
        if result is None:
            raise FileNotFoundError(f"File '{id}' could not be loaded")
        length = len(result)
        logger.debug(f'Returning cached content for {id} (length={length})')
        return result

    def search(self, search_query, types=None):
        if self._search_index_dirty:
            self._rebuild_search_index()
        return self._line_index.search(search_query, types=types)

    def _rebuild_search_index(self):
        """Rebuild the search index from current node map."""
        # Snapshot to avoid RuntimeError from concurrent dict modification
        for node in list(self._node_map.values()):
            if node.raw is None:
                self._refresh_node(node)
        self._line_index.build(self._node_map)
        self._search_index_dirty = False
        logger.debug('Rebuilt search index')

    def get_dashboard_data(self):
        """Return data needed for the dashboard landing page."""
        import re

        workspace_name = os.path.basename(self._root_dir) or self._root_dir
        workspace_path = self._root_dir

        # --- Stats ---
        file_count = len(self._node_map)
        heading_count = 0
        word_count = 0

        for node in list(self._node_map.values()):
            if node.raw:
                # Count headings (lines starting with #)
                for line in node.raw.splitlines():
                    stripped = line.strip()
                    if re.match(r'^#{1,6}\s+', stripped):
                        heading_count += 1
                # Word count (simple split)
                word_count += len(node.raw.split())

        # --- Recent files (top 8 by mtime) ---
        nodes_with_time = [
            n for n in list(self._node_map.values()) if n.last_updated is not None
        ]
        nodes_with_time.sort(key=lambda n: n.last_updated, reverse=True)
        recent_files = []
        for n in nodes_with_time[:8]:
            recent_files.append({
                'name': n.id.split('/')[-1],
                'path': n.id,
                'mtime': n.last_updated,
            })

        # --- README preview ---
        readme_html = None
        readme_path = None
        # Check common README filenames
        for candidate in ['README.md', 'readme.md', 'Readme.md']:
            if candidate in self._node_map:
                node = self._node_map[candidate]
                self._refresh_node(node)
                if node.raw:
                    # Take first 15 non-empty lines
                    lines = node.raw.splitlines()
                    preview_lines = []
                    for line in lines:
                        preview_lines.append(line)
                        if len(preview_lines) >= 15:
                            break
                    preview_md = '\n'.join(preview_lines)
                    readme_html = MarkdownParser.parse(preview_md)
                    readme_path = candidate
                break

        return {
            'workspace_name': workspace_name,
            'workspace_path': workspace_path,
            'file_count': file_count,
            'heading_count': heading_count,
            'word_count': word_count,
            'recent_files': recent_files,
            'readme_html': readme_html,
            'readme_path': readme_path,
        }

    def get_tree(self):
        """
        Return the tree structure without file contents for API responses.
        """

        # Key function fo sorting
        def key_func(node):
            name, type = node['name'], node['type']
            if type == 'directory':
                return (1, name)
            return (0, name)

        tree = {}

        for node in list(self._node_map.values()):
            parts = node.id.split(PATH_DELIMITER)
            current_level = tree

            current_path = ""

            for part in parts[:-1]:
                # build directory path (added)
                current_path = part if current_path == "" else current_path + PATH_DELIMITER + part

                dir_node = current_level.get(part, None)
                if not dir_node:
                    dir_node = {
                        'type': 'directory',
                        'name': part,
                        'id': current_path,
                        'children': {}
                    }
                    current_level[part] = dir_node
                current_level = dir_node['children']

            file_node = {
                'type': 'file',
                'name': parts[-1],
                'id': node.id
            }
            current_level[parts[-1]] = file_node

        def dict_to_list(node):
            """Recursively convert children dicts to lists for API output."""
            if node['type'] == 'directory':
                children_list = [dict_to_list(child) for child in node['children'].values()]
                children_list.sort(key=key_func)
                return {
                    'type': 'directory',
                    'name': node['name'],
                    'path': node['id'],
                    'children': children_list
                }
            else:
                return {
                    'type': 'file',
                    'name': node['name'],
                    'path': node['id'] # For some reason, frontend expects 'path' instead of 'id'
                }

        list_tree = []
        for dir_node in tree.values():
            list_tree.append(dict_to_list(dir_node))
        list_tree.sort(key=key_func)
        return list_tree

