# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HackerCast is a Python application that creates daily audio podcasts from top Hacker News stories. The pipeline fetches stories, scrapes content, transforms it to podcast dialogue format using Gemini AI, and converts to multi-voice audio using Google Cloud Text-to-Speech.

## Quick Start

```bash
# Run complete pipeline (requires activation)
source venv/bin/activate
python main.py run --limit 20

# Or use the convenience script
./RUN 20
```

## Required Environment Variables

```bash
# Google Cloud TTS (required for audio generation)
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
export GOOGLE_CLOUD_PROJECT="hackercast-472403"

# Gemini AI (required for podcast script transformation)
export GEMINI_API_KEY="your_gemini_api_key"

# Podcast Publishing (optional)
export PODCAST_PUBLISHING_ENABLED=true
export TRANSISTOR_API_KEY="your_transistor_key"
export TRANSISTOR_SHOW_ID="your_show_id"
```

## Architecture

### Pipeline Flow
1. **hn_api.py** - Fetches story metadata from Hacker News API
2. **scraper.py** - Extracts article content from URLs (BeautifulSoup + Goose3)
3. **podcast_transformer.py** - Uses Gemini 2.0 Flash to transform raw content into podcast dialogue format (Chloe & David)
4. **tts_converter.py** - Multi-voice TTS using Google Cloud (Chloe: en-US-Studio-O, David: en-US-Journey-D)
5. **podcast_publisher.py** - Publishes to Transistor.fm (optional)

### Key Components
- **main.py** - CLI orchestrator using Click, coordinates full pipeline
- **config.py** - Configuration management with dataclasses and environment variables
- **interactive_selector.py** - Rich-based TUI for manual story curation
- **story_selection.py** - Data models for story selection state
- **rss_server.py** - Flask RSS feed server for podcast distribution

### Voice Configuration
Voice configs are in `tts_converter.py` (lines 81-100). To change voices:
- Chloe uses Studio-O (female, supports pitch)
- David uses Journey-D (deep male, no pitch support)
- Journey voices don't support pitch parameters - always set pitch=0.0

### Podcast Script Format
Scripts are dialogue-formatted with speaker prefixes:
```
Chloe: Welcome to HackerCast...
David: Thanks Chloe, today we have...
```

Prompt template is in `prompts/podcast-prompt-1.md`.

## Common Commands

### Running the Pipeline
```bash
# Simple automated run
python main.py run --limit 20

# Interactive story selection
python main.py run --interactive --limit 30

# Debug mode
python main.py --debug run --limit 10
```

### Interactive Selection
```bash
python main.py interactive --limit 50

# Commands in interactive mode:
# - s/select: toggle selection
# - a/all, n/none: select/deselect all
# - score:150: select stories with score ≥ 150
# - hours:12: select stories from last 12 hours
# - f/filter: search by text
# - u/urls: show only stories with URLs
# - c/confirm: proceed with selection
```

### Individual Components
```bash
# Fetch stories only
python main.py fetch --limit 10

# Scrape single URL
python main.py scrape "https://example.com/article"

# Convert text to speech
python main.py tts "Text to convert" output.mp3

# Publish episode
python main.py publish audio.mp3 --title "Episode Title"

# List Transistor shows
python main.py shows
```

### Testing
```bash
# Run simple tests
python test_simple.py

# Run comprehensive test suite
pytest

# Run specific test file
pytest tests/test_hn_api.py

# Run with coverage
pytest --cov=. --cov-report=html
```

## Output Structure

```
output/
├── rss.xml                                      # RSS feed for podcast
├── audio/
│   └── YYYYMMDD/
│       ├── latest.mp3                           # Latest episode for the day
│       └── HHMMSS.mp3                           # Archived episodes (timestamped)
└── data/
    └── YYYYMMDD/
        ├── latest.txt                           # Latest script
        ├── latest.json                          # Latest pipeline data
        ├── latest_podcast.txt                   # Latest podcast script
        └── HHMMSS.* (archived files)
```

When running multiple times per day, existing `latest.*` files are automatically archived with timestamps (e.g., `210717.mp3`).

## RSS Feed & Podcast Server

HackerCast automatically generates an RSS feed that's compatible with podcast players and can be served via a simple HTTP server.

### Generating RSS Feed

The RSS feed is automatically generated during the pipeline run. To manually generate:

```bash
# Generate RSS feed
python rss_generator.py --output-dir output --output-file output/rss.xml --base-url http://localhost:5000

# Custom configuration
python rss_generator.py \
  --output-dir output \
  --output-file output/rss.xml \
  --base-url https://podcast.example.com \
  --title "My HackerCast" \
  --author "My Name" \
  --email "my@email.com"
```

### Running Podcast Server

Start the Flask server to serve the RSS feed and audio files:

```bash
# Start server on default port (5000)
python podcast_server.py

# Custom port and base URL
python podcast_server.py --port 8080 --base-url https://podcast.example.com

# Specify output directory
python podcast_server.py --output-dir output --host 0.0.0.0 --port 8080
```

Server endpoints:
- `http://localhost:5000/` - Web interface showing episodes
- `http://localhost:5000/rss.xml` - RSS feed for podcast players
- `http://localhost:5000/audio/YYYYMMDD/latest.mp3` - Audio files
- `http://localhost:5000/data/YYYYMMDD/latest.json` - Episode metadata

### Subscribing to Podcast

1. Start the podcast server
2. Copy the RSS feed URL: `http://localhost:5000/rss.xml`
3. Add the URL to your podcast player (e.g., Apple Podcasts, Overcast, Pocket Casts)

For production deployment, set `HACKERCAST_BASE_URL` environment variable to your public URL:
```bash
export HACKERCAST_BASE_URL=https://podcast.example.com
python podcast_server.py --host 0.0.0.0 --port 80
```

## Development Notes

### Google Cloud Project
The codebase is hardcoded to use project `hackercast-472403` (see tts_converter.py:55). This cannot be overridden via environment variables.

### Scraping Limitations
- Some sites (OpenAI, WSJ, Cell.com) return 403/401 errors
- Goose3 has issues with date parsing ('str' object has no attribute 'isoformat')
- BeautifulSoup fallback is used when Goose3 fails

### TTS Chunking
Google Cloud TTS has a 5000 byte limit per request. Large texts are automatically:
1. Chunked by sentences (see `_chunk_text`)
2. Processed individually
3. Concatenated using ffmpeg (or binary concat if ffmpeg unavailable)

### Multi-Voice Dialogue
Dialogue format is auto-detected (>30% lines with "Chloe:" or "David:"). Each speaker gets separate voice configs and segments are concatenated.

### Podcast Transformation
Uses Gemini 2.0 Flash model with a detailed prompt to transform raw article content into engaging dialogue between two hosts. The transformation is enabled by default but can be disabled in TTSConverter initialization.

## Configuration Files

- `config.py` - Main configuration with dataclasses
- `.env` - Environment variables (not in repo)
- `pytest.ini` - Test configuration
- `prompts/podcast-prompt-1.md` - Gemini transformation prompt

## Git LFS

The `output/` directory uses Git LFS for large audio files. Ensure Git LFS is installed and initialized before committing MP3 files.
