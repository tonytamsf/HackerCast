"""Test helpers and utilities for E2E testing."""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import Mock, patch
import subprocess
import pytest

from main import HackerCastPipeline
from hn_api import HackerNewsStory
from scraper import ScrapedContent


class TemporaryTestEnvironment:
    """Manages temporary test environment with clean output directories."""

    def __init__(self):
        self.temp_dir = None
        self.original_env = {}

    def __enter__(self):
        """Setup temporary environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="hackercast_test_")

        # Store original environment variables
        env_vars = ['HACKERCAST_OUTPUT_DIR', 'GOOGLE_APPLICATION_CREDENTIALS']
        for var in env_vars:
            self.original_env[var] = os.environ.get(var)

        # Set test environment
        os.environ['HACKERCAST_OUTPUT_DIR'] = self.temp_dir

        # Create test output directories
        for subdir in ['data', 'audio', 'logs']:
            Path(self.temp_dir, subdir).mkdir(parents=True, exist_ok=True)

        return Path(self.temp_dir)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup temporary environment."""
        # Restore original environment
        for var, value in self.original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value

        # Cleanup temp directory
        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class CommandRunner:
    """Utility for running CLI commands with timeout and output capture."""

    @staticmethod
    def run_command(
        cmd: List[str],
        cwd: Optional[str] = None,
        timeout: int = 60,
        capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """
        Run a command and return (return_code, stdout, stderr).

        Args:
            cmd: Command and arguments as list
            cwd: Working directory
            timeout: Command timeout in seconds
            capture_output: Whether to capture stdout/stderr

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            if cwd is None:
                cwd = str(Path(__file__).parent.parent.parent)

            result = subprocess.run(
                cmd,
                cwd=cwd,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                env=dict(os.environ)
            )
            return result.returncode, result.stdout or "", result.stderr or ""
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return -2, "", f"Command failed: {str(e)}"


class PerformanceMonitor:
    """Monitor performance metrics during test execution."""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.metrics = {}

    def start(self):
        """Start performance monitoring."""
        self.start_time = time.time()

    def stop(self):
        """Stop performance monitoring."""
        self.end_time = time.time()
        self.metrics['duration'] = self.end_time - self.start_time

    def add_metric(self, name: str, value: Any):
        """Add a custom metric."""
        self.metrics[name] = value

    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        return self.metrics.copy()


class FileValidator:
    """Validate file outputs and content."""

    @staticmethod
    def validate_json_file(file_path: Path, required_keys: List[str] = None) -> Tuple[bool, str]:
        """
        Validate JSON file exists and has required structure.

        Args:
            file_path: Path to JSON file
            required_keys: Required top-level keys

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not file_path.exists():
                return False, f"File does not exist: {file_path}"

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if required_keys:
                missing_keys = [key for key in required_keys if key not in data]
                if missing_keys:
                    return False, f"Missing required keys: {missing_keys}"

            return True, ""
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"

    @staticmethod
    def validate_text_file(file_path: Path, min_length: int = 0) -> Tuple[bool, str]:
        """
        Validate text file exists and meets criteria.

        Args:
            file_path: Path to text file
            min_length: Minimum content length

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not file_path.exists():
                return False, f"File does not exist: {file_path}"

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if len(content) < min_length:
                return False, f"Content too short: {len(content)} < {min_length}"

            return True, ""
        except Exception as e:
            return False, f"Validation error: {e}"

    @staticmethod
    def validate_audio_file(file_path: Path, min_size_bytes: int = 1000) -> Tuple[bool, str]:
        """
        Validate audio file exists and meets basic criteria.

        Args:
            file_path: Path to audio file
            min_size_bytes: Minimum file size in bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not file_path.exists():
                return False, f"File does not exist: {file_path}"

            file_size = file_path.stat().st_size
            if file_size < min_size_bytes:
                return False, f"File too small: {file_size} < {min_size_bytes} bytes"

            # Check file extension
            if not file_path.suffix.lower() in ['.mp3', '.wav', '.m4a']:
                return False, f"Invalid audio file extension: {file_path.suffix}"

            return True, ""
        except Exception as e:
            return False, f"Validation error: {e}"


class DataValidator:
    """Validate data structures and content quality."""

    @staticmethod
    def validate_hn_stories(stories: List[HackerNewsStory]) -> Tuple[bool, str]:
        """
        Validate HackerNews stories data structure.

        Args:
            stories: List of HackerNews stories

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not stories:
            return False, "No stories provided"

        for i, story in enumerate(stories):
            if not story.id:
                return False, f"Story {i} missing ID"
            if not story.title:
                return False, f"Story {i} missing title"
            if not story.by:
                return False, f"Story {i} missing author"
            if story.score is None or story.score < 0:
                return False, f"Story {i} has invalid score: {story.score}"

        return True, ""

    @staticmethod
    def validate_scraped_content(content_list: List[ScrapedContent]) -> Tuple[bool, str]:
        """
        Validate scraped content quality.

        Args:
            content_list: List of scraped content

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not content_list:
            return False, "No content provided"

        for i, content in enumerate(content_list):
            if not content.title:
                return False, f"Content {i} missing title"
            if not content.content or len(content.content.strip()) < 100:
                return False, f"Content {i} has insufficient text content"
            if content.word_count < 50:
                return False, f"Content {i} has too few words: {content.word_count}"

        return True, ""

    @staticmethod
    def validate_podcast_script(script: str) -> Tuple[bool, str]:
        """
        Validate podcast script quality.

        Args:
            script: Generated podcast script

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not script or not script.strip():
            return False, "Script is empty"

        script = script.strip()

        # Check minimum length
        if len(script) < 500:
            return False, f"Script too short: {len(script)} characters"

        # Check for introduction
        if "hackercast" not in script.lower() or "welcome" not in script.lower():
            return False, "Script missing proper introduction"

        # Check for story structure
        story_markers = ["story 1", "story 2", "next up", "that wraps up"]
        found_markers = sum(1 for marker in story_markers if marker in script.lower())
        if found_markers < 2:
            return False, "Script missing proper story structure"

        return True, ""


def create_mock_hn_stories(count: int = 5) -> List[HackerNewsStory]:
    """Create mock HackerNews stories for testing."""
    stories = []
    for i in range(count):
        story = HackerNewsStory(
            id=1000 + i,
            title=f"Test Story {i+1}: Technology Innovation",
            by=f"testuser{i+1}",
            score=100 + i * 10,
            time=int(time.time()) - i * 3600,
            url=f"https://example.com/article-{i+1}",
            type="story"
        )
        stories.append(story)
    return stories


def create_mock_scraped_content(count: int = 3) -> List[ScrapedContent]:
    """Create mock scraped content for testing."""
    content_list = []
    for i in range(count):
        content = ScrapedContent(
            url=f"https://example.com/article-{i+1}",
            title=f"Test Article {i+1}",
            content=f"This is test content for article {i+1}. " * 50,  # ~250 words
            author=f"Test Author {i+1}",
            publish_date=None,
            word_count=250,
            scraping_method="mock",
            success=True
        )
        content_list.append(content)
    return content_list


class MetricsCollector:
    """Collect and analyze test metrics."""

    def __init__(self):
        self.metrics = {}

    def record_timing(self, operation: str, duration: float):
        """Record operation timing."""
        if 'timings' not in self.metrics:
            self.metrics['timings'] = {}
        self.metrics['timings'][operation] = duration

    def record_count(self, category: str, count: int):
        """Record count metrics."""
        if 'counts' not in self.metrics:
            self.metrics['counts'] = {}
        self.metrics['counts'][category] = count

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return self.metrics.copy()

    def assert_performance_thresholds(self):
        """Assert performance meets acceptable thresholds."""
        timings = self.metrics.get('timings', {})

        # Define performance thresholds (in seconds)
        thresholds = {
            'fetch_stories': 30.0,
            'scrape_articles': 60.0,
            'generate_script': 10.0,
            'full_pipeline': 120.0
        }

        for operation, threshold in thresholds.items():
            if operation in timings:
                actual = timings[operation]
                assert actual <= threshold, f"{operation} took {actual:.2f}s, exceeds threshold {threshold}s"