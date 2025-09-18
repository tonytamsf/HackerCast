#!/usr/bin/env python

import os
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import mimetypes

from flask import Flask, Response, send_file, request, jsonify
from feedgen.feed import FeedGenerator
from mutagen.mp3 import MP3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
AUDIO_DIR = Path("output/audio")
BASE_URL = "http://localhost:8080"
PODCAST_TITLE = "HackerCast"
PODCAST_DESCRIPTION = "Daily audio podcasts from the top Hacker News stories"
PODCAST_AUTHOR = "HackerCast"
PODCAST_EMAIL = "hackercast@example.com"
PODCAST_LANGUAGE = "en"
PODCAST_CATEGORY = "Technology"


class Episode:
    """Represents a podcast episode."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.filename = file_path.name
        self.creation_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        self.file_size = file_path.stat().st_size

        # Parse date from filename if possible (hackercast_YYYYMMDD_HHMMSS.mp3)
        try:
            parts = self.filename.replace('.mp3', '').split('_')
            if len(parts) >= 2 and parts[1].isdigit() and len(parts[1]) == 8:
                date_str = parts[1]
                self.date = datetime.strptime(date_str, '%Y%m%d')
            else:
                self.date = self.creation_time.replace(hour=0, minute=0, second=0, microsecond=0)
        except (ValueError, IndexError):
            self.date = self.creation_time.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get audio duration
        self.duration = self._get_duration()

    def _get_duration(self) -> Optional[int]:
        """Get audio duration in seconds."""
        try:
            audio = MP3(str(self.file_path))
            return int(audio.info.length) if audio.info.length else None
        except Exception as e:
            logger.warning(f"Could not get duration for {self.filename}: {e}")
            return None

    @property
    def title(self) -> str:
        """Generate episode title."""
        return f"HackerCast - {self.date.strftime('%B %d, %Y')}"

    @property
    def description(self) -> str:
        """Generate episode description."""
        return f"Daily compilation of top Hacker News stories from {self.date.strftime('%B %d, %Y')}"

    @property
    def url(self) -> str:
        """Get episode audio URL."""
        return f"{BASE_URL}/audio/{self.filename}"

    @property
    def guid(self) -> str:
        """Generate unique identifier for episode."""
        return f"{BASE_URL}/episode/{self.date.strftime('%Y-%m-%d')}"


class EpisodeManager:
    """Manages podcast episodes."""

    def __init__(self, audio_dir: Path):
        self.audio_dir = audio_dir
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def get_latest_episode_by_date(self, date: datetime) -> Optional[Episode]:
        """Get the latest episode for a specific date."""
        episodes = self._get_episodes_for_date(date)
        return max(episodes, key=lambda e: e.creation_time) if episodes else None

    def get_latest_episode(self) -> Optional[Episode]:
        """Get the most recent episode."""
        episodes = self._get_all_episodes()
        return max(episodes, key=lambda e: e.creation_time) if episodes else None

    def get_recent_episodes(self, days: int = 30) -> list[Episode]:
        """Get episodes from the last N days, one per day."""
        cutoff_date = datetime.now() - timedelta(days=days)
        episodes_by_date = {}

        for episode in self._get_all_episodes():
            if episode.date >= cutoff_date:
                date_key = episode.date.date()
                if date_key not in episodes_by_date or episode.creation_time > episodes_by_date[date_key].creation_time:
                    episodes_by_date[date_key] = episode

        return sorted(episodes_by_date.values(), key=lambda e: e.date, reverse=True)

    def _get_episodes_for_date(self, date: datetime) -> list[Episode]:
        """Get all episodes for a specific date."""
        episodes = []
        date_str = date.strftime('%Y%m%d')

        for file_path in self.audio_dir.glob('*.mp3'):
            episode = Episode(file_path)
            if date_str in episode.filename or episode.date.date() == date.date():
                episodes.append(episode)

        return episodes

    def _get_all_episodes(self) -> list[Episode]:
        """Get all episodes."""
        episodes = []
        for file_path in self.audio_dir.glob('*.mp3'):
            try:
                episodes.append(Episode(file_path))
            except Exception as e:
                logger.warning(f"Skipping invalid audio file {file_path}: {e}")
        return episodes


# Initialize episode manager
episode_manager = EpisodeManager(AUDIO_DIR)


@app.route('/')
def index():
    """Root endpoint with server information."""
    return jsonify({
        'service': 'HackerCast RSS Server',
        'version': '1.0.0',
        'endpoints': {
            'rss_feed': '/rss',
            'latest_episode': '/latest',
            'audio_files': '/audio/<filename>',
            'episodes_list': '/episodes'
        }
    })


@app.route('/rss')
def rss_feed():
    """Generate RSS feed for the podcast."""
    fg = FeedGenerator()
    fg.load_extension('podcast')

    # Feed metadata
    fg.title(PODCAST_TITLE)
    fg.link(href=BASE_URL, rel='alternate')
    fg.description(PODCAST_DESCRIPTION)
    fg.author({'name': PODCAST_AUTHOR, 'email': PODCAST_EMAIL})
    fg.language(PODCAST_LANGUAGE)
    fg.lastBuildDate(datetime.now(timezone.utc))

    # iTunes-specific tags
    fg.podcast.itunes_author(PODCAST_AUTHOR)
    fg.podcast.itunes_category('Technology')
    fg.podcast.itunes_summary(PODCAST_DESCRIPTION)
    fg.podcast.itunes_owner(name=PODCAST_AUTHOR, email=PODCAST_EMAIL)
    fg.podcast.itunes_explicit('no')

    # Add episodes (latest per day for the last 30 days)
    episodes = episode_manager.get_recent_episodes(30)

    for episode in episodes:
        fe = fg.add_entry()
        fe.title(episode.title)
        fe.description(episode.description)
        fe.enclosure(episode.url, str(episode.file_size), 'audio/mpeg')
        fe.guid(episode.guid)
        fe.pubDate(episode.creation_time.replace(tzinfo=timezone.utc))

        # iTunes-specific episode tags
        if episode.duration:
            fe.podcast.itunes_duration(episode.duration)
        fe.podcast.itunes_author(PODCAST_AUTHOR)
        fe.podcast.itunes_summary(episode.description)

    response = Response(fg.rss_str(pretty=True), mimetype='application/rss+xml')
    response.headers['Content-Type'] = 'application/rss+xml; charset=utf-8'
    return response


@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files."""
    file_path = AUDIO_DIR / filename

    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404

    if not file_path.suffix.lower() == '.mp3':
        return jsonify({'error': 'Invalid file type'}), 400

    return send_file(
        str(file_path),
        mimetype='audio/mpeg',
        as_attachment=False,
        conditional=True
    )


@app.route('/latest')
def latest_episode():
    """Get information about the latest episode."""
    episode = episode_manager.get_latest_episode()

    if not episode:
        return jsonify({'error': 'No episodes found'}), 404

    return jsonify({
        'title': episode.title,
        'description': episode.description,
        'date': episode.date.isoformat(),
        'creation_time': episode.creation_time.isoformat(),
        'filename': episode.filename,
        'url': episode.url,
        'file_size': episode.file_size,
        'duration': episode.duration
    })


@app.route('/episodes')
def list_episodes():
    """List all available episodes."""
    episodes = episode_manager.get_recent_episodes(90)  # Last 90 days

    return jsonify({
        'total': len(episodes),
        'episodes': [
            {
                'title': ep.title,
                'date': ep.date.isoformat(),
                'creation_time': ep.creation_time.isoformat(),
                'filename': ep.filename,
                'url': ep.url,
                'file_size': ep.file_size,
                'duration': ep.duration
            }
            for ep in episodes
        ]
    })


@app.route('/health')
def health_check():
    """Health check endpoint."""
    latest = episode_manager.get_latest_episode()
    return jsonify({
        'status': 'healthy',
        'audio_directory': str(AUDIO_DIR.absolute()),
        'latest_episode': latest.filename if latest else None,
        'total_episodes': len(episode_manager._get_all_episodes())
    })


if __name__ == '__main__':
    # Ensure audio directory exists
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting HackerCast RSS Server")
    logger.info(f"Audio directory: {AUDIO_DIR.absolute()}")
    logger.info(f"RSS feed available at: {BASE_URL}/rss")

    # Run the development server
    app.run(host='0.0.0.0', port=8080, debug=True)