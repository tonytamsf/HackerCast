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
├── audio/
│   └── hackercast_YYYYMMDD_HHMMSS.mp3  # Final podcast audio
└── data/
    ├── script_YYYYMMDD_HHMMSS_Topic.txt  # Generated podcast script
    └── pipeline_data_YYYYMMDD_HHMMSS.json  # Pipeline metadata
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
