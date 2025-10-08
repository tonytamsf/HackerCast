# Project: HackerCast

## Project Overview

HackerCast is a Python-based serverless application that creates daily audio podcasts from the top Hacker News stories. It features automated story fetching, intelligent content scraping, interactive story selection, and text-to-speech conversion using Google Cloud TTS. The application is designed with a rich CLI interface for ease of use.

**Main Technologies:**

*   **Backend:** Python
*   **CLI:** `click`, `rich`
*   **Web Scraping:** `requests`, `beautifulsoup4`, `goose3`
*   **API:** Hacker News API
*   **Text-to-Speech:** Google Cloud Text-to-Speech
*   **Podcast Publishing:** Transistor.fm API
*   **Configuration:** `dataclasses`, `python-dotenv`
*   **Testing:** `pytest`

**Architecture:**

The application is orchestrated by the `HackerCastPipeline` class in `main.py`. It uses a modular architecture with clear separation of concerns:

*   `hn_api.py`: Fetches top stories from the Hacker News API.
*   `scraper.py`: Scrapes article content from URLs using `goose3` and `BeautifulSoup`.
*   `tts_converter.py`: Converts text to speech using the Google Cloud Text-to-Speech API.
*   `podcast_publisher.py`: Publishes the generated podcast to Transistor.fm.
*   `interactive_selector.py`: Provides an interactive terminal UI for story selection using `rich`.
*   `story_selection.py`: Defines the data models for the interactive selection feature.
*   `config.py`: Manages application configuration using `dataclasses` and environment variables.
*   `main.py`: Provides the main CLI interface using `click` and orchestrates the podcast generation pipeline.

## Building and Running

**Installation:**

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set up Google Cloud credentials for TTS.
4.  Configure environment variables (see `.env.example`).

**Running the application:**

*   **Run the complete pipeline automatically:**
    ```bash
    python main.py run
    ```
*   **Run with interactive story selection:**
    ```bash
    python main.py run --interactive
    ```
*   **Fetch and select stories manually:**
    ```bash
    python main.py select --limit 10
    ```

**Testing:**

*   **Run simple functionality tests:**
    ```bash
    python test_simple.py
    ```
*   **Run comprehensive tests with pytest:**
    ```bash
    pytest
    ```

## Development Conventions

*   **Configuration:** The project uses a `ConfigManager` class to manage configuration from environment variables and (optionally) a configuration file. Configuration is defined using `dataclasses` in `config.py`.
*   **Coding Style:** The code follows PEP 8 and uses `black` for formatting and `flake8` for linting.
*   **Typing:** The project uses type hints and `mypy` for static type checking.
*   **Testing:** The project uses `pytest` for testing. Tests are located in the `tests/` directory.
*   **CLI:** The project uses the `click` library to create a command-line interface.
*   **UI:** The project uses the `rich` library to create a rich terminal UI for the interactive story selector.
