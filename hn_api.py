#!/usr/bin/env python

import requests
import sys

HN_API_BASE_URL = "https://hacker-news.firebaseio.com/v0"

def get_top_story_ids(limit=20):
    """Fetches the top story IDs from the Hacker News API."""
    try:
        top_stories_url = f"{HN_API_BASE_URL}/topstories.json"
        response = requests.get(top_stories_url)
        response.raise_for_status()
        story_ids = response.json()
        return story_ids[:limit]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching top stories: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    limit = 20
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("Usage: python hn_api.py [limit]", file=sys.stderr)
            sys.exit(1)

    story_ids = get_top_story_ids(limit)
    if story_ids:
        for story_id in story_ids:
            print(story_id)
