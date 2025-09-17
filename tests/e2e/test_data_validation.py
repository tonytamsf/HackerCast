"""End-to-end tests for data validation and content quality."""

import json
import time
from pathlib import Path
from typing import List, Dict, Any
import pytest

from hn_api import HackerNewsStory
from scraper import ScrapedContent
from main import HackerCastPipeline
from tests.utils.test_helpers import (
    DataValidator, FileValidator, PerformanceMonitor, MetricsCollector
)
from tests.utils.mock_services import E2ETestContext
from tests.utils.test_helpers import create_mock_hn_stories, create_mock_scraped_content


class TestDataValidation:
    """Test data validation and content quality across the pipeline."""

    def setup_method(self):
        """Setup for each test method."""
        self.metrics = MetricsCollector()

    def test_hn_stories_data_structure(self):
        """Test HackerNews stories data structure validation."""
        # Create test stories with various edge cases
        stories = [
            HackerNewsStory(
                id=1001,
                title="Valid Story Title",
                by="testuser",
                score=100,
                time=int(time.time()),
                url="https://example.com/story1",
                type="story"
            ),
            HackerNewsStory(
                id=1002,
                title="Another Valid Story",
                by="another_user",
                score=0,  # Edge case: zero score
                time=int(time.time()) - 3600,
                url="https://example.com/story2",
                type="story"
            )
        ]

        # Validate stories
        is_valid, error = DataValidator.validate_hn_stories(stories)
        assert is_valid, f"Valid stories failed validation: {error}"

        # Test with invalid stories
        invalid_stories = [
            HackerNewsStory(
                id=None,  # Invalid: missing ID
                title="Invalid Story",
                by="testuser",
                score=100,
                time=int(time.time()),
                url="https://example.com/invalid",
                type="story"
            )
        ]

        is_valid, error = DataValidator.validate_hn_stories(invalid_stories)
        assert not is_valid, "Invalid stories should fail validation"
        assert "missing ID" in error

    def test_scraped_content_quality_validation(self):
        """Test scraped content quality validation."""
        # Create valid content
        valid_content = [
            ScrapedContent(
                url="https://example.com/article1",
                title="High Quality Article",
                content="This is a substantial article with plenty of content. " * 20,
                author="Quality Author",
                publish_date=None,
                word_count=300,
                scraping_method="test",
                success=True
            )
        ]

        is_valid, error = DataValidator.validate_scraped_content(valid_content)
        assert is_valid, f"Valid content failed validation: {error}"

        # Test with poor quality content
        poor_content = [
            ScrapedContent(
                url="https://example.com/poor",
                title="Poor Article",
                content="Too short.",  # Too little content
                author="Poor Author",
                publish_date=None,
                word_count=2,
                scraping_method="test",
                success=True
            )
        ]

        is_valid, error = DataValidator.validate_scraped_content(poor_content)
        assert not is_valid, "Poor content should fail validation"

    def test_podcast_script_quality_validation(self):
        """Test podcast script quality validation."""
        # Valid script
        valid_script = """
        Welcome to HackerCast, your daily digest of the top stories from Hacker News.
        Today is September 16, 2023, and we have 3 fascinating stories to share with you.

        Story 1: Revolutionary AI Framework
        This is a comprehensive story about artificial intelligence developments.

        Next up...

        Story 2: Programming Language Innovation
        Another detailed story about programming language advances.

        That wraps up today's HackerCast. Thank you for listening.
        """

        is_valid, error = DataValidator.validate_podcast_script(valid_script)
        assert is_valid, f"Valid script failed validation: {error}"

        # Invalid scripts
        invalid_scripts = [
            "",  # Empty script
            "Short script",  # Too short
            "This is a long script without proper podcast structure and formatting.",  # Missing structure
        ]

        for script in invalid_scripts:
            is_valid, error = DataValidator.validate_podcast_script(script)
            assert not is_valid, f"Invalid script should fail validation: {script[:50]}"

    def test_file_output_validation(self):
        """Test file output validation across different formats."""
        with E2ETestContext() as ctx:
            # Create test files
            json_file = ctx.output_dir / "test_data.json"
            text_file = ctx.output_dir / "test_script.txt"
            audio_file = ctx.output_dir / "test_audio.mp3"

            # Create valid JSON file
            test_data = {
                "timestamp": "20230916_120000",
                "stories": [{"id": 1, "title": "Test"}],
                "stats": {"count": 1}
            }
            with open(json_file, 'w') as f:
                json.dump(test_data, f)

            # Validate JSON file
            is_valid, error = FileValidator.validate_json_file(
                json_file,
                required_keys=["timestamp", "stories", "stats"]
            )
            assert is_valid, f"JSON validation failed: {error}"

            # Create text file
            with open(text_file, 'w') as f:
                f.write("This is a test script with sufficient content. " * 20)

            # Validate text file
            is_valid, error = FileValidator.validate_text_file(text_file, min_length=100)
            assert is_valid, f"Text validation failed: {error}"

            # Create mock audio file
            with open(audio_file, 'wb') as f:
                f.write(b'ID3' + b'\x00' * 1000)  # Minimal MP3-like structure

            # Validate audio file
            is_valid, error = FileValidator.validate_audio_file(audio_file, min_size_bytes=500)
            assert is_valid, f"Audio validation failed: {error}"

    def test_content_completeness_validation(self):
        """Test validation of content completeness across pipeline stages."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Run pipeline stages individually for validation
            stories = pipeline.fetch_top_stories(3)

            # Validate stories completeness
            assert len(stories) == 3, "Wrong number of stories fetched"

            for story in stories:
                assert story.id is not None, "Story missing ID"
                assert story.title, "Story missing title"
                assert story.by, "Story missing author"
                assert story.score is not None, "Story missing score"

            # Scrape content
            content = pipeline.scrape_articles(stories)

            # Validate content completeness
            assert len(content) >= 1, "No content scraped"

            for article in content:
                assert article.title, "Article missing title"
                assert article.content, "Article missing content"
                assert len(article.content) > 50, "Article content too short"
                assert article.word_count > 0, "Article missing word count"

            # Generate script
            script = pipeline.generate_podcast_script(content)

            # Validate script completeness
            assert script, "No script generated"
            assert len(script) > 500, "Script too short"
            assert "hackercast" in script.lower(), "Script missing branding"
            assert "story" in script.lower(), "Script missing story references"

    def test_data_consistency_validation(self):
        """Test data consistency across pipeline stages."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Run full pipeline
            result = pipeline.run_full_pipeline(limit=3)
            assert result["success"], "Pipeline should succeed"

            # Load saved data
            data_file = Path(result["data_file"])
            with open(data_file, 'r') as f:
                saved_data = json.load(f)

            # Validate data consistency
            stories_data = saved_data["stories"]
            scraped_data = saved_data["scraped_content"]
            stats_data = saved_data["stats"]

            # Story count consistency
            assert len(stories_data) == stats_data["stories_fetched"], "Story count mismatch"
            assert len(scraped_data) == stats_data["articles_scraped"], "Content count mismatch"

            # Word count consistency
            total_words = sum(content["word_count"] for content in scraped_data)
            assert total_words == stats_data["total_words"], "Word count mismatch"

            # URL consistency between stories and scraped content
            story_urls = {story["url"] for story in stories_data if story.get("url")}
            scraped_urls = {content["url"] for content in scraped_data}

            # Scraped URLs should be subset of story URLs
            assert scraped_urls.issubset(story_urls), "URL mismatch between stories and content"

    def test_edge_case_data_handling(self):
        """Test handling of edge cases in data processing."""
        # Test with stories that have no URLs
        stories_no_urls = [
            HackerNewsStory(
                id=2001,
                title="Ask HN: Question without URL",
                by="questioner",
                score=50,
                time=int(time.time()),
                url=None,  # No URL
                type="story"
            )
        ]

        is_valid, error = DataValidator.validate_hn_stories(stories_no_urls)
        assert is_valid, "Stories without URLs should be valid"

        # Test with very short titles
        stories_short_titles = [
            HackerNewsStory(
                id=2002,
                title="Hi",  # Very short title
                by="brief_user",
                score=1,
                time=int(time.time()),
                url="https://example.com/brief",
                type="story"
            )
        ]

        is_valid, error = DataValidator.validate_hn_stories(stories_short_titles)
        assert is_valid, "Stories with short titles should be valid"

        # Test with special characters in content
        special_content = [
            ScrapedContent(
                url="https://example.com/special",
                title="Special Characters: àáâãäå æç èéêë",
                content="Content with special characters: àáâãäå æç èéêë ìíîï ñ òóôõö ùúûü ý " * 10,
                author="Special Author",
                publish_date=None,
                word_count=100,
                scraping_method="test",
                success=True
            )
        ]

        is_valid, error = DataValidator.validate_scraped_content(special_content)
        assert is_valid, f"Content with special characters should be valid: {error}"

    def test_large_dataset_validation(self):
        """Test validation with larger datasets."""
        # Create large dataset
        large_stories = create_mock_hn_stories(50)
        large_content = create_mock_scraped_content(30)

        # Validate large story dataset
        is_valid, error = DataValidator.validate_hn_stories(large_stories)
        assert is_valid, f"Large story dataset failed validation: {error}"

        # Validate large content dataset
        is_valid, error = DataValidator.validate_scraped_content(large_content)
        assert is_valid, f"Large content dataset failed validation: {error}"

        # Check memory efficiency
        import sys
        stories_size = sys.getsizeof(large_stories)
        content_size = sys.getsizeof(large_content)

        # Basic size checks (not too strict, just ensuring reasonable memory usage)
        assert stories_size < 1024 * 1024, "Stories dataset using too much memory"  # < 1MB
        assert content_size < 5 * 1024 * 1024, "Content dataset using too much memory"  # < 5MB

    def test_corrupted_data_handling(self):
        """Test handling of corrupted or malformed data."""
        with E2ETestContext() as ctx:
            # Create corrupted JSON file
            corrupted_file = ctx.output_dir / "corrupted.json"
            with open(corrupted_file, 'w') as f:
                f.write('{"invalid": json, content}')  # Invalid JSON

            # Validate corrupted file
            is_valid, error = FileValidator.validate_json_file(corrupted_file)
            assert not is_valid, "Corrupted JSON should fail validation"
            assert "Invalid JSON" in error

            # Create file with missing required keys
            incomplete_file = ctx.output_dir / "incomplete.json"
            with open(incomplete_file, 'w') as f:
                json.dump({"partial": "data"}, f)

            # Validate incomplete file
            is_valid, error = FileValidator.validate_json_file(
                incomplete_file,
                required_keys=["timestamp", "stories"]
            )
            assert not is_valid, "Incomplete JSON should fail validation"
            assert "Missing required keys" in error

    def test_unicode_and_encoding_validation(self):
        """Test handling of Unicode content and encoding issues."""
        # Test with various Unicode content
        unicode_content = [
            ScrapedContent(
                url="https://example.com/unicode",
                title="Unicode Test: 你好世界 こんにちは Здравствуй мир",
                content="Content with Unicode: 你好世界 こんにちは Здравствуй мир 🚀 🌟 ⭐ " * 10,
                author="Unicode Author 🌍",
                publish_date=None,
                word_count=150,
                scraping_method="test",
                success=True
            )
        ]

        is_valid, error = DataValidator.validate_scraped_content(unicode_content)
        assert is_valid, f"Unicode content should be valid: {error}"

        # Test script generation with Unicode
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))
            script = pipeline.generate_podcast_script(unicode_content)

            is_valid, error = DataValidator.validate_podcast_script(script)
            assert is_valid, f"Unicode script should be valid: {error}"

    def test_timestamp_and_metadata_validation(self):
        """Test validation of timestamps and metadata."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))
            result = pipeline.run_full_pipeline(limit=2)

            assert result["success"], "Pipeline should succeed"

            # Load and validate metadata
            data_file = Path(result["data_file"])
            with open(data_file, 'r') as f:
                data = json.load(f)

            # Validate timestamp format
            timestamp = data["timestamp"]
            assert len(timestamp) == 15, "Invalid timestamp format"  # YYYYMMDD_HHMMSS
            assert timestamp[8] == "_", "Invalid timestamp separator"

            # Validate run_date ISO format
            run_date = data["run_date"]
            from datetime import datetime
            try:
                datetime.fromisoformat(run_date.replace('Z', '+00:00'))
            except ValueError:
                pytest.fail(f"Invalid ISO date format: {run_date}")

            # Validate config metadata
            config = data["config"]
            assert "environment" in config, "Missing environment in config"
            assert config["environment"] == "test", "Wrong environment"

    def teardown_method(self):
        """Cleanup after each test method."""
        # Log metrics if any were collected
        metrics = self.metrics.get_summary()
        if metrics:
            print(f"\nData validation metrics: {metrics}")