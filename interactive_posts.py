#!/usr/bin/env python3
"""
Interactive LinkedIn posts viewer with marking and TODO list functionality.
"""

import json
import glob
from pathlib import Path
from datetime import datetime, timedelta
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, Static
from textual.containers import Container, VerticalScroll
from textual.binding import Binding
from textual.screen import Screen


class RawJsonScreen(Screen):
    """Screen to show raw JSON data."""

    BINDINGS = [
        Binding("escape", "dismiss", "Back", priority=True),
    ]

    def __init__(self, post_data: dict):
        super().__init__()
        self.post_data = post_data

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(
            Static(self._format_json(), id="raw-json")
        )
        yield Footer()

    def _format_json(self) -> str:
        """Format post data as pretty JSON."""
        def json_serializer(obj):
            """Handle datetime serialization."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        return json.dumps(self.post_data, indent=2, default=json_serializer)

    def action_dismiss(self):
        """Return to previous screen."""
        self.app.pop_screen()


class PostDetailScreen(Screen):
    """Screen to show full post details."""

    BINDINGS = [
        Binding("escape", "dismiss", "Back", priority=True),
        Binding("r", "show_raw", "Raw JSON"),
    ]

    def __init__(self, post_data: dict):
        super().__init__()
        self.post_data = post_data

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(
            Static(self._format_post(), id="post-detail")
        )
        yield Footer()

    def _format_post(self) -> str:
        """Format post data for display."""
        author = self.post_data.get("author", {})
        posted_at = self.post_data.get("posted_at", {})

        lines = [
            f"[bold cyan]Date:[/bold cyan] {posted_at.get('date', 'N/A')}",
            f"[bold cyan]Author:[/bold cyan] {author.get('username', 'N/A')}",
            f"[bold cyan]Name:[/bold cyan] {author.get('name', 'N/A')}",
            f"[bold cyan]URL:[/bold cyan] {self.post_data.get('url', 'N/A')}",
            "",
            "[bold cyan]Text:[/bold cyan]",
            self.post_data.get("text", "No text available."),
        ]

        return "\n".join(lines)

    def action_dismiss(self):
        """Return to main screen."""
        self.app.pop_screen()

    def action_show_raw(self):
        """Show raw JSON data."""
        self.app.push_screen(RawJsonScreen(self.post_data))


class TodoScreen(Screen):
    """Screen to show TODO list of marked posts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Back", priority=True),
    ]

    def __init__(self, marked_posts_data: list):
        super().__init__()
        self.marked_posts_data = marked_posts_data

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(
            Static(self._format_todos(), id="todo-list")
        )
        yield Footer()

    def _format_todos(self) -> str:
        """Format TODO list for display."""
        if not self.marked_posts_data:
            return "[yellow]No posts marked for response.[/yellow]"

        lines = [
            "[bold cyan]TODO: LinkedIn Posts to Respond To[/bold cyan]",
            "=" * 80,
            ""
        ]

        for idx, post in enumerate(self.marked_posts_data, 1):
            author = post.get("author", {})
            posted_at = post.get("posted_at", {})
            text = post.get("text", "")
            url = post.get("url", "N/A")

            # Truncate text for preview
            text_preview = text[:100] + "..." if len(text) > 100 else text

            lines.extend([
                f"[bold yellow]({idx})[/bold yellow] Respond to post by [bold]{author.get('username', 'N/A')}[/bold]",
                f"    [cyan]Date:[/cyan] {posted_at.get('date', 'N/A')}",
                f"    [cyan]URL:[/cyan] {url}",
                f"    [cyan]Profile:[/cyan] {author.get('name', 'N/A')} (@{author.get('username', 'N/A')})",
                f"    [cyan]Preview:[/cyan] {text_preview}",
                ""
            ])

        return "\n".join(lines)

    def action_dismiss(self):
        """Return to main screen."""
        self.app.pop_screen()


class LinkedInPostsApp(App):
    """Interactive LinkedIn posts viewer application."""

    CSS = """
    DataTable {
        height: 100%;
    }

    #post-detail {
        padding: 1 2;
    }

    .marked {
        background: darkgreen;
    }
    """

    BINDINGS = [
        Binding("q", "quit_with_todos", "Quit & Show TODOs", priority=True),
        Binding("t", "view_todos", "View TODOs", priority=True),
        Binding("m", "mark_post", "Mark Post"),
        Binding("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, data_dir: str):
        super().__init__()
        self.data_dir = data_dir
        self.posts = []
        self.marked_posts = set()
        self.post_index_map = {}  # Maps row key to post index

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield DataTable(cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        """Set up the table when the app starts."""
        table = self.query_one(DataTable)
        table.add_column("Date", key="date")
        table.add_column("Username", key="username")
        table.add_column("Text Preview", key="text")
        table.add_column("Media", key="media")
        table.add_column("Marked", key="marked")

        self.load_and_display_posts()

    def load_posts(self) -> list:
        """Load all posts from JSON files in the specified directory."""
        posts = []
        json_files = glob.glob(f"{self.data_dir}/*.json")

        for file_path in json_files:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    posts.extend(data)

        return posts

    def parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except:
            return datetime.min

    def load_and_display_posts(self):
        """Load posts and populate the table."""
        self.posts = self.load_posts()

        # Calculate date threshold (30 days ago)
        thirty_days_ago = datetime.now() - timedelta(days=30)

        # Filter and sort posts
        filtered_posts = []
        for post in self.posts:
            date_str = post.get("posted_at", {}).get("date", "")
            datetime_obj = self.parse_date(date_str)

            if datetime_obj >= thirty_days_ago:
                post["datetime_obj"] = datetime_obj
                filtered_posts.append(post)

        # Sort by date, newest first
        filtered_posts.sort(key=lambda x: x.get("datetime_obj", datetime.min), reverse=True)
        self.posts = filtered_posts

        # Populate table
        table = self.query_one(DataTable)
        for idx, post in enumerate(self.posts):
            date_str = post.get("posted_at", {}).get("date", "")
            username = post.get("author", {}).get("username", "")
            text = post.get("text", "")
            text_preview = text[:50] if text else ""

            # Check if post has media
            media = post.get("media", {})
            has_media = "📷" if media and media.get("type") in ["image", "video"] else ""

            row_key = table.add_row(date_str, username, text_preview, has_media, "")
            self.post_index_map[row_key] = idx

    def on_data_table_row_selected(self, event):
        """Handle row selection (Enter key)."""
        row_key = event.row_key

        if row_key is not None and row_key in self.post_index_map:
            post_idx = self.post_index_map[row_key]
            post = self.posts[post_idx]
            self.push_screen(PostDetailScreen(post))

    def action_mark_post(self):
        """Mark/unmark the current post."""
        table = self.query_one(DataTable)
        cursor_row = table.cursor_row

        # Get all row keys and use the cursor index to find the correct one
        if cursor_row is not None:
            row_keys = list(table.rows.keys())
            if cursor_row < len(row_keys):
                row_key = row_keys[cursor_row]

                if row_key in self.post_index_map:
                    post_idx = self.post_index_map[row_key]

                    if post_idx in self.marked_posts:
                        self.marked_posts.remove(post_idx)
                        table.update_cell(row_key, "marked", "")
                    else:
                        self.marked_posts.add(post_idx)
                        table.update_cell(row_key, "marked", "✅")

    def action_view_todos(self):
        """Show TODO list in a popup screen."""
        marked_posts_data = [self.posts[idx] for idx in sorted(self.marked_posts)]
        self.push_screen(TodoScreen(marked_posts_data))

    def action_quit_with_todos(self):
        """Print TODO list and quit."""
        self.exit()

        if not self.marked_posts:
            print("\nNo posts marked for response.\n")
            return

        print("\n" + "="*80)
        print("TODO: LinkedIn Posts to Respond To")
        print("="*80 + "\n")

        for idx, post_idx in enumerate(sorted(self.marked_posts), 1):
            post = self.posts[post_idx]
            author = post.get("author", {})
            posted_at = post.get("posted_at", {})
            text = post.get("text", "")
            url = post.get("url", "N/A")

            # Truncate text for preview
            text_preview = text[:100] + "..." if len(text) > 100 else text

            print(f"({idx}) Respond to post by {author.get('username', 'N/A')}")
            print(f"    Date: {posted_at.get('date', 'N/A')}")
            print(f"    URL: {url}")
            print(f"    Profile: {author.get('name', 'N/A')} (@{author.get('username', 'N/A')})")
            print(f"    Preview: {text_preview}")
            print()


def main():
    """Run the application."""
    data_dir = "data/20251125/linkedin"
    app = LinkedInPostsApp(data_dir)
    app.run()


if __name__ == "__main__":
    main()
