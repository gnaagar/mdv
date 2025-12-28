# mdv - Mardown Viewer for local directories

## Features

- Clean styles, convenient to customize
- Directory tree sidebar for quick switching
- Table of contents automatically generates, heading tracking/highlighting
- Searching: both files names and content


## Installation

Install globally:

```sh
uv tool install git+https://github.com/gnaagar/mdv.git
```

## Usage

Run without installing:

```sh
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

You can then view the file `abc.md` in three ways:

- `http://localhost:5000/v/notes/topics/abc.md`: Default viewer
- `http://localhost:5000/m/notes/topics/abc.md`: Minimal viewer
- `http://localhost:5000/t/notes/topics/abc.md`: Plaintext form

## Development

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
