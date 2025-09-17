# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HackerCast is a Python-based serverless application that creates daily audio podcasts from the top 20 Hacker News stories. The project follows a three-phase development approach from PoC to full automation.

## Architecture

The application consists of three main Python modules in the root directory:

- `hn_api.py` - Fetches top story IDs from Hacker News API
- `scraper.py` - Scrapes article content from URLs using BeautifulSoup
- `tts_converter.py` - Converts text to MP3 using Google Cloud Text-to-Speech

The planned serverless architecture will use Google Cloud Functions for orchestration, with browser automation (Puppeteer/Selenium) to interact with NotebookLM for script generation, since NotebookLM lacks a public API.

## Development Environment

### Virtual Environment
The project uses a Python virtual environment located in `venv/`. To activate:
```bash
source venv/bin/activate  # On macOS/Linux
```

### Dependencies
Install required packages:
```bash
pip install -r requirements.txt
```

Key dependencies:
- `requests` - HTTP requests for APIs and web scraping
- `beautifulsoup4` - HTML parsing
- `goose3` - Article extraction (alternative to BeautifulSoup)
- `selenium` - Browser automation for NotebookLM interaction
- `google-cloud-texttospeech` - Google Cloud TTS API

### Authentication
Google Cloud Text-to-Speech requires authentication. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your service account key file.

## Running Individual Components

### Fetch Top Stories
```bash
python hn_api.py [limit]
# Example: python hn_api.py 5
```

### Scrape Article Content
```bash
python scraper.py <URL>
# Example: python scraper.py "https://example.com/article"
```

### Convert Text to Speech
```bash
python tts_converter.py "<text>" <output_file.mp3>
# Example: python tts_converter.py "Hello world" output.mp3
```

## Current Development Phase

The project is in Phase 1 (Proof of Concept), focusing on manual execution of each pipeline step to validate technology choices. No automated build, test, or deployment processes are currently implemented.

## File Structure

- `docs/prd.md` - Detailed Product Requirements Document
- `GEMINI.md` - Project overview and development conventions
- `requirements.txt` - Python dependencies
- `venv/` - Virtual environment (excluded from version control)

## Development Notes

- Follow PEP 8 Python style conventions
- Sensitive information (API keys) should use environment variables, not hardcoded values
- The project targets serverless deployment on Google Cloud Platform
- Browser automation is used as a workaround for NotebookLM's lack of public API