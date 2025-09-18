#!/usr/bin/env python

import sys
from typing import List, Optional, Callable
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

from story_selection import StorySelection, SelectableStory
from hn_api import HackerNewsStory


class InteractiveStorySelector:
    """Interactive story selector using Rich for terminal UI."""

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the interactive selector.

        Args:
            console: Rich console instance (creates new one if None)
        """
        self.console = console or Console()
        self.selection: Optional[StorySelection] = None
        self.current_page = 0
        self.page_size = 10
        self.cursor_position = 0
        self.filter_text = ""
        self.show_help = False

    def select_stories(self, stories: List[HackerNewsStory]) -> List[HackerNewsStory]:
        """
        Interactive story selection interface.

        Args:
            stories: List of HackerNewsStory objects to select from

        Returns:
            List of selected HackerNewsStory objects
        """
        # Input validation
        if not isinstance(stories, list):
            raise TypeError("Stories must be a list")

        if not stories:
            self.console.print("[red]No stories to select from![/red]")
            return []

        # Validate story objects
        for i, story in enumerate(stories):
            if not hasattr(story, 'id') or not hasattr(story, 'title'):
                raise ValueError(f"Invalid story object at index {i}: missing required attributes")

        try:
            self.selection = StorySelection.from_hn_stories(stories)
        except Exception as e:
            self.console.print(f"[red]Error creating story selection: {e}[/red]")
            return []

        self.console.print(Panel.fit(
            "[bold blue]Interactive Story Selector[/bold blue]\n"
            f"Use arrow keys/hjkl to navigate, SPACE to toggle, ENTER to confirm\n"
            f"Press 'h' for help, 'q' to quit"
        ))

        try:
            # Use simplified keyboard input for CLI compatibility
            return self._run_selection_loop()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Selection cancelled by user[/yellow]")
            return []
        except Exception as e:
            self.console.print(f"[red]Unexpected error in selection interface: {e}[/red]")
            import traceback
            self.console.print(f"[dim]Debug: {traceback.format_exc()}[/dim]")
            return []

    def _run_selection_loop(self) -> List[HackerNewsStory]:
        """Run the main selection loop with simplified input."""
        while True:
            self._display_interface()

            try:
                # Get user input
                self.console.print("\n[cyan]Commands:[/cyan] (s)elect/(d)eselect, (a)ll, (n)one, (i)nvert")
                self.console.print("[cyan]Advanced:[/cyan] (f)ilter, (p)review, (u)rls, score:N, hours:N, (h)elp")
                self.console.print("[cyan]Actions:[/cyan] (c)onfirm, (q)uit")

                command = Prompt.ask("Enter command", default="h").lower().strip()

                if command in ['q', 'quit']:
                    self.console.print("[yellow]Selection cancelled[/yellow]")
                    return []
                elif command in ['c', 'confirm']:
                    return self._confirm_selection()
                elif command in ['h', 'help']:
                    self._show_help()
                elif command in ['s', 'select']:
                    self._toggle_current_story()
                elif command in ['d', 'deselect']:
                    self._deselect_current_story()
                elif command in ['a', 'all']:
                    self._select_all()
                elif command in ['n', 'none']:
                    self._deselect_all()
                elif command in ['i', 'invert']:
                    self._invert_selection()
                elif command in ['f', 'filter']:
                    self._set_filter()
                elif command in ['p', 'preview']:
                    self._preview_current_story()
                elif command in ['u', 'urls']:
                    self._toggle_url_filter()
                elif command in ['score']:
                    self._select_by_score()
                elif command in ['recent']:
                    self._select_recent_stories()
                elif command.isdigit():
                    self._jump_to_story(int(command))
                elif command in ['next', '>']:
                    self._next_page()
                elif command in ['prev', '<']:
                    self._previous_page()
                elif command.startswith('score:'):
                    try:
                        min_score = int(command.split(':')[1])
                        self._select_by_score(min_score)
                    except (ValueError, IndexError):
                        self.console.print("[red]Invalid score format. Use 'score:number'[/red]")
                elif command.startswith('hours:'):
                    try:
                        max_hours = int(command.split(':')[1])
                        self._select_recent_stories(max_hours)
                    except (ValueError, IndexError):
                        self.console.print("[red]Invalid hours format. Use 'hours:number'[/red]")
                else:
                    self.console.print(f"[red]Unknown command: {command}[/red]")

            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[yellow]Selection cancelled[/yellow]")
                return []

    def _display_interface(self) -> None:
        """Display the main selection interface."""
        if not self.selection:
            return

        # Clear screen and show header
        self.console.clear()
        self._display_header()

        # Show stories table
        self._display_stories_table()

        # Show footer with summary
        self._display_footer()

    def _display_header(self) -> None:
        """Display header with filters and summary."""
        if not self.selection:
            return

        summary = self.selection.get_selection_summary()

        header_text = f"[bold]HackerCast Story Selector[/bold] | "
        header_text += f"Total: {summary['total']} | "
        header_text += f"Selected: [green]{summary['selected']}[/green] | "
        header_text += f"Filtered: {summary['filtered']}"

        if self.filter_text:
            header_text += f" | Filter: [yellow]'{self.filter_text}'[/yellow]"

        self.console.print(Panel(header_text))

    def _display_stories_table(self) -> None:
        """Display stories in a table format."""
        if not self.selection:
            return

        filtered_stories = self.selection.filtered_stories

        if not filtered_stories:
            self.console.print("[yellow]No stories match current filters[/yellow]")
            return

        # Calculate pagination
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(filtered_stories))
        page_stories = filtered_stories[start_idx:end_idx]

        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", justify="right", width=3)
        table.add_column("Sel", justify="center", width=3)
        table.add_column("Title", style="white", min_width=40, max_width=60)
        table.add_column("Score", justify="right", style="green", width=5)
        table.add_column("Age", justify="right", style="yellow", width=4)
        table.add_column("Author", style="blue", width=15)
        table.add_column("URL", style="dim", width=3)

        for i, story in enumerate(page_stories):
            row_idx = start_idx + i
            is_current = row_idx == self.cursor_position

            # Selection indicator
            sel_icon = "✓" if story.selected else "○"
            sel_style = "green" if story.selected else "white"

            # Title with current indicator
            title = story.display_title
            if is_current:
                title = f"[reverse]{title}[/reverse]"

            # Age display
            age_text = f"{story.age_hours}h" if story.age_hours < 24 else f"{story.age_hours//24}d"

            # URL indicator
            url_icon = "🔗" if story.has_url else "❌"

            table.add_row(
                str(row_idx + 1),
                f"[{sel_style}]{sel_icon}[/{sel_style}]",
                title,
                str(story.story.score),
                age_text,
                story.story.by[:14] if len(story.story.by) > 14 else story.story.by,
                url_icon
            )

        self.console.print(table)

        # Show pagination info
        total_pages = (len(filtered_stories) + self.page_size - 1) // self.page_size
        if total_pages > 1:
            page_info = f"Page {self.current_page + 1} of {total_pages}"
            self.console.print(f"[dim]{page_info}[/dim]")

    def _display_footer(self) -> None:
        """Display footer with quick commands."""
        footer_text = (
            "[bold]Quick Commands:[/bold] "
            "(s)elect • (a)ll • (n)one • (i)nvert • (f)ilter • (p)review • (u)rls • "
            "(c)onfirm • (h)elp • (q)uit"
        )
        self.console.print(f"\n[dim]{footer_text}[/dim]")

    def _toggle_current_story(self) -> None:
        """Toggle selection of current story."""
        if not self.selection:
            return

        filtered_stories = self.selection.filtered_stories
        if 0 <= self.cursor_position < len(filtered_stories):
            story = filtered_stories[self.cursor_position]
            story.toggle_selection()
            self.console.print(f"[green]{'Selected' if story.selected else 'Deselected'}: {story.display_title}[/green]")

    def _deselect_current_story(self) -> None:
        """Deselect current story."""
        if not self.selection:
            return

        filtered_stories = self.selection.filtered_stories
        if 0 <= self.cursor_position < len(filtered_stories):
            story = filtered_stories[self.cursor_position]
            if story.selected:
                story.selected = False
                self.console.print(f"[yellow]Deselected: {story.display_title}[/yellow]")

    def _select_all(self) -> None:
        """Select all filtered stories."""
        if not self.selection:
            return

        count = self.selection.select_all(filtered_only=True)
        self.console.print(f"[green]Selected {count} additional stories[/green]")

    def _deselect_all(self) -> None:
        """Deselect all filtered stories."""
        if not self.selection:
            return

        count = self.selection.deselect_all(filtered_only=True)
        self.console.print(f"[yellow]Deselected {count} stories[/yellow]")

    def _invert_selection(self) -> None:
        """Invert selection for all filtered stories."""
        if not self.selection:
            return

        count = self.selection.invert_selection(filtered_only=True)
        self.console.print(f"[blue]Inverted selection for {count} stories[/blue]")

    def _set_filter(self) -> None:
        """Set filter for stories."""
        if not self.selection:
            self.console.print("[red]No selection available[/red]")
            return

        try:
            current_filter = self.selection._filter_query
            new_filter = Prompt.ask(
                "Enter filter text (title/author)",
                default=current_filter
            ).strip()

            # Validate filter length
            if len(new_filter) > 100:
                self.console.print("[red]Filter text too long (max 100 characters)[/red]")
                return

            self.selection.set_filter(new_filter)
            self.filter_text = new_filter
            self.current_page = 0  # Reset to first page
            self.cursor_position = 0

            filtered_count = len(self.selection.filtered_stories)
            if new_filter:
                self.console.print(f"[blue]Filter applied: '{new_filter}' ({filtered_count} matches)[/blue]")
            else:
                self.console.print(f"[blue]Filter cleared ({filtered_count} stories)[/blue]")

        except Exception as e:
            self.console.print(f"[red]Error setting filter: {e}[/red]")

    def _jump_to_story(self, story_number: int) -> None:
        """Jump to specific story number."""
        if not self.selection:
            return

        # Convert 1-based to 0-based index
        target_idx = story_number - 1
        filtered_stories = self.selection.filtered_stories

        if 0 <= target_idx < len(filtered_stories):
            self.cursor_position = target_idx
            # Calculate which page this story is on
            self.current_page = target_idx // self.page_size
            self.console.print(f"[blue]Jumped to story #{story_number}[/blue]")
        else:
            self.console.print(f"[red]Invalid story number: {story_number}[/red]")

    def _next_page(self) -> None:
        """Go to next page."""
        if not self.selection:
            return

        filtered_stories = self.selection.filtered_stories
        total_pages = (len(filtered_stories) + self.page_size - 1) // self.page_size

        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.cursor_position = self.current_page * self.page_size
            self.console.print(f"[blue]Next page ({self.current_page + 1}/{total_pages})[/blue]")
        else:
            self.console.print("[yellow]Already on last page[/yellow]")

    def _previous_page(self) -> None:
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self.cursor_position = self.current_page * self.page_size
            total_pages = (len(self.selection.filtered_stories) + self.page_size - 1) // self.page_size
            self.console.print(f"[blue]Previous page ({self.current_page + 1}/{total_pages})[/blue]")
        else:
            self.console.print("[yellow]Already on first page[/yellow]")

    def _preview_current_story(self) -> None:
        """Show preview of current story with URL and metadata."""
        if not self.selection:
            return

        filtered_stories = self.selection.filtered_stories
        if not (0 <= self.cursor_position < len(filtered_stories)):
            self.console.print("[yellow]No story selected for preview[/yellow]")
            return

        story = filtered_stories[self.cursor_position]

        # Create preview panel
        preview_content = []
        preview_content.append(f"[bold]{story.story.title}[/bold]")
        preview_content.append(f"")
        preview_content.append(f"[cyan]Author:[/cyan] {story.story.by}")
        preview_content.append(f"[green]Score:[/cyan] {story.story.score}")
        preview_content.append(f"[yellow]Age:[/cyan] {story.age_hours} hours")
        preview_content.append(f"[magenta]Comments:[/cyan] {story.story.descendants}")
        preview_content.append(f"[blue]Selected:[/cyan] {'Yes' if story.selected else 'No'}")

        if story.story.url:
            # Truncate long URLs
            url = story.story.url
            if len(url) > 80:
                url = url[:77] + "..."
            preview_content.append(f"[dim]URL:[/cyan] {url}")
        else:
            preview_content.append("[red]No URL available (cannot scrape)[/red]")

        preview_text = "\n".join(preview_content)

        self.console.print(Panel(
            preview_text,
            title=f"Story Preview #{self.cursor_position + 1}",
            border_style="blue"
        ))

        Prompt.ask("Press Enter to continue")

    def _toggle_url_filter(self) -> None:
        """Toggle URL filter on/off."""
        if not self.selection:
            return

        current_state = self.selection._show_only_with_urls
        self.selection.set_url_filter(not current_state)

        # Reset pagination
        self.current_page = 0
        self.cursor_position = 0

        status = "enabled" if not current_state else "disabled"
        filtered_count = len(self.selection.filtered_stories)
        self.console.print(f"[blue]URL filter {status} ({filtered_count} stories shown)[/blue]")

    def _select_by_score(self, min_score: Optional[int] = None) -> None:
        """Select stories by minimum score."""
        if not self.selection:
            return

        if min_score is None:
            min_score_str = Prompt.ask("Enter minimum score", default="50")
            try:
                min_score = int(min_score_str)
            except ValueError:
                self.console.print("[red]Invalid score. Please enter a number.[/red]")
                return

        if min_score < 0:
            self.console.print("[red]Score must be non-negative[/red]")
            return

        count = self.selection.select_by_criteria(min_score=min_score)
        self.console.print(f"[green]Selected {count} additional stories with score ≥ {min_score}[/green]")

    def _select_recent_stories(self, max_hours: Optional[int] = None) -> None:
        """Select stories newer than specified hours."""
        if not self.selection:
            return

        if max_hours is None:
            max_hours_str = Prompt.ask("Enter maximum age in hours", default="24")
            try:
                max_hours = int(max_hours_str)
            except ValueError:
                self.console.print("[red]Invalid hours. Please enter a number.[/red]")
                return

        if max_hours < 0:
            self.console.print("[red]Hours must be non-negative[/red]")
            return

        count = self.selection.select_by_criteria(max_age_hours=max_hours)
        self.console.print(f"[green]Selected {count} additional stories newer than {max_hours} hours[/green]")

    def _show_help(self) -> None:
        """Show help information."""
        help_text = """
[bold blue]Interactive Story Selector Help[/bold blue]

[bold]Navigation:[/bold]
• [cyan]<number>[/cyan] - Jump to story number
• [cyan]next, >[/cyan] - Next page
• [cyan]prev, <[/cyan] - Previous page

[bold]Selection:[/bold]
• [cyan]s, select[/cyan] - Toggle current story selection
• [cyan]d, deselect[/cyan] - Deselect current story
• [cyan]a, all[/cyan] - Select all filtered stories
• [cyan]n, none[/cyan] - Deselect all filtered stories
• [cyan]i, invert[/cyan] - Invert selection for filtered stories

[bold]Smart Selection:[/bold]
• [cyan]score[/cyan] - Select by minimum score (interactive)
• [cyan]score:N[/cyan] - Select stories with score ≥ N
• [cyan]recent[/cyan] - Select recent stories (interactive)
• [cyan]hours:N[/cyan] - Select stories newer than N hours

[bold]Filtering & Preview:[/bold]
• [cyan]f, filter[/cyan] - Set text filter (searches title and author)
• [cyan]u, urls[/cyan] - Toggle showing only stories with URLs
• [cyan]p, preview[/cyan] - Preview current story details

[bold]Actions:[/bold]
• [cyan]c, confirm[/cyan] - Confirm selection and proceed
• [cyan]h, help[/cyan] - Show this help
• [cyan]q, quit[/cyan] - Cancel and quit

[bold]Examples:[/bold]
• [dim]score:100[/dim] - Select all stories with 100+ points
• [dim]hours:6[/dim] - Select stories from last 6 hours
• [dim]u[/dim] - Toggle filter to show only scrapable stories

[bold]Legend:[/bold]
• ✓ = Selected story    • ○ = Unselected story
• 🔗 = Has URL         • ❌ = No URL (cannot scrape)

Stories are [green]selected by default[/green]. Deselect stories you don't want to process.
Only stories with URLs can be scraped for content.
"""
        self.console.print(Panel(help_text, title="Help", border_style="blue"))
        Prompt.ask("Press Enter to continue")

    def _confirm_selection(self) -> List[HackerNewsStory]:
        """Confirm current selection and return selected stories."""
        if not self.selection:
            return []

        selected_stories = self.selection.selected_stories

        if not selected_stories:
            self.console.print("[red]No stories selected![/red]")
            retry = Prompt.ask("Go back to selection? (y/n)", default="y").lower()
            if retry in ['y', 'yes']:
                return []  # Continue loop
            else:
                return []  # Return empty list

        # Show validation warnings
        validation = self.selection.validate_selection()
        if validation['warnings']:
            self.console.print("[yellow]Warnings:[/yellow]")
            for warning in validation['warnings']:
                self.console.print(f"  • {warning}")

        # Show selection summary
        summary = self.selection.get_selection_summary()
        self.console.print(f"\n[green]Selected {summary['selected']} out of {summary['total']} stories[/green]")

        if summary['selected_with_urls'] < summary['selected']:
            skipped = summary['selected'] - summary['selected_with_urls']
            self.console.print(f"[yellow]Note: {skipped} selected stories have no URL and will be skipped[/yellow]")

        # Final confirmation
        confirm = Prompt.ask("\nProceed with selected stories? (y/n)", default="y").lower()
        if confirm in ['y', 'yes']:
            return selected_stories
        else:
            return []  # Continue loop