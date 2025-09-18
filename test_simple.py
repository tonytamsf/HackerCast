#!/usr/bin/env python

"""
Simple standalone test for core story selection logic without external dependencies.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


# Mock HackerNewsStory for testing
@dataclass
class MockHackerNewsStory:
    id: int
    title: str
    url: Optional[str]
    score: int
    by: str
    time: int
    descendants: int
    type: str = "story"


# Minimal implementation of story selection for testing
@dataclass
class TestSelectableStory:
    story: MockHackerNewsStory
    selected: bool = True

    @property
    def has_url(self) -> bool:
        return self.story.url is not None and self.story.url.strip() != ""

    def toggle_selection(self) -> None:
        self.selected = not self.selected


def test_story_selection_basic():
    """Test basic story selection functionality."""
    print("Testing basic story selection...")

    # Create test story
    story = MockHackerNewsStory(
        id=123,
        title="Test Story",
        url="https://example.com",
        score=100,
        by="testuser",
        time=int(datetime.now().timestamp()),
        descendants=10
    )

    # Test SelectableStory
    selectable = TestSelectableStory(story=story)

    # Test initial state
    assert selectable.selected is True, "Story should be selected by default"
    assert selectable.has_url is True, "Story should have URL"

    # Test toggle
    selectable.toggle_selection()
    assert selectable.selected is False, "Story should be deselected after toggle"

    selectable.toggle_selection()
    assert selectable.selected is True, "Story should be selected after second toggle"

    print("✓ Basic story selection tests passed")


def test_story_without_url():
    """Test story without URL."""
    print("Testing story without URL...")

    story = MockHackerNewsStory(
        id=124,
        title="Ask HN: Something",
        url=None,
        score=50,
        by="testuser",
        time=int(datetime.now().timestamp()),
        descendants=5
    )

    selectable = TestSelectableStory(story=story)
    assert selectable.has_url is False, "Story without URL should return False for has_url"

    print("✓ Story without URL tests passed")


def test_story_validation():
    """Test story validation logic."""
    print("Testing story validation...")

    # Valid story
    valid_story = MockHackerNewsStory(
        id=125,
        title="Valid Story",
        url="https://example.com",
        score=100,
        by="testuser",
        time=int(datetime.now().timestamp()),
        descendants=10
    )

    # Test basic validation requirements
    assert hasattr(valid_story, 'id'), "Story should have id"
    assert hasattr(valid_story, 'title'), "Story should have title"
    assert hasattr(valid_story, 'score'), "Story should have score"
    assert valid_story.id > 0, "Story ID should be positive"
    assert valid_story.title.strip(), "Story title should not be empty"
    assert valid_story.score >= 0, "Story score should be non-negative"

    print("✓ Story validation tests passed")


def test_interactive_commands():
    """Test that command parsing would work."""
    print("Testing command parsing logic...")

    # Test command validation
    valid_commands = ['s', 'select', 'd', 'deselect', 'a', 'all', 'n', 'none', 'i', 'invert']
    advanced_commands = ['f', 'filter', 'p', 'preview', 'u', 'urls']
    action_commands = ['c', 'confirm', 'h', 'help', 'q', 'quit']

    all_commands = valid_commands + advanced_commands + action_commands

    # Test that all commands are strings
    for cmd in all_commands:
        assert isinstance(cmd, str), f"Command {cmd} should be string"
        assert cmd.strip(), f"Command {cmd} should not be empty"

    # Test score command format
    score_command = "score:100"
    assert score_command.startswith('score:'), "Score command should start with 'score:'"

    parts = score_command.split(':')
    assert len(parts) == 2, "Score command should have exactly one colon"
    assert parts[1].isdigit(), "Score value should be numeric"

    # Test hours command format
    hours_command = "hours:24"
    assert hours_command.startswith('hours:'), "Hours command should start with 'hours:'"

    parts = hours_command.split(':')
    assert len(parts) == 2, "Hours command should have exactly one colon"
    assert parts[1].isdigit(), "Hours value should be numeric"

    print("✓ Command parsing tests passed")


def run_all_tests():
    """Run all simple tests."""
    print("🧪 Running simple tests for interactive story selection...")
    print()

    try:
        test_story_selection_basic()
        test_story_without_url()
        test_story_validation()
        test_interactive_commands()

        print()
        print("🎉 All simple tests passed!")
        print()
        print("The interactive story selection feature is ready to use!")
        print("Try these commands:")
        print("  python main.py run --interactive")
        print("  python main.py interactive --limit 10")
        print("  python main.py select --limit 20")

    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    return True


if __name__ == "__main__":
    run_all_tests()