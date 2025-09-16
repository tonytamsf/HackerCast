#!/usr/bin/env python

import requests
import sys
import json

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

def get_story_details(story_id):
    """Fetches the details of a story from the Hacker News API."""
    try:
        item_url = f"{HN_API_BASE_URL}/item/{story_id}.json"
        response = requests.get(item_url)
        response.raise_for_status()
        story_details = response.json()
        return {
            "title": story_details.get("title"),
            "url": story_details.get("url"),
            "score": story_details.get("score")
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching story details for ID {story_id}: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hn_api.py <command> [args]", file=sys.stderr)
        print("Commands:", file=sys.stderr)
        print("  top [limit] - Get top story IDs", file=sys.stderr)
        print("  story <story_id> - Get story details", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "top":
        limit = 20
        if len(sys.argv) > 2:
            try:
                limit = int(sys.argv[2])
            except ValueError:
                print("Usage: python hn_api.py top [limit]", file=sys.stderr)
                sys.exit(1)
        story_ids = get_top_story_ids(limit)
        if story_ids:
            for story_id in story_ids:
                print(story_id)

    elif command == "story":
        if len(sys.argv) != 3:
            print("Usage: python hn_api.py story <story_id>", file=sys.stderr)
            sys.exit(1)
        try:
            story_id = int(sys.argv[2])
        except ValueError:
            print("Error: story_id must be an integer.", file=sys.stderr)
            sys.exit(1)
        
        details = get_story_details(story_id)
        if details:
            print(json.dumps(details, indent=4))

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)