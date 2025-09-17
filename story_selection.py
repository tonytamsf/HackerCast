#!/usr/bin/env python

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from datetime import datetime

from hn_api import HackerNewsStory


@dataclass
class SelectableStory:
    """A story that can be selected/deselected for processing."""

    story: HackerNewsStory
    selected: bool = True  # Selected by default (opt-out design)
    preview_text: Optional[str] = None

    @property
    def display_title(self) -> str:
        """Get truncated title for display."""
        if len(self.story.title) <= 60:
            return self.story.title
        return self.story.title[:57] + "..."

    @property
    def has_url(self) -> bool:
        """Check if story has a valid URL."""
        return self.story.url is not None and self.story.url.strip() != ""

    @property
    def age_hours(self) -> int:
        """Get story age in hours."""
        now = datetime.now().timestamp()
        return int((now - self.story.time) / 3600)

    def toggle_selection(self) -> None:
        """Toggle the selection state."""
        self.selected = not self.selected


@dataclass
class StorySelection:
    """Manages selection state for a collection of stories."""

    stories: List[SelectableStory] = field(default_factory=list)
    _filter_query: str = ""
    _show_only_with_urls: bool = False

    def __post_init__(self):
        """Initialize after creation."""
        self._validate_stories()

    def _validate_stories(self) -> None:
        """Validate the stories list."""
        if not isinstance(self.stories, list):
            raise ValueError("Stories must be a list")

        for story in self.stories:
            if not isinstance(story, SelectableStory):
                raise ValueError("All items must be SelectableStory instances")

    @classmethod
    def from_hn_stories(cls, hn_stories: List[HackerNewsStory]) -> "StorySelection":
        """Create StorySelection from list of HackerNewsStory objects."""
        selectable_stories = [SelectableStory(story=story) for story in hn_stories]
        return cls(stories=selectable_stories)

    @property
    def total_count(self) -> int:
        """Total number of stories."""
        return len(self.stories)

    @property
    def selected_count(self) -> int:
        """Number of selected stories."""
        return sum(1 for story in self.stories if story.selected)

    @property
    def filtered_stories(self) -> List[SelectableStory]:
        """Get stories matching current filters."""
        filtered = self.stories

        # Apply URL filter
        if self._show_only_with_urls:
            filtered = [story for story in filtered if story.has_url]

        # Apply text filter
        if self._filter_query.strip():
            query_lower = self._filter_query.lower()
            filtered = [
                story for story in filtered
                if query_lower in story.story.title.lower() or
                   query_lower in story.story.by.lower()
            ]

        return filtered

    @property
    def selected_stories(self) -> List[HackerNewsStory]:
        """Get list of selected HackerNewsStory objects."""
        return [story.story for story in self.stories if story.selected]

    def get_story_by_index(self, index: int) -> Optional[SelectableStory]:
        """Get story by filtered list index."""
        filtered = self.filtered_stories
        if 0 <= index < len(filtered):
            return filtered[index]
        return None

    def toggle_story(self, index: int) -> bool:
        """Toggle story selection by filtered list index."""
        story = self.get_story_by_index(index)
        if story:
            story.toggle_selection()
            return True
        return False

    def select_all(self, filtered_only: bool = False) -> int:
        """Select all stories. Returns number of stories affected."""
        stories_to_select = self.filtered_stories if filtered_only else self.stories
        count = 0
        for story in stories_to_select:
            if not story.selected:
                story.selected = True
                count += 1
        return count

    def deselect_all(self, filtered_only: bool = False) -> int:
        """Deselect all stories. Returns number of stories affected."""
        stories_to_deselect = self.filtered_stories if filtered_only else self.stories
        count = 0
        for story in stories_to_deselect:
            if story.selected:
                story.selected = False
                count += 1
        return count

    def invert_selection(self, filtered_only: bool = False) -> int:
        """Invert selection for all stories. Returns number of stories affected."""
        stories_to_invert = self.filtered_stories if filtered_only else self.stories
        for story in stories_to_invert:
            story.toggle_selection()
        return len(stories_to_invert)

    def select_by_criteria(self, min_score: Optional[int] = None,
                          max_age_hours: Optional[int] = None,
                          has_url_only: bool = False) -> int:
        """Select stories by criteria. Returns number of stories selected."""
        count = 0
        for story in self.stories:
            should_select = True

            if min_score is not None and story.story.score < min_score:
                should_select = False

            if max_age_hours is not None and story.age_hours > max_age_hours:
                should_select = False

            if has_url_only and not story.has_url:
                should_select = False

            if should_select and not story.selected:
                story.selected = True
                count += 1

        return count

    def set_filter(self, query: str) -> None:
        """Set text filter query."""
        if not isinstance(query, str):
            raise TypeError("Filter query must be a string")
        self._filter_query = query.strip()

    def set_url_filter(self, show_only_with_urls: bool) -> None:
        """Set URL filter."""
        if not isinstance(show_only_with_urls, bool):
            raise TypeError("URL filter must be a boolean")
        self._show_only_with_urls = show_only_with_urls

    def clear_filters(self) -> None:
        """Clear all filters."""
        self._filter_query = ""
        self._show_only_with_urls = False

    def get_selection_summary(self) -> Dict[str, int]:
        """Get summary of current selection state."""
        return {
            "total": self.total_count,
            "selected": self.selected_count,
            "filtered": len(self.filtered_stories),
            "with_urls": sum(1 for s in self.stories if s.has_url),
            "selected_with_urls": sum(1 for s in self.stories if s.selected and s.has_url)
        }

    def validate_selection(self) -> Dict[str, List[str]]:
        """Validate current selection and return any issues."""
        issues = {
            "warnings": [],
            "errors": []
        }

        selected_stories = [s for s in self.stories if s.selected]

        if not selected_stories:
            issues["errors"].append("No stories selected")

        stories_without_urls = [s for s in selected_stories if not s.has_url]
        if stories_without_urls:
            issues["warnings"].append(
                f"{len(stories_without_urls)} selected stories have no URL and cannot be scraped"
            )

        if len(selected_stories) > 50:
            issues["warnings"].append(
                f"Large number of stories selected ({len(selected_stories)}). This may take a long time to process."
            )

        return issues