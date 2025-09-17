"""Mock responses and test data fixtures."""

import json
from typing import Dict, List, Any


class HackerNewsFixtures:
    """Fixtures for Hacker News API responses."""

    TOP_STORIES_RESPONSE = [
        40001,
        40002,
        40003,
        40004,
        40005,
        40006,
        40007,
        40008,
        40009,
        40010,
        40011,
        40012,
        40013,
        40014,
        40015,
        40016,
        40017,
        40018,
        40019,
        40020,
    ]

    STORY_ITEMS = {
        40001: {
            "id": 40001,
            "type": "story",
            "by": "techpioneer",
            "time": 1694890800,
            "title": "Revolutionary AI Framework Achieves Human-Level Performance",
            "url": "https://example.com/ai-framework-breakthrough",
            "score": 1250,
            "descendants": 234,
        },
        40002: {
            "id": 40002,
            "type": "story",
            "by": "langdev",
            "time": 1694887200,
            "title": "New Programming Language Promises 10x Performance Gains",
            "url": "https://example.com/new-programming-language",
            "score": 980,
            "descendants": 156,
        },
        40003: {
            "id": 40003,
            "type": "story",
            "by": "quantumresearcher",
            "time": 1694883600,
            "title": "Quantum Computing Breakthrough: 1000-Qubit Processor Unveiled",
            "url": "https://example.com/quantum-breakthrough",
            "score": 1500,
            "descendants": 312,
        },
        40004: {
            "id": 40004,
            "type": "story",
            "by": "securityexpert",
            "time": 1694880000,
            "title": "Open Source Security Tool Prevents 99% of Cyber Attacks",
            "url": "https://example.com/security-tool",
            "score": 750,
            "descendants": 89,
        },
        40005: {
            "id": 40005,
            "type": "story",
            "by": "cloudstartup",
            "time": 1694876400,
            "title": "Startup Disrupts Cloud Computing with Edge-First Architecture",
            "url": "https://example.com/edge-computing",
            "score": 650,
            "descendants": 67,
        },
    }

    @classmethod
    def get_story_item(cls, story_id: int) -> Dict[str, Any]:
        """Get story item by ID."""
        return cls.STORY_ITEMS.get(story_id, {})


class ScrapingFixtures:
    """Fixtures for web scraping responses."""

    ARTICLE_CONTENT = {
        "https://example.com/ai-framework-breakthrough": """
        <html>
        <head><title>Revolutionary AI Framework Achieves Human-Level Performance</title></head>
        <body>
            <article>
                <h1>Revolutionary AI Framework Achieves Human-Level Performance</h1>
                <div class="author">By Tech Reporter</div>
                <div class="content">
                    <p>Researchers at TechCorp have unveiled a groundbreaking artificial intelligence
                    framework that has achieved human-level performance across multiple cognitive tasks.</p>

                    <p>The new system, called CogniAI, represents a significant leap forward in machine
                    learning capabilities. In benchmark tests, CogniAI scored within 2% of human
                    performance on complex reasoning tasks.</p>

                    <p>"This represents a paradigm shift in how we approach artificial intelligence,"
                    said Dr. Sarah Chen, lead researcher on the project.</p>
                </div>
            </article>
        </body>
        </html>
        """,
        "https://example.com/new-programming-language": """
        <html>
        <head><title>New Programming Language Promises 10x Performance Gains</title></head>
        <body>
            <article>
                <h1>New Programming Language Promises 10x Performance Gains</h1>
                <div class="author">By Language Design Team</div>
                <div class="content">
                    <p>A team of compiler engineers has introduced Velocity, a new systems programming
                    language that claims to deliver performance improvements of up to 10x over
                    traditional languages.</p>

                    <p>Velocity combines the performance characteristics of C++ with the safety
                    guarantees of Rust, using innovative static analysis techniques.</p>

                    <p>Early benchmarks show impressive results across various computational tasks.
                    Sorting algorithms implemented in Velocity run 8.5x faster than equivalent
                    Python code.</p>
                </div>
            </article>
        </body>
        </html>
        """,
    }

    @classmethod
    def get_article_html(cls, url: str) -> str:
        """Get article HTML by URL."""
        return cls.ARTICLE_CONTENT.get(
            url, "<html><body><p>Default test content</p></body></html>"
        )


class ErrorFixtures:
    """Fixtures for error scenarios."""

    NETWORK_ERRORS = [
        "Connection timeout",
        "Name resolution failed",
        "Connection refused",
        "SSL certificate verification failed",
    ]

    HTTP_ERRORS = {
        404: "Not Found",
        500: "Internal Server Error",
        503: "Service Unavailable",
        429: "Too Many Requests",
    }

    API_ERRORS = {
        "rate_limit": {"error": "Rate limit exceeded", "retry_after": 3600},
        "invalid_id": {"error": "Invalid item ID"},
        "service_down": {"error": "Service temporarily unavailable"},
    }


class TestDataFixtures:
    """Fixtures for test data validation."""

    VALID_PIPELINE_OUTPUT = {
        "timestamp": "20230916_120000",
        "run_date": "2023-09-16T12:00:00",
        "config": {
            "environment": "test",
            "max_stories": 5,
            "tts_voice": "en-US-Standard-A",
        },
        "stories": [
            {
                "id": 40001,
                "title": "Test Story 1",
                "by": "testuser",
                "score": 100,
                "url": "https://example.com/story1",
            }
        ],
        "scraped_content": [
            {
                "url": "https://example.com/story1",
                "title": "Test Story 1",
                "content": "Test content",
                "word_count": 100,
                "success": True,
            }
        ],
        "audio_files": ["output/audio/test_audio.mp3"],
        "stats": {
            "stories_fetched": 1,
            "articles_scraped": 1,
            "total_words": 100,
            "audio_files_generated": 1,
        },
    }

    VALID_PODCAST_SCRIPT = """
    Welcome to HackerCast, your daily digest of the top stories from Hacker News.
    Today is September 16, 2023, and we have 3 fascinating stories to share with you.

    Story 1: Revolutionary AI Framework Achieves Human-Level Performance
    Researchers at TechCorp have unveiled a groundbreaking artificial intelligence
    framework that has achieved human-level performance across multiple cognitive tasks.

    Next up...

    Story 2: New Programming Language Promises 10x Performance Gains
    A team of compiler engineers has introduced Velocity, a new systems programming
    language that claims to deliver performance improvements of up to 10x.

    Next up...

    Story 3: Quantum Computing Breakthrough: 1000-Qubit Processor Unveiled
    QuantumTech Industries has achieved a major milestone in quantum computing with
    the unveiling of their 1000-qubit quantum processor.

    That wraps up today's HackerCast. Thank you for listening, and we'll see you
    tomorrow with more stories from the world of technology.
    """

    PERFORMANCE_BENCHMARKS = {
        "fetch_stories": {
            "max_duration_seconds": 30,
            "max_api_calls": 25,
            "min_success_rate": 0.95,
        },
        "scrape_articles": {
            "max_duration_seconds": 60,
            "max_requests_per_second": 5,
            "min_success_rate": 0.80,
        },
        "generate_script": {
            "max_duration_seconds": 10,
            "min_word_count": 200,
            "max_word_count": 5000,
        },
        "full_pipeline": {
            "max_duration_seconds": 120,
            "min_output_files": 2,  # script + data
            "max_memory_mb": 500,
        },
    }


def load_test_config() -> Dict[str, Any]:
    """Load test configuration."""
    return {
        "environment": "test",
        "debug": True,
        "hackernews": {
            "api_base_url": "https://hacker-news.firebaseio.com/v0",
            "max_stories": 5,
            "request_timeout": 10,
        },
        "scraping": {"request_timeout": 10, "max_retries": 2, "retry_delay": 0.5},
        "tts": {
            "enabled": False,
            "language_code": "en-US",
            "voice_name": "en-US-Standard-A",
        },
        "output": {"base_directory": "/tmp/hackercast_test"},
    }
