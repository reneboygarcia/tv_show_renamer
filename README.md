

![Banner](images/banner.png)

## Introduction

**TV Show Renamer** is a user-friendly application designed to help you organize and rename your TV show collection effortlessly. With a simple interface and automated features, managing your media library has never been easier.

## Installation

> **For Windows instructions, see:** [README_WINDOWS.md](README_WINDOWS.md)

### Prerequisites

- [Python 3.7+](https://www.python.org/downloads/)
- [Make](https://www.gnu.org/software/make/)
- [Homebrew](https://brew.sh/) (macOS only)
- [Git](https://git-scm.com/downloads)

### Quick Setup

```bash
# Clone the repository
$ git clone https://github.com/reneboygarcia/tv_show_renamer.git
$ cd tv_show_renamer

# (macOS only) Ensure Tcl/Tk is installed
$ brew install tcl-tk

# Install all dependencies and set up everything
$ make install
```

This will:
- Create a Python virtual environment
- Install required Python packages
- Set up tkdnd for drag-and-drop support

**If you encounter issues with tkdnd:**
```bash
make clean
make venv
source venv/bin/activate
pip install -r requirements.txt
```

**Verify Tcl/Tk:**
```bash
make verify-tcltk
```

## Quick Start

```bash
source venv/bin/activate  # Activate the virtual environment
make run                  # Start the application
```

Follow the on-screen instructions to select your TV show directory and apply renaming rules.
## Features

- **Automatic Renaming:** Rename TV show files based on season/episode.
- **Organize Media:** Sort files into folders automatically.
- **Custom Naming:** Choose your own filename conventions.
- **Drag-and-Drop:** (macOS/Linux) Requires tkdnd, installed automatically if possible.
## Troubleshooting

- **tkdnd Installation Fails:**
  - Run: `make clean && make venv && source venv/bin/activate && pip install -r requirements.txt`
  - Ensure you have Tcl/Tk: `brew install tcl-tk`

- **Other Issues:**
  - Make sure your Python version is 3.7 or higher.
  - If you see errors about missing dependencies, re-run `make install` after activating your virtual environment.

## Supported Platforms and Formats

- **OS:** Windows, macOS, Linux
- **Video:** `.mp4`, `.mkv`, `.avi`, and more
- **Metadata:** Uses TMDB; accuracy depends on TMDB data
## Getting Help

- **Open an Issue:** [GitHub Issues](https://github.com/reneboygarcia/tv_show_renamer/issues)

## Acknowledgments

- **The Movie Database (TMDB):** For comprehensive media metadata ([TMDB Logos Attribution](https://www.themoviedb.org/about/logos-attribution))
