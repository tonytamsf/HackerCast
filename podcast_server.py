#!/usr/bin/env python

import os
import logging
from pathlib import Path
from flask import Flask, send_file, send_from_directory, render_template_string, abort
from rss_generator import RSSFeedGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Configuration
OUTPUT_DIR = Path(os.getenv('HACKERCAST_OUTPUT_DIR', 'output'))
BASE_URL = os.getenv('HACKERCAST_BASE_URL', 'http://localhost:5000')
RSS_FILE = OUTPUT_DIR / 'rss.xml'

# Simple HTML template for index page
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HackerCast - Daily Hacker News Podcast</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }
        h1 {
            color: #ff6600;
            border-bottom: 2px solid #ff6600;
            padding-bottom: 10px;
        }
        h2 {
            color: #444;
            margin-top: 30px;
        }
        .episode {
            background: #f5f5f5;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #ff6600;
        }
        .episode h3 {
            margin-top: 0;
            color: #333;
        }
        .episode-meta {
            color: #666;
            font-size: 0.9em;
        }
        .subscribe {
            background: #ff6600;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            display: inline-block;
            margin: 20px 0;
        }
        .subscribe:hover {
            background: #e65c00;
        }
        audio {
            width: 100%;
            margin-top: 10px;
        }
        footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <h1>🎙️ HackerCast</h1>
    <p>Your daily digest of the top stories from Hacker News, delivered as a podcast.</p>

    <h2>Subscribe</h2>
    <a href="/rss.xml" class="subscribe">📡 Subscribe via RSS</a>
    <p>Copy this URL into your podcast player: <code>{{ base_url }}/rss.xml</code></p>

    <h2>Recent Episodes</h2>
    {% if episodes %}
        {% for episode in episodes %}
        <div class="episode">
            <h3>{{ episode.title }}</h3>
            <p class="episode-meta">
                📅 {{ episode.pub_date.strftime('%B %d, %Y') }} |
                ⏱️ {{ episode.duration_formatted }} |
                💾 {{ "%.1f"|format(episode.file_size / 1024 / 1024) }} MB
            </p>
            <audio controls preload="none">
                <source src="{{ episode.audio_url }}" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
        </div>
        {% endfor %}
    {% else %}
        <p>No episodes available yet. Check back soon!</p>
    {% endif %}

    <footer>
        <p>Powered by HackerCast | Generated from <a href="https://news.ycombinator.com">Hacker News</a></p>
    </footer>
</body>
</html>
"""


@app.route('/')
def index():
    """Serve the index page with episode list."""
    try:
        # Generate RSS feed data to get episodes
        generator = RSSFeedGenerator(
            output_dir=str(OUTPUT_DIR),
            base_url=BASE_URL
        )
        episodes = generator.scan_episodes()

        # Limit to 10 most recent episodes for the index page
        episodes = episodes[:10]

        return render_template_string(
            INDEX_TEMPLATE,
            episodes=episodes,
            base_url=BASE_URL
        )
    except Exception as e:
        logger.error(f"Error generating index page: {e}")
        abort(500)


@app.route('/rss.xml')
def rss_feed():
    """Serve the RSS feed."""
    try:
        # Regenerate RSS feed on each request (or check if file is recent)
        if not RSS_FILE.exists() or should_regenerate_rss():
            logger.info("Regenerating RSS feed...")
            generator = RSSFeedGenerator(
                output_dir=str(OUTPUT_DIR),
                base_url=BASE_URL
            )
            generator.generate_and_save(str(RSS_FILE))

        return send_file(RSS_FILE, mimetype='application/rss+xml')
    except Exception as e:
        logger.error(f"Error serving RSS feed: {e}")
        abort(500)


@app.route('/audio/<date>/<filename>')
def serve_audio(date, filename):
    """Serve audio files."""
    try:
        audio_dir = OUTPUT_DIR / 'audio' / date

        # Security check: ensure date is in YYYYMMDD format
        if not (len(date) == 8 and date.isdigit()):
            abort(404)

        # Only allow specific filenames
        if not (filename.endswith('.mp3') and (filename == 'latest.mp3' or filename.replace('.mp3', '').isdigit())):
            abort(404)

        if not audio_dir.exists():
            abort(404)

        return send_from_directory(audio_dir, filename, mimetype='audio/mpeg')
    except Exception as e:
        logger.error(f"Error serving audio file {date}/{filename}: {e}")
        abort(404)


@app.route('/data/<date>/<filename>')
def serve_data(date, filename):
    """Serve data files (for debugging)."""
    try:
        data_dir = OUTPUT_DIR / 'data' / date

        # Security check: ensure date is in YYYYMMDD format
        if not (len(date) == 8 and date.isdigit()):
            abort(404)

        # Only allow specific file types
        allowed_extensions = {'.txt', '.json'}
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            abort(404)

        if not data_dir.exists():
            abort(404)

        # Determine mimetype
        mimetype = 'application/json' if filename.endswith('.json') else 'text/plain'

        return send_from_directory(data_dir, filename, mimetype=mimetype)
    except Exception as e:
        logger.error(f"Error serving data file {date}/{filename}: {e}")
        abort(404)


def should_regenerate_rss() -> bool:
    """Check if RSS feed should be regenerated."""
    # For now, always regenerate if file is older than 1 hour
    if not RSS_FILE.exists():
        return True

    import time
    age_seconds = time.time() - RSS_FILE.stat().st_mtime
    return age_seconds > 3600  # 1 hour


def main():
    """Main entry point for the server."""
    import argparse

    parser = argparse.ArgumentParser(description='HackerCast Podcast Server')
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to bind to (default: 5000)'
    )
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Output directory containing audio and data subdirectories'
    )
    parser.add_argument(
        '--base-url',
        help='Base URL for podcast (e.g., https://podcast.example.com)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Run in debug mode'
    )

    args = parser.parse_args()

    # Update global configuration
    global OUTPUT_DIR, BASE_URL
    OUTPUT_DIR = Path(args.output_dir)

    if args.base_url:
        BASE_URL = args.base_url
    else:
        # Construct base URL from host and port
        host = args.host if args.host != '0.0.0.0' else 'localhost'
        BASE_URL = f"http://{host}:{args.port}"

    logger.info(f"Starting HackerCast Podcast Server...")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Base URL: {BASE_URL}")
    logger.info(f"Server: {args.host}:{args.port}")

    # Generate initial RSS feed
    try:
        logger.info("Generating initial RSS feed...")
        generator = RSSFeedGenerator(
            output_dir=str(OUTPUT_DIR),
            base_url=BASE_URL
        )
        generator.generate_and_save(str(RSS_FILE))
    except Exception as e:
        logger.warning(f"Failed to generate initial RSS feed: {e}")

    # Start Flask server
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
