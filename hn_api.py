#!/usr/bin/env python

import json
import logging
import sys
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import get_config

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class HackerNewsStory:
    """Represents a Hacker News story."""
    id: int
    title: str
    url: Optional[str]
    score: int
    by: str
    time: int
    descendants: int
    type: str = "story"

    @property
    def created_at(self) -> datetime:
        """Get the story creation datetime."""
        return datetime.fromtimestamp(self.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert story to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'score': self.score,
            'by': self.by,
            'time': self.time,
            'descendants': self.descendants,
            'type': self.type,
            'created_at': self.created_at.isoformat()
        }

class HackerNewsAPI:
    """Enhanced Hacker News API client with retry logic and error handling."""

    def __init__(self, base_url: str = "https://hacker-news.firebaseio.com/v0"):
        """
        Initialize the HN API client.

        Args:
            base_url: Base URL for the Hacker News API
        """
        self.base_url = base_url
        self.config = get_config()

        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.config.hackernews.retry_attempts,
            backoff_factor=self.config.hackernews.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set timeout
        self.timeout = self.config.hackernews.timeout

        logger.info(f"Initialized HN API client with base URL: {base_url}")

    def _make_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Make a request to the HN API.

        Args:
            endpoint: API endpoint to call

        Returns:
            JSON response data or None if failed
        """
        url = f"{self.base_url}/{endpoint}"

        try:
            logger.debug(f"Making request to: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Successfully fetched data from: {url}")
            return data

        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error for {url}: {e}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for {url}: {e}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            return None

    def get_top_story_ids(self, limit: Optional[int] = None) -> Optional[List[int]]:
        """
        Fetch the top story IDs from the Hacker News API.

        Args:
            limit: Maximum number of story IDs to return

        Returns:
            List of story IDs or None if failed
        """
        if limit is None:
            limit = self.config.hackernews.max_stories

        if limit <= 0:
            logger.error(f"Invalid limit: {limit}")
            return None

        logger.info(f"Fetching top {limit} story IDs")

        data = self._make_request("topstories.json")
        if data is None:
            return None

        if not isinstance(data, list):
            logger.error(f"Expected list, got {type(data)}")
            return None

        story_ids = data[:limit]
        logger.info(f"Successfully fetched {len(story_ids)} story IDs")
        return story_ids

    def get_story_details(self, story_id: int) -> Optional[HackerNewsStory]:
        """
        Fetch details for a specific story.

        Args:
            story_id: The story ID to fetch

        Returns:
            HackerNewsStory object or None if failed
        """
        logger.debug(f"Fetching story details for ID: {story_id}")

        data = self._make_request(f"item/{story_id}.json")
        if data is None:
            return None

        # Validate required fields
        required_fields = ['id', 'title', 'score', 'by', 'time', 'descendants']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            logger.warning(f"Story {story_id} missing fields: {missing_fields}")
            return None

        # Create story object
        try:
            story = HackerNewsStory(
                id=data['id'],
                title=data['title'],
                url=data.get('url'),  # URL is optional for some stories
                score=data['score'],
                by=data['by'],
                time=data['time'],
                descendants=data['descendants'],
                type=data.get('type', 'story')
            )

            logger.debug(f"Successfully parsed story: {story.title}")
            return story

        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Error parsing story {story_id}: {e}")
            return None

    def get_top_stories(self, limit: Optional[int] = None) -> List[HackerNewsStory]:
        """
        Fetch complete details for top stories.

        Args:
            limit: Maximum number of stories to return

        Returns:
            List of HackerNewsStory objects
        """
        story_ids = self.get_top_story_ids(limit)
        if not story_ids:
            return []

        stories = []
        failed_count = 0

        logger.info(f"Fetching details for {len(story_ids)} stories")

        for i, story_id in enumerate(story_ids, 1):
            story = self.get_story_details(story_id)

            if story:
                stories.append(story)
                logger.debug(f"Progress: {i}/{len(story_ids)} - {story.title}")
            else:
                failed_count += 1
                logger.warning(f"Failed to fetch story {story_id}")

            # Add small delay to be respectful to the API
            if i < len(story_ids):
                time.sleep(0.1)

        logger.info(f"Successfully fetched {len(stories)} stories, {failed_count} failed")
        return stories

def get_top_story_ids(limit: int = 20) -> Optional[List[int]]:
    """
    Legacy function for backward compatibility.

    Args:
        limit: Maximum number of story IDs to return

    Returns:
        List of story IDs or None if failed
    """
    api = HackerNewsAPI()
    return api.get_top_story_ids(limit)

def main():
    """Command-line interface for the HN API."""
    limit = 20

    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            if limit <= 0:
                raise ValueError("Limit must be positive")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            print("Usage: python hn_api.py [limit]", file=sys.stderr)
            sys.exit(1)

    try:
        api = HackerNewsAPI()
        story_ids = api.get_top_story_ids(limit)

        if story_ids:
            for story_id in story_ids:
                print(story_id)
        else:
            print("Failed to fetch story IDs", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
