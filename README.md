# social-tui

Interactive TUI application for viewing and managing LinkedIn posts from JSON data sources.

## Features

- **Interactive Table View**: Browse LinkedIn posts in a clean table interface
- **Navigate**: Use arrow keys to move through posts
- **View Details**: Press `Enter` to see full post content
- **Mark Posts**: Press `m` to mark posts for follow-up
- **View TODOs**: Press `t` to see all marked posts in a popup
- **Export TODOs**: Press `q` to quit and print TODO list to terminal

## Installation

```bash
# Install dependencies using uv
uv pip install -r pyproject.toml
```

Or install manually:
```bash
pip install rich textual
```

## Usage

### 1. Prepare Input CSV

Create an `input-data.csv` file with LinkedIn profiles to track:

```csv
name,username
Corey Quinn,coquinn
Jeff Barr,jeffbarr
Darko Mesaros,darko-mesaros
```

**CSV Structure:**
- **Header row required**: `name,username`
- **name**: Full name of the LinkedIn user
- **username**: LinkedIn username (from their profile URL: `linkedin.com/in/{username}`)

### 2. Run Apify Scraper

```bash
./run_apify.sh
```

This will scrape LinkedIn posts and save JSON output to `data/{date}/linkedin/`.

### 3. View Posts Interactively

```bash
./interactive_posts.py
```

Or:
```bash
python interactive_posts.py
```

## Key Bindings

| Key | Action |
|-----|--------|
| `↑`/`↓` | Navigate through posts |
| `Enter` | View full post details |
| `Escape` | Return to list view |
| `m` | Mark/unmark post for response |
| `t` | View TODO list (popup) |
| `s` | Save marked posts to JSON |
| `q` | Quit and print TODO list |
| `Ctrl+C` | Quit without printing TODOs |

## Project Structure

```
social-tui/
├── data/              # Input data and scraped posts
│   ├── input-data.csv
│   └── YYYYMMDD/
│       └── linkedin/
│           └── *.json
├── output/            # Generated files (marked posts, reports)
├── tests/             # Test files
├── scripts/           # Utility scripts
├── docs/              # Documentation
├── cache/             # Cached images
├── interactive_posts.py  # Main TUI application
├── show_posts.py         # Simple table viewer
├── main.py               # Entry point
└── run_apify.sh          # LinkedIn scraper script
```

## Files

### Core Application
- `main.py` - Entry point for the application
- `interactive_posts.py` - Main interactive TUI application
- `show_posts.py` - Simple table viewer (non-interactive)

### Scripts
- `run_apify.sh` - Scraper script for fetching LinkedIn posts
- `scripts/` - Utility scripts for data extraction and processing

### Data
- `data/input-data.csv` - List of LinkedIn profiles to track
- `data/YYYYMMDD/linkedin/*.json` - Scraped LinkedIn posts
- `output/` - Generated files (marked posts saved here automatically)

### Documentation
- `docs/` - Additional documentation files

## Data Structure

The application expects JSON files in this structure:
```
data/
 YYYYMMDD/
     linkedin/
         *.json
```

Each JSON file contains an array of post objects with fields like:
- `posted_at.date`
- `author.username`
- `author.name`
- `text`
- `url`
- `media` (optional)

### Marked Posts Output

When you mark posts and press `s` to save, they are automatically saved to:
```
output/marked_posts_YYYYMMDD_HHMMSS.json
```

The output includes:
- Search metadata (date, filter query)
- Full post data for all marked posts
