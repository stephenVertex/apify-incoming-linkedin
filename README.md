# social-tui

Interactive TUI application for viewing and managing LinkedIn posts from JSON data sources.

## Features

- **Interactive Table View**: Browse LinkedIn posts in a clean table interface
- **Navigate**: Use arrow keys to move through posts
- **View Details**: Press `Enter` to see full post content
- **Multi-Action Marking**: Press `m` to quickly mark posts with 'save' action, or `M` to select multiple actions:
  - Queue for repost
  - Autoreact (like, celebrate, love)
  - Autocomment
  - Manual comment
  - Autorepost with thoughts
  - Manual repost with thoughts
  - Save for later
- **Mark from Detail View**: Mark posts with actions while viewing full post details
- **View TODOs**: Press `t` to see all marked posts in a popup
- **Export TODOs**: Press `q` to quit and print TODO list with action metadata to terminal
- **Save Marked Posts**: Press `s` to export marked posts with action metadata to JSON

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

### Main Table View

| Key | Action |
|-----|--------|
| `↑`/`↓` or `j`/`k` | Navigate through posts |
| `Enter` | View full post details |
| `m` | Quick mark/unmark post with 'save' action |
| `M` (Shift+m) | Mark with multiple actions (opens action modal) |
| `t` | View TODO list (popup) |
| `s` | Save marked posts to JSON file |
| `r` | Start filtering posts |
| `n` | Toggle showing only new posts (DB mode only) |
| `o` | Open post URL in browser |
| `q` | Quit and print TODO list |
| `Ctrl+C` | Quit without printing TODOs |

### Post Detail View

| Key | Action |
|-----|--------|
| `Escape` | Return to list view |
| `m` | Quick mark/unmark post with 'save' action |
| `M` (Shift+m) | Mark with multiple actions (opens action modal) |
| `o` | Open post URL in browser |
| `r` | Show raw JSON data |
| `i` | View image(s) in terminal (Kitty terminal only) |

### Action Selection Modal

| Key | Action |
|-----|--------|
| `q` | Toggle "Queue for repost" |
| `a` | Toggle "Autoreact" |
| `c` | Toggle "Autocomment" |
| `n` | Toggle "Manual comment" |
| `t` | Toggle "Autorepost with thoughts" |
| `r` | Toggle "Manual repost with thoughts" |
| `s` | Toggle "Save" |
| `Escape` | Close modal and save selections |

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
- Action metadata for each post with:
  - Selected actions (e.g., `["q", "a"]` for queue and autoreact)
  - Timestamp when the post was marked

#### Action Codes

Marked posts display action codes in the "Marked" column:
- `q` - Queue for repost
- `a` - Autoreact
- `c` - Autocomment
- `n` - Manual comment
- `t` - Autorepost with thoughts
- `r` - Manual repost with thoughts
- `s` - Save

Multiple actions are shown together (e.g., `aq` means autoreact and queue for repost).
