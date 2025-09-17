# HackerCast Development Workflow

## Overview

This guide establishes development standards, local environment setup, testing procedures, and workflow practices for the HackerCast project. It ensures consistent development practices across the team and smooth transition from development to production.

## Local Development Environment

### 1. Environment Setup

**Prerequisites**:
```bash
# Python 3.11+ with virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

**Required Tools**:
```bash
# Development tools
pip install black isort flake8 mypy pytest pytest-cov pytest-asyncio

# Google Cloud tools
pip install google-cloud-functions-framework
pip install google-cloud-storage google-cloud-firestore google-cloud-pubsub
pip install google-cloud-texttospeech google-cloud-logging

# Web scraping and automation
pip install selenium beautifulsoup4 goose3 requests

# Local testing tools
pip install pytest-mock responses docker
```

### 2. Project Structure

```
HackerCast/
├── src/                          # Source code
│   ├── hn_fetcher/              # HN API Fetcher function
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── tests/
│   ├── content_processor/        # Content processing function
│   │   ├── main.py
│   │   ├── content_extractor.py
│   │   ├── requirements.txt
│   │   └── tests/
│   ├── script_generator/         # Script generation service
│   │   ├── main.py
│   │   ├── notebooklm_automator.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/
│   ├── audio_generator/          # Audio generation function
│   │   ├── main.py
│   │   ├── tts_client.py
│   │   ├── requirements.txt
│   │   └── tests/
│   ├── podcast_publisher/        # Podcast publishing function
│   │   ├── main.py
│   │   ├── rss_generator.py
│   │   ├── requirements.txt
│   │   └── tests/
│   └── shared/                   # Shared utilities
│       ├── __init__.py
│       ├── config.py
│       ├── logging_utils.py
│       ├── storage_utils.py
│       ├── firestore_utils.py
│       └── tests/
├── tests/                        # Integration tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_integration.py
│   └── test_e2e.py
├── infrastructure/               # Terraform configurations
├── scripts/                      # Build and deployment scripts
├── docs/                        # Documentation
├── .github/workflows/           # CI/CD pipelines
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── pyproject.toml              # Python project configuration
├── .env.example                # Environment variables template
└── README.md
```

### 3. Configuration Management

**Environment Variables** (`.env` file):
```bash
# Development environment
ENVIRONMENT=development
PROJECT_ID=hackercast-dev
REGION=us-central1

# Google Cloud settings
GOOGLE_APPLICATION_CREDENTIALS=./service-account-dev.json
FIRESTORE_EMULATOR_HOST=localhost:8080
PUBSUB_EMULATOR_HOST=localhost:8085

# External services
HN_API_BASE_URL=https://hacker-news.firebaseio.com/v0
NOTEBOOKLM_BASE_URL=https://notebooklm.google.com

# Local development overrides
ENABLE_BROWSER_AUTOMATION=false
USE_MOCK_TTS=true
STORAGE_BUCKET=hackercast-dev-audio
```

**Configuration Management** (`src/shared/config.py`):
```python
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Application configuration."""

    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    project_id: str = os.getenv("PROJECT_ID", "hackercast-dev")
    region: str = os.getenv("REGION", "us-central1")

    # Storage
    storage_bucket: str = os.getenv("STORAGE_BUCKET", "hackercast-dev-audio")

    # External APIs
    hn_api_base_url: str = os.getenv("HN_API_BASE_URL", "https://hacker-news.firebaseio.com/v0")
    notebooklm_base_url: str = os.getenv("NOTEBOOKLM_BASE_URL", "https://notebooklm.google.com")

    # Development settings
    enable_browser_automation: bool = os.getenv("ENABLE_BROWSER_AUTOMATION", "true").lower() == "true"
    use_mock_tts: bool = os.getenv("USE_MOCK_TTS", "false").lower() == "true"

    # Timeouts and limits
    content_extraction_timeout: int = int(os.getenv("CONTENT_EXTRACTION_TIMEOUT", "30"))
    script_generation_timeout: int = int(os.getenv("SCRIPT_GENERATION_TIMEOUT", "300"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment."""
        return cls()

# Global configuration instance
config = Config.load()
```

## Development Standards

### 1. Code Style and Quality

**Python Style Guide** (`pyproject.toml`):
```toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
line_length = 88

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[tool.pytest.ini_options]
testpaths = ["tests", "src"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --cov=src --cov-report=html --cov-report=term-missing"
asyncio_mode = "auto"
```

**Pre-commit Hooks** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-beautifulsoup4]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
```

### 2. Logging Standards

**Structured Logging** (`src/shared/logging_utils.py`):
```python
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for Cloud Logging compatibility."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "message": record.getMessage(),
            "component": getattr(record, "component", "unknown"),
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add execution context if available
        if hasattr(record, "execution_id"):
            log_entry["execution_id"] = record.execution_id

        if hasattr(record, "story_id"):
            log_entry["story_id"] = record.story_id

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry)

def setup_logging(component: str, level: str = "INFO") -> logging.Logger:
    """Set up structured logging for a component."""
    logger = logging.getLogger(component)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler with structured formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)

    # Add component name to all log records
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.component = component
        return record

    logging.setLogRecordFactory(record_factory)

    return logger

# Usage example
logger = setup_logging("content_processor")
logger.info("Processing started", extra={
    "extra_fields": {
        "story_id": "123",
        "url": "https://example.com"
    }
})
```

### 3. Error Handling Patterns

**Exception Hierarchy** (`src/shared/exceptions.py`):
```python
class HackerCastError(Exception):
    """Base exception for HackerCast errors."""

    def __init__(self, message: str, error_code: str = None, **context):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context

    def to_dict(self) -> dict:
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context
        }

class ContentExtractionError(HackerCastError):
    """Raised when content cannot be extracted from URL."""

class ScriptGenerationError(HackerCastError):
    """Raised when script generation fails."""

class AudioGenerationError(HackerCastError):
    """Raised when TTS conversion fails."""

class ValidationError(HackerCastError):
    """Raised when data validation fails."""

# Decorator for error handling
from functools import wraps
from typing import Callable, Type, Union

def handle_errors(
    exceptions: Union[Type[Exception], tuple] = Exception,
    logger: logging.Logger = None,
    reraise: bool = True
):
    """Decorator to handle and log exceptions."""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if logger:
                    logger.error(
                        f"Error in {func.__name__}: {str(e)}",
                        extra={"extra_fields": {"function": func.__name__, "args": str(args)}}
                    )

                if reraise:
                    raise
                return None

        return wrapper
    return decorator
```

## Testing Strategy

### 1. Unit Testing

**Test Structure** (`src/content_processor/tests/test_content_extractor.py`):
```python
import pytest
from unittest.mock import Mock, patch
import requests
from bs4 import BeautifulSoup

from content_processor.content_extractor import ContentExtractor, ContentResult
from shared.exceptions import ContentExtractionError

class TestContentExtractor:

    def setup_method(self):
        self.extractor = ContentExtractor()

    @pytest.mark.asyncio
    async def test_extract_success(self):
        """Test successful content extraction."""
        html_content = """
        <html>
            <head><title>Test Article</title></head>
            <body>
                <article>
                    <h1>Test Article</h1>
                    <p>This is test content.</p>
                </article>
            </body>
        </html>
        """

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = html_content.encode()
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = await self.extractor.extract("https://example.com/article")

            assert isinstance(result, ContentResult)
            assert result.title == "Test Article"
            assert "test content" in result.text.lower()
            assert result.word_count > 0
            assert result.is_valid

    @pytest.mark.asyncio
    async def test_extract_timeout(self):
        """Test extraction timeout handling."""
        with patch('requests.get', side_effect=requests.Timeout):
            with pytest.raises(ContentExtractionError) as exc_info:
                await self.extractor.extract("https://example.com/slow")

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.parametrize("status_code", [404, 500, 403])
    async def test_extract_http_errors(self, status_code):
        """Test handling of various HTTP errors."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = requests.HTTPError(f"{status_code} Error")
            mock_get.return_value = mock_response

            with pytest.raises(ContentExtractionError):
                await self.extractor.extract("https://example.com/error")
```

**Mock Services** (`tests/mocks.py`):
```python
from unittest.mock import Mock
from google.cloud import firestore, storage, pubsub_v1
import json

class MockFirestoreClient:
    """Mock Firestore client for testing."""

    def __init__(self):
        self._data = {}

    def collection(self, collection_name):
        return MockCollection(self, collection_name)

    def get_data(self, collection, document):
        return self._data.get(f"{collection}/{document}", {})

    def set_data(self, collection, document, data):
        self._data[f"{collection}/{document}"] = data

class MockCollection:
    def __init__(self, client, name):
        self.client = client
        self.name = name

    def document(self, doc_id):
        return MockDocument(self.client, self.name, doc_id)

class MockDocument:
    def __init__(self, client, collection, doc_id):
        self.client = client
        self.collection = collection
        self.doc_id = doc_id

    def get(self):
        data = self.client.get_data(self.collection, self.doc_id)
        mock_doc = Mock()
        mock_doc.exists = bool(data)
        mock_doc.to_dict.return_value = data
        return mock_doc

    def set(self, data):
        self.client.set_data(self.collection, self.doc_id, data)

class MockPubSubPublisher:
    """Mock Pub/Sub publisher for testing."""

    def __init__(self):
        self.published_messages = []

    def publish(self, topic, data, **attributes):
        self.published_messages.append({
            "topic": topic,
            "data": data,
            "attributes": attributes
        })
        # Return a future that resolves immediately
        future = Mock()
        future.result.return_value = "message-id"
        return future
```

### 2. Integration Testing

**Integration Test Setup** (`tests/conftest.py`):
```python
import pytest
import os
from google.cloud import firestore
from testcontainers.compose import DockerCompose

@pytest.fixture(scope="session")
def firebase_emulator():
    """Start Firebase emulator for integration tests."""
    compose = DockerCompose("tests", compose_file_name="docker-compose.test.yml")
    compose.start()

    # Set emulator environment variables
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
    os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"

    yield

    compose.stop()

@pytest.fixture
def firestore_client(firebase_emulator):
    """Provide Firestore client connected to emulator."""
    return firestore.Client(project="test-project")

@pytest.fixture
def clean_firestore(firestore_client):
    """Clean Firestore data between tests."""
    # Clean up before test
    collections = firestore_client.collections()
    for collection in collections:
        docs = collection.stream()
        for doc in docs:
            doc.reference.delete()

    yield firestore_client

    # Clean up after test
    collections = firestore_client.collections()
    for collection in collections:
        docs = collection.stream()
        for doc in docs:
            doc.reference.delete()
```

**Docker Compose for Testing** (`tests/docker-compose.test.yml`):
```yaml
version: '3.8'

services:
  firestore-emulator:
    image: mtlynch/firestore-emulator
    ports:
      - "8080:8080"
    environment:
      - FIRESTORE_PROJECT_ID=test-project

  pubsub-emulator:
    image: google/cloud-sdk:latest
    ports:
      - "8085:8085"
    command: >
      bash -c "gcloud beta emulators pubsub start --host-port=0.0.0.0:8085 --project=test-project"

  chrome:
    image: selenium/standalone-chrome:latest
    ports:
      - "4444:4444"
    shm_size: 2gb
    environment:
      - SE_NODE_MAX_SESSIONS=2
```

### 3. End-to-End Testing

**E2E Test Suite** (`tests/test_e2e.py`):
```python
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

from src.hn_fetcher.main import fetch_top_stories
from src.content_processor.main import process_content
from tests.mocks import MockFirestoreClient, MockPubSubPublisher

@pytest.mark.e2e
class TestFullPipeline:
    """End-to-end tests for the complete podcast generation pipeline."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.firestore_client = MockFirestoreClient()
        self.pubsub_publisher = MockPubSubPublisher()

    @pytest.mark.asyncio
    async def test_complete_pipeline(self):
        """Test the complete pipeline from HN API to published podcast."""

        # Mock external dependencies
        with patch('requests.get') as mock_get, \
             patch('google.cloud.firestore.Client', return_value=self.firestore_client), \
             patch('google.cloud.pubsub_v1.PublisherClient', return_value=self.pubsub_publisher):

            # Mock HN API response
            mock_get.return_value.json.return_value = [1, 2, 3]  # Story IDs

            # Step 1: Fetch top stories
            result = await fetch_top_stories({"limit": 3}, None)
            assert result["stories_queued"] == 3
            assert len(self.pubsub_publisher.published_messages) == 3

            # Step 2: Process content for each story
            for message in self.pubsub_publisher.published_messages:
                story_data = json.loads(message["data"])

                # Mock article content
                mock_get.return_value.content = b"<html><body><h1>Test Article</h1><p>Content</p></body></html>"

                result = await process_content({"data": message["data"]}, None)
                assert result["status"] == "success"

            # Verify Firestore state
            story_doc = self.firestore_client.get_data("stories", datetime.now().strftime("%Y-%m-%d"))
            assert len(story_doc["stories"]) == 3

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test pipeline behavior when components fail."""

        with patch('requests.get') as mock_get:
            # Simulate network error
            mock_get.side_effect = Exception("Network error")

            result = await process_content({
                "data": json.dumps({
                    "story_id": "123",
                    "url": "https://example.com/failing-url"
                })
            }, None)

            assert result["status"] == "error"
            assert "Network error" in result["error_message"]
```

## Local Development Workflow

### 1. Development Server

**Local Function Server** (`scripts/dev-server.py`):
```python
#!/usr/bin/env python3

import subprocess
import threading
import time
from pathlib import Path

def start_function_server(function_path: Path, port: int):
    """Start a local function server."""
    cmd = [
        "functions-framework",
        "--target", "main",
        "--source", str(function_path),
        "--port", str(port)
    ]

    subprocess.run(cmd, cwd=function_path)

def start_emulators():
    """Start local emulators."""
    # Start Firestore emulator
    firestore_cmd = [
        "gcloud", "emulators", "firestore", "start",
        "--host-port", "localhost:8080"
    ]

    pubsub_cmd = [
        "gcloud", "emulators", "pubsub", "start",
        "--host-port", "localhost:8085"
    ]

    # Start in background
    threading.Thread(target=lambda: subprocess.run(firestore_cmd), daemon=True).start()
    threading.Thread(target=lambda: subprocess.run(pubsub_cmd), daemon=True).start()

    time.sleep(5)  # Wait for emulators to start

if __name__ == "__main__":
    print("Starting development environment...")

    # Start emulators
    start_emulators()

    # Start function servers
    functions = [
        ("src/hn_fetcher", 8001),
        ("src/content_processor", 8002),
        ("src/audio_generator", 8003),
        ("src/podcast_publisher", 8004)
    ]

    threads = []
    for func_path, port in functions:
        thread = threading.Thread(
            target=start_function_server,
            args=(Path(func_path), port),
            daemon=True
        )
        thread.start()
        threads.append(thread)
        print(f"Started {func_path} on port {port}")

    print("Development environment ready!")
    print("Press Ctrl+C to stop")

    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("Stopping development environment...")
```

### 2. Testing Commands

**Make Tasks** (`Makefile`):
```makefile
.PHONY: install test lint format clean dev-setup

# Installation
install:
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

# Testing
test:
	pytest tests/ -v

test-unit:
	pytest src/ -v -k "not integration and not e2e"

test-integration:
	pytest tests/ -v -k "integration" --tb=short

test-e2e:
	pytest tests/ -v -k "e2e" --tb=short

test-coverage:
	pytest --cov=src --cov-report=html --cov-report=term-missing

# Code quality
lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

format-check:
	black --check src/ tests/
	isort --check-only src/ tests/

# Development
dev-setup:
	python scripts/dev-server.py

dev-test:
	python scripts/test-local-pipeline.py

# Build
build:
	./scripts/package-functions.sh

# Deployment
deploy-dev:
	./scripts/deploy.sh dev

deploy-prod:
	./scripts/deploy.sh prod

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ build/ dist/
```

### 3. Git Workflow

**Branch Strategy**:
- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Feature development branches
- `hotfix/*`: Critical production fixes

**Commit Message Format**:
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Pull Request Template** (`.github/pull_request_template.md`):
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] This change requires a documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Manual testing completed

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
```

## Documentation Standards

### 1. Code Documentation

**Docstring Format** (Google Style):
```python
def extract_content(url: str, timeout: int = 30) -> ContentResult:
    """Extract text content from a web page.

    Uses multiple extraction strategies to handle different website layouts
    and provides fallback mechanisms for robust content extraction.

    Args:
        url: The URL to extract content from
        timeout: Request timeout in seconds

    Returns:
        ContentResult containing extracted text and metadata

    Raises:
        ContentExtractionError: When content cannot be extracted
        ValidationError: When extracted content doesn't meet quality thresholds

    Example:
        >>> result = extract_content("https://example.com/article")
        >>> print(f"Extracted {result.word_count} words")
        Extracted 1250 words
    """
```

### 2. API Documentation

**OpenAPI Specification** for HTTP endpoints:
```yaml
openapi: 3.0.0
info:
  title: HackerCast API
  version: 1.0.0
  description: Internal APIs for HackerCast components

paths:
  /fetch-top-stories:
    post:
      summary: Fetch top stories from Hacker News
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                limit:
                  type: integer
                  default: 20
      responses:
        '200':
          description: Stories queued for processing
          content:
            application/json:
              schema:
                type: object
                properties:
                  execution_id:
                    type: string
                  stories_queued:
                    type: integer
```

This development workflow ensures consistent code quality, comprehensive testing, and smooth collaboration across the HackerCast development team.