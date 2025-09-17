"""Tests for Hacker News API module."""

import json
import pytest
from unittest.mock import Mock, patch
import requests

from hn_api import HackerNewsAPI, HackerNewsStory, get_top_story_ids


class TestHackerNewsStory:
    """Test HackerNewsStory class."""

    def test_story_creation(self, mock_hn_story_data):
        """Test creating a story from data."""
        story = HackerNewsStory(**mock_hn_story_data)

        assert story.id == 12345
        assert story.title == "Test Story Title"
        assert story.url == "https://example.com/test-article"
        assert story.score == 150
        assert story.by == "testuser"
        assert story.time == 1642608000
        assert story.descendants == 42
        assert story.type == "story"

    def test_story_created_at_property(self, mock_hn_story_data):
        """Test created_at property."""
        story = HackerNewsStory(**mock_hn_story_data)
        created_at = story.created_at

        assert created_at.year == 2022
        assert created_at.month == 1
        assert created_at.day == 19

    def test_story_to_dict(self, mock_hn_story_data):
        """Test converting story to dictionary."""
        story = HackerNewsStory(**mock_hn_story_data)
        story_dict = story.to_dict()

        assert story_dict["id"] == 12345
        assert story_dict["title"] == "Test Story Title"
        assert story_dict["url"] == "https://example.com/test-article"
        assert "created_at" in story_dict


class TestHackerNewsAPI:
    """Test HackerNewsAPI class."""

    def test_api_initialization(self, test_config):
        """Test API client initialization."""
        with patch("hn_api.get_config", return_value=test_config):
            api = HackerNewsAPI()

            assert api.base_url == "https://hacker-news.firebaseio.com/v0"
            assert api.timeout == test_config.hackernews.timeout

    @patch("hn_api.requests.Session.get")
    def test_make_request_success(self, mock_get, test_config):
        """Test successful API request."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch("hn_api.get_config", return_value=test_config):
            api = HackerNewsAPI()
            result = api._make_request("test.json")

            assert result == {"test": "data"}
            mock_get.assert_called_once()

    @patch("hn_api.requests.Session.get")
    def test_make_request_timeout(self, mock_get, test_config):
        """Test API request timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        with patch("hn_api.get_config", return_value=test_config):
            api = HackerNewsAPI()
            result = api._make_request("test.json")

            assert result is None

    @patch("hn_api.requests.Session.get")
    def test_make_request_http_error(self, mock_get, test_config):
        """Test API request HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404"
        )
        mock_get.return_value = mock_response

        with patch("hn_api.get_config", return_value=test_config):
            api = HackerNewsAPI()
            result = api._make_request("test.json")

            assert result is None

    @patch("hn_api.requests.Session.get")
    def test_get_top_story_ids_success(
        self, mock_get, test_config, mock_hn_stories_list
    ):
        """Test getting top story IDs successfully."""
        mock_response = Mock()
        mock_response.json.return_value = mock_hn_stories_list + [
            12350,
            12351,
        ]  # Extra stories
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch("hn_api.get_config", return_value=test_config):
            api = HackerNewsAPI()
            story_ids = api.get_top_story_ids(5)

            assert story_ids == mock_hn_stories_list
            assert len(story_ids) == 5

    def test_get_top_story_ids_invalid_limit(self, test_config):
        """Test getting story IDs with invalid limit."""
        with patch("hn_api.get_config", return_value=test_config):
            api = HackerNewsAPI()
            story_ids = api.get_top_story_ids(-1)

            assert story_ids is None

    @patch("hn_api.requests.Session.get")
    def test_get_story_details_success(self, mock_get, test_config, mock_hn_story_data):
        """Test getting story details successfully."""
        mock_response = Mock()
        mock_response.json.return_value = mock_hn_story_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch("hn_api.get_config", return_value=test_config):
            api = HackerNewsAPI()
            story = api.get_story_details(12345)

            assert story is not None
            assert story.id == 12345
            assert story.title == "Test Story Title"

    @patch("hn_api.requests.Session.get")
    def test_get_story_details_missing_fields(self, mock_get, test_config):
        """Test getting story details with missing required fields."""
        incomplete_data = {"id": 12345, "title": "Test"}  # Missing required fields

        mock_response = Mock()
        mock_response.json.return_value = incomplete_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch("hn_api.get_config", return_value=test_config):
            api = HackerNewsAPI()
            story = api.get_story_details(12345)

            assert story is None

    @patch("hn_api.HackerNewsAPI.get_story_details")
    @patch("hn_api.HackerNewsAPI.get_top_story_ids")
    def test_get_top_stories_success(
        self, mock_get_ids, mock_get_details, test_config, mock_hn_story_data
    ):
        """Test getting complete top stories."""
        mock_get_ids.return_value = [12345, 12346]

        # Create story objects
        story1 = HackerNewsStory(**mock_hn_story_data)
        story2_data = mock_hn_story_data.copy()
        story2_data["id"] = 12346
        story2_data["title"] = "Second Story"
        story2 = HackerNewsStory(**story2_data)

        mock_get_details.side_effect = [story1, story2]

        with patch("hn_api.get_config", return_value=test_config):
            api = HackerNewsAPI()
            stories = api.get_top_stories(2)

            assert len(stories) == 2
            assert stories[0].title == "Test Story Title"
            assert stories[1].title == "Second Story"

    @patch("hn_api.HackerNewsAPI.get_top_story_ids")
    def test_get_top_stories_no_ids(self, mock_get_ids, test_config):
        """Test getting top stories when no IDs are returned."""
        mock_get_ids.return_value = None

        with patch("hn_api.get_config", return_value=test_config):
            api = HackerNewsAPI()
            stories = api.get_top_stories(5)

            assert stories == []


class TestLegacyFunctions:
    """Test legacy backward compatibility functions."""

    @patch("hn_api.HackerNewsAPI")
    def test_get_top_story_ids_legacy(self, mock_api_class):
        """Test legacy get_top_story_ids function."""
        mock_api = Mock()
        mock_api.get_top_story_ids.return_value = [12345, 12346]
        mock_api_class.return_value = mock_api

        result = get_top_story_ids(2)

        assert result == [12345, 12346]
        mock_api.get_top_story_ids.assert_called_once_with(2)
