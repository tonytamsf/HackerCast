"""Pytest configuration and fixtures."""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from config import ConfigManager, AppConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_config():
    """Create a test configuration."""
    with patch.dict(
        "os.environ",
        {
            "HACKERCAST_ENV": "test",
            "HACKERCAST_DEBUG": "true",
            "HN_MAX_STORIES": "5",
            "LOG_LEVEL": "DEBUG",
            "OUTPUT_BASE_DIR": "/tmp/hackercast_test",
        },
    ):
        config_manager = ConfigManager()
        yield config_manager.config


@pytest.fixture
def mock_hn_story_data():
    """Mock Hacker News story data."""
    return {
        "id": 12345,
        "title": "Test Story Title",
        "url": "https://example.com/test-article",
        "score": 150,
        "by": "testuser",
        "time": 1642608000,  # Unix timestamp
        "descendants": 42,
        "type": "story",
    }


@pytest.fixture
def mock_hn_stories_list():
    """Mock list of Hacker News story IDs."""
    return [12345, 12346, 12347, 12348, 12349]


@pytest.fixture
def mock_scraped_content():
    """Mock scraped content data."""
    return {
        "url": "https://example.com/test-article",
        "title": "Test Article Title",
        "content": "This is test content for the article. " * 50,  # ~250 words
        "author": "Test Author",
        "published_date": "2022-01-19T12:00:00",
        "meta_description": "Test meta description",
        "word_count": 250,
        "scraping_method": "mock",
    }


@pytest.fixture
def mock_requests_response():
    """Mock requests.Response object."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.json.return_value = {"test": "data"}
    mock_response.content = b"<html><body>Test content</body></html>"
    mock_response.raise_for_status.return_value = None
    return mock_response


@pytest.fixture
def mock_google_tts_client():
    """Mock Google TTS client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.audio_content = b"fake_audio_data"
    mock_client.synthesize_speech.return_value = mock_response
    return mock_client


@pytest.fixture(autouse=True)
def setup_test_environment(temp_dir):
    """Set up test environment for all tests."""
    # Create test output directories
    output_dir = temp_dir / "output"
    (output_dir / "audio").mkdir(parents=True)
    (output_dir / "data").mkdir(parents=True)
    (output_dir / "logs").mkdir(parents=True)

    # Patch environment variables
    with patch.dict(
        "os.environ", {"OUTPUT_BASE_DIR": str(output_dir), "HACKERCAST_ENV": "test"}
    ):
        yield
