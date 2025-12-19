from fuzzy_search import FuzzySearch
from mdparser import MarkdownParser
from logger import get_logger
import os
from dataclasses import dataclass
import threading, time

logger = get_logger(__name__)

PATH_DELIMITER = '/'
IGNORED_DIRS = {'.git'}
MD_EXTENSION = '.md'


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
        self._root_dir = cfg['dir']
        self._precache = cfg.get('precache',None)
        self._node_map = {}
        self.refresh()
        if self._precache:
            self._build_full_cache()
        else:
            threading.Thread(target=self._build_full_cache).start()
        self._fuzzy_search = FuzzySearch(self._node_map)

    # Refresh the last updated time of the node and invalidate
    # content if required
    def _sync_node (self, node):
        full_path = os.path.join(self._root_dir, node.id)
        last_updated = os.stat(full_path).st_mtime
        if node.last_updated is None or node.last_updated < last_updated:
            if node.last_updated is not None:
                logger.debug(f"Clearing stale content of node {id}")
            node.raw = None  # Invalidate raw content
            node.parsed = None
            node.last_updated = last_updated

    # Lightweight sync with file system.
    # It is a metadata refresh, which does not read file contents.
    # It adds/deletes nodes which are not in the cache (but there in the file system)
    # It also invalidates contents of nodes which are outdated.
    def refresh(self):
        # Assume that we will delete everything
        to_delete = set(self._node_map.keys())

        for root, dirs, files in os.walk(self._root_dir):
            # Modify 'dirs' in-place to skip ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for file in files:
                if file.endswith(MD_EXTENSION) and not any(ignored in root for ignored in IGNORED_DIRS):
                    full_path = os.path.join(root, file)
                    id = os.path.relpath(full_path, self._root_dir)

                    if id not in self._node_map:
                        logger.debug(f"Adding node: {id} to cache")
                        # Create new bare node
                        node = FileNode(id=id)
                        self._node_map[node.id] = node

                    self._sync_node(self._node_map[id])

                    if id in to_delete:
                        to_delete.remove(id)

        # Remove nodes that are no longer in the file system
        for id in to_delete:
            logger.debug(f"Removing node: {id} from cache")
            self._node_map.pop(id, None)

    def _build_full_cache(self):
        # Assuming bare map is already built
        for node in self._node_map.values():
            time.sleep(0.05) # Sleep for 50ms to allow other processing
            self._refresh_node(node)

        # For stats
        size = 0
        for node in self._node_map.values():
            size += len(node.raw)
            size += len(node.parsed)
        logger.debug(f'Built full cache of {size} bytes worth of content')

    def _refresh_node(self, node):
        self._sync_node(node)
        if node.raw is not None and node.parsed is not None:
            # Node is already fully loaded, no need to refresh
            return

        full_path = os.path.join(self._root_dir, node.id)
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
        length = len(result)
        logger.debug(f'Returning cached content for {id} (length={length})')
        return result

    def search(self, search_query):
        results = self._fuzzy_search.context_search(search_query)
        return results

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

        for node in self._node_map.values():
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

