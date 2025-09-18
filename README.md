# HackerCast

A Python-based serverless application that creates daily audio podcasts from the top Hacker News stories.

## Features

- **Automated Story Fetching**: Retrieves top stories from Hacker News API
- **Intelligent Content Scraping**: Extracts article content from URLs
- **Interactive Story Selection**: Manually choose which stories to include in your podcast
- **Text-to-Speech Conversion**: Generates natural-sounding audio using Google Cloud TTS
- **Rich CLI Interface**: Beautiful terminal interface with progress tracking

## Quick Start

### Basic Usage

```bash
# Run complete pipeline automatically
python main.py run

# Interactive story selection
python main.py run --interactive

# Fetch and select stories manually
python main.py select --limit 10
```

### Interactive Selection

The interactive selection feature allows you to manually choose which stories to process:

```bash
# Launch interactive mode
python main.py interactive --limit 20

# Or add --interactive to the run command
python main.py run --interactive --limit 15
```

**Interactive Commands:**
- `s` - Toggle story selection
- `a` - Select all stories
- `n` - Deselect all stories
- `f` - Filter by text
- `u` - Show only stories with URLs
- `score:100` - Select stories with 100+ points
- `hours:12` - Select stories from last 12 hours
- `p` - Preview story details
- `h` - Show help
- `c` - Confirm and proceed

See [docs/interactive-selection-guide.md](docs/interactive-selection-guide.md) for detailed usage instructions.

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up Google Cloud credentials for TTS (see CLAUDE.md)
4. Configure environment variables (see .env.example)

## Usage Examples

```bash
# Basic podcast generation
python main.py run --limit 10

# Interactive selection with debugging
python main.py --debug interactive --limit 30

# Just fetch and display stories
python main.py fetch --limit 5

# Scrape a single article
python main.py scrape "https://example.com/article"

# Convert text to speech
python main.py tts "Hello world" output.mp3
```

## Documentation

- [Interactive Selection Guide](docs/interactive-selection-guide.md) - Comprehensive guide for story selection
- [CLAUDE.md](CLAUDE.md) - Development setup and conventions
- [Configuration](config.py) - Available configuration options

## Architecture

- `hn_api.py` - Hacker News API client
- `scraper.py` - Web scraping and content extraction
- `tts_converter.py` - Google Cloud Text-to-Speech integration
- `story_selection.py` - Interactive selection data models
- `interactive_selector.py` - Rich-based terminal UI
- `main.py` - CLI interface and pipeline orchestration

## Testing

```bash
# Run simple functionality tests
python test_simple.py

# Run comprehensive tests (requires pytest)
pytest test_interactive_selection.py
```
# Test update
