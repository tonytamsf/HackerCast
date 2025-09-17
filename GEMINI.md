# Project: HackerCast

## Project Overview

HackerCast is a Python-based project designed to create a daily audio podcast summarizing the top 20 stories from Hacker News. The goal is to provide a convenient, audio-first format for tech professionals to stay informed.

The architecture is serverless, intended to run on Google Cloud Platform (or a similar cloud provider). The planned workflow is as follows:

1.  **Data Ingestion:** A daily scheduled function will fetch the top 20 stories from the Hacker News API and scrape the content of each article.
2.  **Content Generation:** The scraped text will be fed into Google's NotebookLM to generate a conversational podcast script for each article. This will be automated using a headless browser tool like Puppeteer or Selenium, as NotebookLM does not yet have a public API.
3.  **Audio Production:** The generated scripts will be converted to high-quality MP3 audio files using a Text-to-Speech (TTS) service (e.g., Google WaveNet).
4.  **Publishing:** The audio files will be hosted on a public cloud storage service (e.g., Google Cloud Storage), and a standard RSS 2.0 podcast feed will be generated and updated daily.

## Building and Running

This project is in the initial implementation phase, following the plan outlined in the [Product Requirements Document](docs/prd.md). There are no single commands to build or run the entire application yet.

The development is planned in phases:

1.  **Phase 1: Proof of Concept (Manual):** This phase focuses on manually executing each step of the pipeline to validate the technology choices. It involves:
    *   Manually scraping an article with a Python script.
    *   Manually generating a script using the NotebookLM web interface.
    *   Manually converting the script to audio with a TTS service.
    *   Manually creating and testing an RSS feed.

2.  **Phase 2: Automation & MVP Build:** This phase involves writing the core Python application using Google Cloud Functions for orchestration.

**TODO:** Add specific commands for building, local testing, and deploying the cloud functions as they are developed.

## Development Conventions

*   **Language:** Python
*   **Platform:** Serverless functions (preferably Google Cloud Functions)
*   **Key Libraries/APIs:**
    *   `requests` and `BeautifulSoup` for web scraping.
    *   Puppeteer or Selenium for browser automation to interact with NotebookLM.
    *   A Text-to-Speech API (e.g., Google Text-to-Speech).
    *   The official Hacker News API.
*   **Code Style:** Follow standard Python best practices (PEP 8).
*   **Configuration:** Sensitive information like API keys should be managed through environment variables or a secret management service, not hardcoded in the source.
