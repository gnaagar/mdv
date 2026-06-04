# mdv - Mardown Viewer for local directories

## Features

- Clean styles, convenient to customize
- Directory tree sidebar for quick switching
- Table of contents automatically generates, heading tracking/highlighting
- Searching: both files names and content


## Installation

Install globally using `pipx` or `uv`:

```sh
# using pipx
pipx install git+https://github.com/gnaagar/mdv.git

# or using uv
uv tool install git+https://github.com/gnaagar/mdv.git
```

## Usage

Run without installing:

```sh
# using pipx
pipx run git+https://github.com/gnaagar/mdv.git

# or using uv
uvx git+https://github.com/gnaagar/mdv.git
```

Or, if installed:

```sh
cd ~/workspace/scratch
mdv
```

Suppose directory listing of `~/workspace/scratch` is

```
/home/terxor/workspace/scratch
└── notes
    └── topics
        └── abc.md
```

You can then view the file `abc.md` in two ways:

- `http://localhost:5000/v/notes/topics/abc.md`: Default viewer (supports toggling Focus Mode inside the UI)
- `http://localhost:5000/t/notes/topics/abc.md`: Plaintext form

## Development

### Running from source

```sh
uvx .
```

When iterating, `uvx .` may serve a cached build. To force a fresh run without nuking the whole uv cache:

```sh
uvx -n .        # bypasses cache entirely, rebuilds from source
# or: uvx --no-cache .
```

### Sass styles

Sass standalone binary:

```
cd /tmp
# Note: Use your os version
SASS_URL=https://github.com/sass/dart-sass/releases/download/1.97.0/dart-sass-1.97.0-macos-arm64.tar.gz
curl -fsSL -o sass.tar.gz $SASS_URL
tar -xzf sass.tar.gz
```

Now, regen css while development:

```
/tmp/dart-sass/sass --watch src/styles:static/
```

--------------------------------------------------------------------------------
