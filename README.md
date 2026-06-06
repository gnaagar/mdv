# mdv — Markdown Viewer for Local Directories

A clean, elegant, and high-performance Markdown viewer for navigating and reading local document workspaces.

---

## Features

- **Premium Aesthetics**: Harmonious light and dark themes (including standard light, dark, and One Dark modes) with elegant typography and smooth micro-animations.
- **Directory Tree Explorer**: An interactive, modal-based directory explorer with subsequence-matching fuzzy filtering to quickly swap files (press `.` to open).
- **Fuzzy Content Search**: Ultra-fast, line-based content search with fzf-style substring/subsequence matching and inline category filters (press `/` to open).
- **Smart Table of Contents**: Sidebar navigation with automatic scroll-tracking and bidirectional synchronization.
- **Focus Mode**: Hide distracting menus and sidebars to read documents in a clean, uncluttered layout.
- **Rich Content Support**: Full support for rendering complex math equations via KaTeX, and flowchart diagrams via Mermaid.js.

---

## Keyboard Shortcuts

The viewer includes robust offline-capable keyboard hotkeys for keyboard-driven navigation:

| Key | Action |
| --- | --- |
| `.` | Open Directory Tree Explorer |
| `/` | Open Content Search Modal |
| `Escape` | Close any active modal |
| `ArrowUp` / `ArrowDown` | Navigate through files/results in modals |
| `Enter` | Open the selected file or search result |

---

## Installation

Install globally using `pipx` or `uv`:

```sh
# Using pipx
pipx install git+https://github.com/gnaagar/mdv.git

# Or using uv
uv tool install git+https://github.com/gnaagar/mdv.git
```

---

## Usage

Start the server inside your workspace directory:

```sh
# Change to your notes/documentation workspace
cd ~/my-workspace

# Run the viewer
mdv
```

By default, the server boots on `http://localhost:8000/`. You can specify a custom port or host if needed:

```sh
mdv --port 8080 --host 0.0.0.0
```

### Navigating Workspace Files
- The home page (`http://localhost:8000/`) displays a dashboard of your workspace with a list of recent files.
- Individual markdown files can be read at `http://localhost:8000/_/path/to/file.md`.

---

## Development

To run from source during local development, use `uv`:

```sh
# Run locally with test/sample documents
uv run mdv samples --port 8000
```

If you are modifying frontend assets (like CSS and JS) and need to bypass browser caching, the templates support version cache-busting.
