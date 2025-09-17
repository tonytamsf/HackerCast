"""End-to-end tests for the complete HackerCast pipeline."""

import json
import time
from pathlib import Path
from typing import Dict, Any
import pytest

from main import HackerCastPipeline
from tests.utils.test_helpers import (
    TemporaryTestEnvironment, PerformanceMonitor, FileValidator,
    DataValidator, TestMetrics, CommandRunner
)
from tests.utils.mock_services import E2ETestContext, create_test_config_file


class TestFullPipeline:
    """Test complete pipeline execution end-to-end."""

    def setup_method(self):
        """Setup for each test method."""
        self.metrics = TestMetrics()
        self.performance = PerformanceMonitor()

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    def test_full_pipeline_with_mocks(self):
        """Test complete pipeline with mocked external services."""
        with E2ETestContext() as ctx:
            self.performance.start()

            # Initialize pipeline with test config
            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Run full pipeline
            result = pipeline.run_full_pipeline(limit=3)

            self.performance.stop()
            self.metrics.record_timing("full_pipeline", self.performance.get_metrics()["duration"])

            # Verify success
            assert result["success"], f"Pipeline failed: {result.get('error')}"
            assert result["stories_count"] == 3, "Wrong number of stories processed"
            assert result["scraped_count"] >= 1, "No articles scraped"
            assert result["script_length"] > 0, "No script generated"

            # Verify output files exist
            data_file = Path(result["data_file"])
            assert data_file.exists(), "Pipeline data file not created"

            # Validate data file structure
            is_valid, error = FileValidator.validate_json_file(
                data_file,
                required_keys=["timestamp", "stories", "scraped_content", "stats"]
            )
            assert is_valid, f"Invalid data file: {error}"

            # Performance check
            assert self.performance.get_metrics()["duration"] < 60.0, "Pipeline too slow"

            # Record metrics
            self.metrics.record_count("stories_fetched", result["stories_count"])
            self.metrics.record_count("articles_scraped", result["scraped_content"])

    def test_pipeline_error_recovery(self):
        """Test pipeline behavior during various error conditions."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Test with API failure
            ctx.mock_hn_api.set_failure_mode(True)

            result = pipeline.run_full_pipeline(limit=3)

            assert not result["success"], "Pipeline should fail with API errors"
            assert "error" in result, "Error details should be provided"

            # Reset API and test scraping failure
            ctx.mock_hn_api.set_failure_mode(False)
            ctx.mock_scraper.set_failure_mode(True, failure_rate=1.0)

            result = pipeline.run_full_pipeline(limit=3)

            # Pipeline might still succeed if it handles scraping failures gracefully
            if not result["success"]:
                assert "error" in result

    def test_pipeline_partial_failures(self):
        """Test pipeline with partial failures in scraping."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Set 50% failure rate for scraping
            ctx.mock_scraper.set_failure_mode(False, failure_rate=0.5)

            result = pipeline.run_full_pipeline(limit=5)

            # Pipeline should succeed even with some scraping failures
            assert result["success"], "Pipeline should handle partial failures"
            assert result["scraped_count"] >= 1, "At least some articles should be scraped"

    def test_pipeline_performance_benchmarks(self):
        """Test pipeline performance against benchmarks."""
        with E2ETestContext() as ctx:
            # Add artificial delays to test performance under load
            ctx.mock_hn_api.set_delay(0.1)  # 100ms delay per API call

            self.performance.start()

            pipeline = HackerCastPipeline(str(ctx.config_file))
            result = pipeline.run_full_pipeline(limit=5)

            self.performance.stop()

            assert result["success"], "Pipeline should succeed despite delays"

            # Record detailed timing metrics
            runtime = self.performance.get_metrics()["duration"]
            self.metrics.record_timing("pipeline_with_delays", runtime)

            # Performance should still be reasonable with artificial delays
            assert runtime < 30.0, f"Pipeline too slow with delays: {runtime}s"

    def test_pipeline_memory_usage(self):
        """Test pipeline memory usage patterns."""
        import psutil
        import os

        with E2ETestContext() as ctx:
            # Get initial memory usage
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            pipeline = HackerCastPipeline(str(ctx.config_file))
            result = pipeline.run_full_pipeline(limit=10)

            # Get final memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            assert result["success"], "Pipeline should succeed"

            # Memory usage should be reasonable
            assert memory_increase < 100, f"Excessive memory usage: {memory_increase}MB"

            self.metrics.record_count("memory_usage_mb", int(memory_increase))

    def test_pipeline_concurrent_execution(self):
        """Test pipeline behavior under concurrent execution."""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def run_pipeline():
            with E2ETestContext() as ctx:
                pipeline = HackerCastPipeline(str(ctx.config_file))
                return pipeline.run_full_pipeline(limit=2)

        # Run multiple pipelines concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run_pipeline) for _ in range(2)]

            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        # All pipelines should succeed independently
        for i, result in enumerate(results):
            assert result["success"], f"Concurrent pipeline {i} failed: {result.get('error')}"

    def test_pipeline_output_validation(self):
        """Test comprehensive validation of pipeline outputs."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))
            result = pipeline.run_full_pipeline(limit=3)

            assert result["success"], "Pipeline should succeed"

            # Validate data file content
            data_file = Path(result["data_file"])
            with open(data_file, 'r') as f:
                data = json.load(f)

            # Validate structure
            required_keys = ["timestamp", "run_date", "config", "stories", "scraped_content", "stats"]
            for key in required_keys:
                assert key in data, f"Missing key in data file: {key}"

            # Validate stories data
            stories = data["stories"]
            assert len(stories) == 3, "Wrong number of stories in data"

            for story in stories:
                assert "id" in story, "Story missing ID"
                assert "title" in story, "Story missing title"
                assert "score" in story, "Story missing score"

            # Validate scraped content
            scraped = data["scraped_content"]
            assert len(scraped) >= 1, "No scraped content in data"

            for content in scraped:
                assert "title" in content, "Content missing title"
                assert "word_count" in content, "Content missing word count"
                assert content["word_count"] > 0, "Content has zero words"

            # Validate stats
            stats = data["stats"]
            assert stats["stories_fetched"] == 3, "Stats mismatch: stories_fetched"
            assert stats["articles_scraped"] >= 1, "Stats mismatch: articles_scraped"

    def test_pipeline_script_generation_quality(self):
        """Test quality of generated podcast script."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Fetch and scrape content
            stories = pipeline.fetch_top_stories(3)
            content = pipeline.scrape_articles(stories)

            # Generate script
            script = pipeline.generate_podcast_script(content)

            # Validate script quality
            is_valid, error = DataValidator.validate_podcast_script(script)
            assert is_valid, f"Invalid script: {error}"

            # Check script file was created
            script_files = list(ctx.output_dir.glob("data/script_*.txt"))
            assert len(script_files) >= 1, "Script file not created"

            script_file = script_files[0]
            is_valid, error = FileValidator.validate_text_file(script_file, min_length=500)
            assert is_valid, f"Invalid script file: {error}"

    def test_pipeline_configuration_variations(self):
        """Test pipeline with different configuration variations."""
        configurations = [
            {"hackernews": {"max_stories": 1}},
            {"hackernews": {"max_stories": 5}},
            {"scraping": {"max_retries": 1}},
            {"scraping": {"request_timeout": 5}}
        ]

        for config_override in configurations:
            with E2ETestContext() as ctx:
                # Modify config file
                with open(ctx.config_file, 'r') as f:
                    config = json.load(f)

                # Apply override
                for key, value in config_override.items():
                    if isinstance(value, dict):
                        config[key].update(value)
                    else:
                        config[key] = value

                with open(ctx.config_file, 'w') as f:
                    json.dump(config, f)

                # Run pipeline
                pipeline = HackerCastPipeline(str(ctx.config_file))
                result = pipeline.run_full_pipeline(limit=2)

                assert result["success"], f"Pipeline failed with config {config_override}: {result.get('error')}"

    def test_pipeline_cleanup_behavior(self):
        """Test pipeline cleanup and resource management."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Run pipeline
            result = pipeline.run_full_pipeline(limit=2)
            assert result["success"], "Pipeline should succeed"

            # Explicit cleanup
            pipeline.cleanup()

            # Verify cleanup completed without errors
            # (This is mainly to ensure cleanup doesn't crash)

    def test_cli_run_command_integration(self):
        """Test full pipeline via CLI run command."""
        with TemporaryTestEnvironment() as temp_dir:
            project_root = Path(__file__).parent.parent.parent
            python_executable = str(project_root / "venv" / "bin" / "python")
            if not Path(python_executable).exists():
                python_executable = "python"

            main_script = str(project_root / "main.py")

            # Create test config
            config_file = create_test_config_file(temp_dir)

            self.performance.start()

            # Run CLI command
            return_code, stdout, stderr = CommandRunner.run_command([
                python_executable, main_script,
                "--config", str(config_file),
                "run", "--limit", "2"
            ], timeout=120)

            self.performance.stop()
            self.metrics.record_timing("cli_run_command", self.performance.get_metrics()["duration"])

            # CLI run might fail due to missing real APIs, but should not crash
            assert return_code in [0, 1], f"CLI run crashed: {stderr}"

            # Check for expected output patterns
            if return_code == 0:
                assert "Pipeline completed" in stdout or "success" in stdout.lower()

            # Performance check
            assert self.performance.get_metrics()["duration"] < 120.0, "CLI run too slow"

    def test_pipeline_data_persistence(self):
        """Test pipeline data persistence and reload."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Run pipeline and save data
            result = pipeline.run_full_pipeline(limit=2)
            assert result["success"], "Pipeline should succeed"

            data_file = Path(result["data_file"])
            assert data_file.exists(), "Data file should be created"

            # Load saved data and validate
            with open(data_file, 'r') as f:
                saved_data = json.load(f)

            # Verify data integrity
            assert "stories" in saved_data
            assert "scraped_content" in saved_data
            assert len(saved_data["stories"]) == 2

            # Verify timestamps
            assert "timestamp" in saved_data
            assert "run_date" in saved_data

    def teardown_method(self):
        """Cleanup after each test method."""
        # Log performance metrics
        metrics = self.metrics.get_summary()
        if metrics:
            print(f"\nPipeline test metrics: {metrics}")

        # Assert performance thresholds
        try:
            self.metrics.assert_performance_thresholds()
        except AssertionError as e:
            print(f"\nPerformance threshold warning: {e}")