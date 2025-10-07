#!/usr/bin/env python

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PodcastEpisode:
    """Represents a single podcast episode."""

    def __init__(
        self,
        date: str,
        audio_file: Path,
        title: str,
        description: str,
        duration_seconds: int = 0,
        file_size: int = 0,
        chapters_url: Optional[str] = None,
    ):
        self.date = date  # YYYYMMDD format
        self.audio_file = audio_file
        self.title = title
        self.description = description
        self.duration_seconds = duration_seconds
        self.file_size = file_size
        self.chapters_url = chapters_url

        # Parse date
        self.pub_date = datetime.strptime(date, "%Y%m%d")

    @property
    def audio_url(self) -> str:
        """Get the URL path for the audio file."""
        # Relative path from output directory
        return f"/audio/{self.date}/latest.mp3"

    @property
    def guid(self) -> str:
        """Get a unique GUID for this episode."""
        return f"hackercast-{self.date}"

    @property
    def rfc822_date(self) -> str:
        """Get publication date in RFC 822 format."""
        return self.pub_date.strftime("%a, %d %b %Y 00:00:00 GMT")

    @property
    def duration_formatted(self) -> str:
        """Get duration in HH:MM:SS format."""
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class RSSFeedGenerator:
    """Generate RSS feed for HackerCast podcast."""

    def __init__(
        self,
        output_dir: str = "output",
        base_url: Optional[str] = None,
        podcast_title: str = "HackerCast",
        podcast_description: str = "Your daily digest of the top stories from Hacker News",
        podcast_author: str = "HackerCast",
        podcast_email: str = "hackercast@example.com",
        podcast_language: str = "en-us",
        podcast_category: str = "Technology",
    ):
        self.output_dir = Path(output_dir)
        if base_url is None:
            base_url = os.environ.get("HACKERCAST_BASE_URL", "http://localhost:8080")
        self.base_url = base_url.rstrip('/')
        self.podcast_title = podcast_title
        self.podcast_description = podcast_description
        self.podcast_author = podcast_author
        self.podcast_email = podcast_email
        self.podcast_language = podcast_language
        self.podcast_category = podcast_category

    def scan_episodes(self) -> List[PodcastEpisode]:
        """Scan output directory for podcast episodes."""
        episodes = []
        audio_dir = self.output_dir / "audio"

        if not audio_dir.exists():
            logger.warning(f"Audio directory does not exist: {audio_dir}")
            return episodes

        # Find all date-based subdirectories (YYYYMMDD format)
        for date_dir in sorted(audio_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue

            # Check if directory name is in YYYYMMDD format
            date_str = date_dir.name
            if not (len(date_str) == 8 and date_str.isdigit()):
                continue

            # Look for latest.mp3
            audio_file = date_dir / "latest.mp3"
            if not audio_file.exists():
                logger.debug(f"No latest.mp3 found in {date_dir}")
                continue

            # Get file size
            file_size = audio_file.stat().st_size

            # Check for chapter file
            chapters_file = audio_file.with_suffix('.chapters.json')
            chapters_url = None
            if chapters_file.exists():
                chapters_url = f"/audio/{date_str}/latest.chapters.json"
                logger.info(f"Found chapters file for {date_str}")

            # Try to load metadata from pipeline data
            data_dir = self.output_dir / "data" / date_str
            metadata_file = data_dir / "latest.json"

            title = f"HackerCast - {date_str}"
            description = "Daily digest of top Hacker News stories"
            duration = 0

            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)

                    # Extract title and description from metadata
                    num_stories = metadata.get('stats', {}).get('stories_fetched', 0)
                    num_articles = metadata.get('stats', {}).get('articles_scraped', 0)

                    if num_articles > 0:
                        title = f"HackerCast - {date_str} - Top {num_articles} Stories"

                        # Build description from story titles
                        stories = metadata.get('stories', [])
                        if stories:
                            story_titles = [s.get('title', '') for s in stories[:5]]
                            description = f"Today's top Hacker News stories:\n\n" + "\n".join(
                                f"• {title}" for title in story_titles if title
                            )

                except Exception as e:
                    logger.warning(f"Failed to load metadata from {metadata_file}: {e}")

            # Try to get audio duration using ffprobe if available
            try:
                import subprocess
                result = subprocess.run(
                    ['ffprobe', '-v', 'error', '-show_entries',
                     'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                     str(audio_file)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    duration = int(float(result.stdout.strip()))
            except Exception as e:
                logger.debug(f"Could not get duration for {audio_file}: {e}")

            episode = PodcastEpisode(
                date=date_str,
                audio_file=audio_file,
                title=title,
                description=description,
                duration_seconds=duration,
                file_size=file_size,
                chapters_url=chapters_url,
            )
            episodes.append(episode)
            logger.info(f"Found episode: {episode.title} ({file_size} bytes)")

        return episodes

    def generate_rss(self, episodes: List[PodcastEpisode]) -> str:
        """Generate RSS feed XML."""
        # Create root RSS element
        rss = ET.Element('rss', {
            'version': '2.0',
            'xmlns:itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
            'xmlns:atom': 'http://www.w3.org/2005/Atom',
            'xmlns:podcast': 'https://podcastindex.org/namespace/1.0',
        })

        # Create channel
        channel = ET.SubElement(rss, 'channel')

        # Add channel metadata
        ET.SubElement(channel, 'title').text = self.podcast_title
        ET.SubElement(channel, 'description').text = self.podcast_description
        ET.SubElement(channel, 'language').text = self.podcast_language
        ET.SubElement(channel, 'link').text = self.base_url

        # Add atom:link for self-reference
        ET.SubElement(channel, '{http://www.w3.org/2005/Atom}link', {
            'href': f"{self.base_url}/rss.xml",
            'rel': 'self',
            'type': 'application/rss+xml'
        })

        # iTunes specific tags
        ET.SubElement(channel, '{http://www.itunes.com/dtds/podcast-1.0.dtd}author').text = self.podcast_author
        ET.SubElement(channel, '{http://www.itunes.com/dtds/podcast-1.0.dtd}summary').text = self.podcast_description

        itunes_owner = ET.SubElement(channel, '{http://www.itunes.com/dtds/podcast-1.0.dtd}owner')
        ET.SubElement(itunes_owner, '{http://www.itunes.com/dtds/podcast-1.0.dtd}name').text = self.podcast_author
        ET.SubElement(itunes_owner, '{http://www.itunes.com/dtds/podcast-1.0.dtd}email').text = self.podcast_email

        ET.SubElement(channel, '{http://www.itunes.com/dtds/podcast-1.0.dtd}explicit').text = 'no'

        itunes_category = ET.SubElement(channel, '{http://www.itunes.com/dtds/podcast-1.0.dtd}category', {
            'text': self.podcast_category
        })

        # Add episodes
        for episode in episodes:
            item = ET.SubElement(channel, 'item')

            ET.SubElement(item, 'title').text = episode.title
            ET.SubElement(item, 'description').text = episode.description
            ET.SubElement(item, 'pubDate').text = episode.rfc822_date
            ET.SubElement(item, 'guid', {'isPermaLink': 'false'}).text = episode.guid

            # Enclosure (audio file)
            enclosure = ET.SubElement(item, 'enclosure', {
                'url': f"{self.base_url}{episode.audio_url}",
                'length': str(episode.file_size),
                'type': 'audio/mpeg'
            })

            # iTunes specific tags
            ET.SubElement(item, '{http://www.itunes.com/dtds/podcast-1.0.dtd}author').text = self.podcast_author
            ET.SubElement(item, '{http://www.itunes.com/dtds/podcast-1.0.dtd}summary').text = episode.description

            if episode.duration_seconds > 0:
                ET.SubElement(item, '{http://www.itunes.com/dtds/podcast-1.0.dtd}duration').text = episode.duration_formatted

            # Add podcast namespace chapters if available
            if episode.chapters_url:
                ET.SubElement(item, '{https://podcastindex.org/namespace/1.0}chapters', {
                    'url': f"{self.base_url}{episode.chapters_url}",
                    'type': 'application/json+chapters'
                })

        # Convert to pretty-printed XML string
        xml_str = ET.tostring(rss, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')

    def generate_and_save(self, output_file: str = "output/rss.xml") -> Path:
        """Generate RSS feed and save to file."""
        logger.info("Scanning for podcast episodes...")
        episodes = self.scan_episodes()

        if not episodes:
            logger.warning("No episodes found!")
        else:
            logger.info(f"Found {len(episodes)} episodes")

        logger.info("Generating RSS feed...")
        rss_xml = self.generate_rss(episodes)

        # Ensure output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write RSS feed
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rss_xml)

        logger.info(f"RSS feed saved to: {output_path}")
        return output_path


def main():
    """Main entry point for RSS feed generation."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate RSS feed for HackerCast podcast')
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Output directory containing audio and data subdirectories'
    )
    parser.add_argument(
        '--output-file',
        default='output/rss.xml',
        help='Path to save RSS feed XML file'
    )
    parser.add_argument(
        '--base-url',
        default=None,
        help='Base URL for podcast server. Defaults to HACKERCAST_BASE_URL env var or http://localhost:8080'
    )
    parser.add_argument(
        '--title',
        default='HackerCast',
        help='Podcast title'
    )
    parser.add_argument(
        '--description',
        default='Your daily digest of the top stories from Hacker News',
        help='Podcast description'
    )
    parser.add_argument(
        '--author',
        default='HackerCast',
        help='Podcast author'
    )
    parser.add_argument(
        '--email',
        default='hackercast@example.com',
        help='Podcast author email'
    )

    args = parser.parse_args()

    generator = RSSFeedGenerator(
        output_dir=args.output_dir,
        base_url=args.base_url,
        podcast_title=args.title,
        podcast_description=args.description,
        podcast_author=args.author,
        podcast_email=args.email,
    )

    generator.generate_and_save(args.output_file)


if __name__ == '__main__':
    main()
