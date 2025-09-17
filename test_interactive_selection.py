#!/usr/bin/env python

"""
Basic tests for the interactive story selection feature.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from hn_api import HackerNewsStory
from story_selection import SelectableStory, StorySelection
from interactive_selector import InteractiveStorySelector


class TestSelectableStory:
    """Test SelectableStory functionality."""

    def test_create_selectable_story(self):
        """Test creating a SelectableStory."""
        story = HackerNewsStory(
            id=123,
            title="Test Story",
            url="https://example.com",
            score=100,
            by="testuser",
            time=int(datetime.now().timestamp()),
            descendants=10
        )

        selectable = SelectableStory(story=story)

        assert selectable.story == story
        assert selectable.selected is True  # Default selected
        assert selectable.has_url is True
        assert "Test Story" in selectable.display_title

    def test_story_without_url(self):
        """Test story without URL."""
        story = HackerNewsStory(
            id=124,
            title="Ask HN: Something",
            url=None,
            score=50,
            by="testuser",
            time=int(datetime.now().timestamp()),
            descendants=5
        )

        selectable = SelectableStory(story=story)

        assert selectable.has_url is False

    def test_toggle_selection(self):
        """Test toggling story selection."""
        story = HackerNewsStory(
            id=125,
            title="Test Story",
            url="https://example.com",
            score=100,
            by="testuser",
            time=int(datetime.now().timestamp()),
            descendants=10
        )

        selectable = SelectableStory(story=story)
        initial_state = selectable.selected

        selectable.toggle_selection()
        assert selectable.selected != initial_state

        selectable.toggle_selection()
        assert selectable.selected == initial_state

    def test_age_calculation(self):
        """Test story age calculation."""
        # Story from 2 hours ago
        two_hours_ago = int(datetime.now().timestamp()) - (2 * 3600)
        story = HackerNewsStory(
            id=126,
            title="Test Story",
            url="https://example.com",
            score=100,
            by="testuser",
            time=two_hours_ago,
            descendants=10
        )

        selectable = SelectableStory(story=story)
        assert selectable.age_hours >= 1  # Should be around 2, but allow some tolerance


class TestStorySelection:
    """Test StorySelection functionality."""

    def create_test_stories(self, count=5):
        """Create test stories for testing."""
        stories = []
        now = int(datetime.now().timestamp())

        for i in range(count):
            story = HackerNewsStory(
                id=1000 + i,
                title=f"Test Story {i+1}",
                url=f"https://example.com/story{i+1}" if i % 2 == 0 else None,
                score=100 + (i * 10),
                by=f"user{i+1}",
                time=now - (i * 3600),  # Each story 1 hour older
                descendants=10 + i
            )
            stories.append(story)

        return stories

    def test_create_from_hn_stories(self):
        """Test creating StorySelection from HackerNewsStory objects."""
        hn_stories = self.create_test_stories(3)
        selection = StorySelection.from_hn_stories(hn_stories)

        assert selection.total_count == 3
        assert selection.selected_count == 3  # All selected by default
        assert len(selection.selected_stories) == 3

    def test_selection_counts(self):
        """Test selection counting."""
        hn_stories = self.create_test_stories(5)
        selection = StorySelection.from_hn_stories(hn_stories)

        # Deselect first story
        selection.stories[0].selected = False

        assert selection.total_count == 5
        assert selection.selected_count == 4

    def test_filtering(self):
        """Test story filtering."""
        hn_stories = self.create_test_stories(5)
        selection = StorySelection.from_hn_stories(hn_stories)

        # Test URL filter
        selection.set_url_filter(True)
        filtered = selection.filtered_stories

        # Should have 3 stories with URLs (even indices)
        assert len(filtered) == 3

        # Test text filter
        selection.clear_filters()
        selection.set_filter("Story 1")
        filtered = selection.filtered_stories

        assert len(filtered) == 1
        assert "Story 1" in filtered[0].story.title

    def test_bulk_operations(self):
        """Test bulk selection operations."""
        hn_stories = self.create_test_stories(5)
        selection = StorySelection.from_hn_stories(hn_stories)

        # Deselect all
        count = selection.deselect_all()
        assert count == 5
        assert selection.selected_count == 0

        # Select all
        count = selection.select_all()
        assert count == 5
        assert selection.selected_count == 5

        # Invert selection
        count = selection.invert_selection()
        assert count == 5
        assert selection.selected_count == 0

    def test_select_by_criteria(self):
        """Test selecting stories by criteria."""
        hn_stories = self.create_test_stories(5)
        selection = StorySelection.from_hn_stories(hn_stories)

        # Deselect all first
        selection.deselect_all()

        # Select stories with score >= 120
        count = selection.select_by_criteria(min_score=120)

        # Should select stories with scores 120, 130, 140
        assert count == 3
        assert selection.selected_count == 3

    def test_validation(self):
        """Test selection validation."""
        hn_stories = self.create_test_stories(3)
        selection = StorySelection.from_hn_stories(hn_stories)

        validation = selection.validate_selection()

        # Should have warnings about stories without URLs
        assert "warnings" in validation
        assert len(validation["warnings"]) > 0

    def test_get_story_by_index(self):
        """Test getting story by filtered index."""
        hn_stories = self.create_test_stories(5)
        selection = StorySelection.from_hn_stories(hn_stories)

        story = selection.get_story_by_index(0)
        assert story is not None
        assert story.story.id == 1000

        # Test invalid index
        story = selection.get_story_by_index(10)
        assert story is None

    def test_toggle_story(self):
        """Test toggling story by index."""
        hn_stories = self.create_test_stories(3)
        selection = StorySelection.from_hn_stories(hn_stories)

        initial_state = selection.stories[0].selected
        success = selection.toggle_story(0)

        assert success is True
        assert selection.stories[0].selected != initial_state


class TestInteractiveSelector:
    """Test InteractiveStorySelector functionality."""

    def create_test_stories(self, count=3):
        """Create test stories for testing."""
        stories = []
        now = int(datetime.now().timestamp())

        for i in range(count):
            story = HackerNewsStory(
                id=2000 + i,
                title=f"Interactive Test Story {i+1}",
                url=f"https://example.com/story{i+1}",
                score=100 + (i * 10),
                by=f"user{i+1}",
                time=now - (i * 3600),
                descendants=10 + i
            )
            stories.append(story)

        return stories

    def test_input_validation(self):
        """Test input validation for story selection."""
        from rich.console import Console

        selector = InteractiveStorySelector(Console())

        # Test with empty list
        result = selector.select_stories([])
        assert result == []

        # Test with invalid input type
        with pytest.raises(TypeError):
            selector.select_stories("not a list")

    @patch('interactive_selector.Prompt.ask')
    def test_selector_initialization(self, mock_prompt):
        """Test that selector initializes properly with valid stories."""
        from rich.console import Console

        mock_prompt.return_value = "q"  # Quit immediately

        stories = self.create_test_stories(3)
        selector = InteractiveStorySelector(Console())

        result = selector.select_stories(stories)

        # Should initialize selection object
        assert selector.selection is not None
        assert selector.selection.total_count == 3


def run_basic_tests():
    """Run basic functionality tests without pytest."""
    print("Running basic functionality tests...")

    # Test SelectableStory
    print("✓ Testing SelectableStory...")
    test_selectable = TestSelectableStory()
    test_selectable.test_create_selectable_story()
    test_selectable.test_toggle_selection()
    print("  ✓ SelectableStory tests passed")

    # Test StorySelection
    print("✓ Testing StorySelection...")
    test_selection = TestStorySelection()
    test_selection.test_create_from_hn_stories()
    test_selection.test_selection_counts()
    test_selection.test_filtering()
    test_selection.test_bulk_operations()
    print("  ✓ StorySelection tests passed")

    # Test InteractiveSelector
    print("✓ Testing InteractiveSelector...")
    test_selector = TestInteractiveSelector()
    test_selector.test_input_validation()
    print("  ✓ InteractiveSelector tests passed")

    print("\n🎉 All basic tests passed!")


if __name__ == "__main__":
    run_basic_tests()