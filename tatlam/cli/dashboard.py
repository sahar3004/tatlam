"""
TATLAM Operations Dashboard - Real-time SQLite DB monitoring with Textual TUI.

This dashboard provides visibility into the scenario database without running SQL queries.
Features:
- Live DataTable showing scenarios with auto-refresh (every 2 seconds)
- Log viewer displaying tatlam.log
- Keyboard shortcuts for navigation and control

Usage:
    python -m tatlam.cli.dashboard
    # or use the launcher script: ./scripts/start_dashboard.sh
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Label, Static
from textual.binding import Binding
from textual.timer import Timer

from sqlalchemy import select, func
from tatlam.infra.db import get_session
from tatlam.infra.models import Scenario
from tatlam.settings import get_settings


class LogViewer(Static):
    """Widget for displaying log file content with auto-refresh."""

    def __init__(self, log_path: str | Path, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.log_path = Path(log_path)
        self.max_lines = 100  # Show last 100 lines

    def on_mount(self) -> None:
        """Set up auto-refresh timer when widget is mounted."""
        self.set_interval(2.0, self.refresh_log)
        self.refresh_log()

    def refresh_log(self) -> None:
        """Read and display the last N lines from the log file."""
        try:
            if not self.log_path.exists():
                self.update("[dim]Log file not found:[/dim] {self.log_path}")
                return

            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Get last max_lines
            recent_lines = lines[-self.max_lines:]
            content = "".join(recent_lines)

            # Format with markup
            formatted = f"[dim]Last {len(recent_lines)} lines from {self.log_path.name}:[/dim]\n\n{content}"
            self.update(formatted)

        except Exception as e:
            self.update(f"[red]Error reading log:[/red] {e}")


class ScenarioTable(DataTable):
    """DataTable widget for displaying scenarios from the database."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh", show=True),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True

    def on_mount(self) -> None:
        """Set up table columns and auto-refresh timer when widget is mounted."""
        # Add columns
        self.add_column("ID", width=8)
        self.add_column("Title", width=40)
        self.add_column("Category", width=25)
        self.add_column("Threat", width=15)
        self.add_column("Status", width=12)
        self.add_column("Created", width=20)

        # Set up auto-refresh (every 2 seconds)
        self.set_interval(2.0, self.refresh_data)
        self.refresh_data()

    def action_refresh(self) -> None:
        """Manual refresh action (triggered by 'r' key)."""
        self.refresh_data()
        self.app.notify("Table refreshed")

    def refresh_data(self) -> None:
        """Fetch data from database and update the table."""
        try:
            with get_session() as session:
                # Query scenarios ordered by creation time (newest first)
                stmt = (
                    select(Scenario)
                    .order_by(Scenario.created_at.desc())
                    .limit(100)
                )
                scenarios = session.scalars(stmt).all()

                # Clear existing rows
                self.clear()

                # Add rows
                for scenario in scenarios:
                    # Truncate title if too long
                    title = scenario.title
                    if len(title) > 37:
                        title = title[:37] + "..."

                    # Truncate category
                    category = scenario.category or "N/A"
                    if len(category) > 22:
                        category = category[:22] + "..."

                    # Format created_at
                    try:
                        created_dt = datetime.fromisoformat(scenario.created_at)
                        created_str = created_dt.strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        created_str = scenario.created_at[:16] if scenario.created_at else "N/A"

                    self.add_row(
                        str(scenario.id),
                        title,
                        category,
                        scenario.threat_level or "N/A",
                        scenario.status or "pending",
                        created_str,
                    )

        except Exception as e:
            self.app.notify(f"Error loading data: {e}", severity="error")
            logging.error(f"Dashboard table refresh failed: {e}")


class StatsBar(Static):
    """Widget for displaying database statistics."""

    def on_mount(self) -> None:
        """Set up auto-refresh timer when widget is mounted."""
        self.set_interval(2.0, self.refresh_stats)
        self.refresh_stats()

    def refresh_stats(self) -> None:
        """Fetch and display database statistics."""
        try:
            with get_session() as session:
                # Count total scenarios
                total = session.scalar(select(func.count(Scenario.id))) or 0

                # Count by status
                pending = session.scalar(
                    select(func.count(Scenario.id)).where(Scenario.status == "pending")
                ) or 0
                approved = session.scalar(
                    select(func.count(Scenario.id)).where(Scenario.status == "approved")
                ) or 0

                # Count by threat level
                high = session.scalar(
                    select(func.count(Scenario.id)).where(Scenario.threat_level.in_(["גבוהה", "גבוהה מאוד"]))
                ) or 0

                stats_text = (
                    f"[bold]Total:[/bold] {total}  |  "
                    f"[yellow]Pending:[/yellow] {pending}  |  "
                    f"[green]Approved:[/green] {approved}  |  "
                    f"[red]High Threat:[/red] {high}"
                )

                self.update(stats_text)

        except Exception as e:
            self.update(f"[red]Error loading stats:[/red] {e}")


class TatlamDashboard(App):
    """TATLAM Operations Dashboard - Real-time scenario database monitoring."""

    CSS = """
    Screen {
        background: $surface;
    }

    #stats {
        dock: top;
        height: 3;
        background: $boost;
        padding: 1 2;
    }

    #table-container {
        height: 60%;
        border: solid $primary;
    }

    #log-container {
        height: 40%;
        border: solid $accent;
        margin-top: 1;
    }

    LogViewer {
        height: 100%;
        padding: 1 2;
        overflow-y: scroll;
    }

    ScenarioTable {
        height: 100%;
    }

    .label {
        padding: 0 2;
        background: $primary-background;
        color: $text;
        text-style: bold;
    }
    """

    TITLE = "TATLAM Operations Dashboard"
    SUB_TITLE = "Real-time Scenario Database Monitor"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh_all", "Refresh All", show=True),
        Binding("d", "toggle_dark", "Toggle Dark Mode", show=False),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.settings = get_settings()

        # Determine log path
        log_path = self.settings.BASE_DIR / "tatlam.log"
        if not log_path.exists():
            # Try alternative locations
            alt_paths = [
                Path("tatlam.log"),
                Path("logs/tatlam.log"),
            ]
            for alt in alt_paths:
                if alt.exists():
                    log_path = alt
                    break

        self.log_path = log_path

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        # Stats bar
        yield StatsBar(id="stats")

        # Main content area
        with Vertical():
            # Scenario table
            with Container(id="table-container"):
                yield Label("Scenarios (ID | Title | Category | Threat | Status | Created)", classes="label")
                yield ScenarioTable()

            # Log viewer
            with Container(id="log-container"):
                yield Label(f"Logs: {self.log_path}", classes="label")
                yield LogViewer(self.log_path)

        yield Footer()

    def action_refresh_all(self) -> None:
        """Refresh all widgets manually."""
        # Refresh table
        table = self.query_one(ScenarioTable)
        table.refresh_data()

        # Refresh stats
        stats = self.query_one(StatsBar)
        stats.refresh_stats()

        # Refresh log
        log_viewer = self.query_one(LogViewer)
        log_viewer.refresh_log()

        self.notify("All widgets refreshed")

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark


def main() -> None:
    """Entry point for the dashboard."""
    app = TatlamDashboard()
    app.run()


if __name__ == "__main__":
    main()
