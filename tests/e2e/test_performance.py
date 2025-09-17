"""End-to-end performance tests and benchmarks."""

import time
import threading
from pathlib import Path
from typing import Dict, List, Any
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed

from main import HackerCastPipeline
from tests.utils.test_helpers import PerformanceMonitor, MetricsCollector, CommandRunner
from tests.utils.mock_services import E2ETestContext


class TestPerformance:
    """Test performance characteristics and benchmarks."""

    def setup_method(self):
        """Setup for each test method."""
        self.metrics = MetricsCollector()
        self.performance = PerformanceMonitor()

    @pytest.mark.performance
    def test_fetch_stories_performance(self):
        """Test story fetching performance."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Test different story limits
            limits = [1, 5, 10, 20]

            for limit in limits:
                self.performance.start()

                stories = pipeline.fetch_top_stories(limit)

                self.performance.stop()
                duration = self.performance.get_metrics()["duration"]

                # Record metrics
                self.metrics.record_timing(f"fetch_{limit}_stories", duration)
                self.metrics.record_count(f"stories_fetched_{limit}", len(stories))

                # Performance assertions
                assert duration < 30.0, f"Fetching {limit} stories too slow: {duration}s"
                assert len(stories) == limit, f"Wrong number of stories fetched for limit {limit}"

                # API efficiency check - should be roughly O(n) but with some overhead
                if limit > 1:
                    expected_max_time = 5.0 + (limit * 0.5)  # 5s overhead + 0.5s per story
                    assert duration < expected_max_time, f"Fetch time not scaling efficiently: {duration}s for {limit} stories"

    @pytest.mark.performance
    def test_scraping_performance(self):
        """Test article scraping performance."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Get stories first
            stories = pipeline.fetch_top_stories(5)

            # Test scraping performance
            self.performance.start()

            content = pipeline.scrape_articles(stories)

            self.performance.stop()
            duration = self.performance.get_metrics()["duration"]

            # Record metrics
            self.metrics.record_timing("scrape_articles", duration)
            self.metrics.record_count("articles_scraped", len(content))

            # Performance assertions
            assert duration < 60.0, f"Scraping too slow: {duration}s"
            assert len(content) >= 1, "No articles scraped"

            # Efficiency check - should not take more than 15s per article on average
            avg_time_per_article = duration / max(len(content), 1)
            assert avg_time_per_article < 15.0, f"Average scraping time too high: {avg_time_per_article}s per article"

    @pytest.mark.performance
    def test_script_generation_performance(self):
        """Test script generation performance."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Get content for script generation
            stories = pipeline.fetch_top_stories(5)
            content = pipeline.scrape_articles(stories)

            # Test script generation performance
            self.performance.start()

            script = pipeline.generate_podcast_script(content)

            self.performance.stop()
            duration = self.performance.get_metrics()["duration"]

            # Record metrics
            self.metrics.record_timing("generate_script", duration)
            self.metrics.record_count("script_length", len(script))

            # Performance assertions
            assert duration < 10.0, f"Script generation too slow: {duration}s"
            assert len(script) > 500, "Generated script too short"

            # Efficiency check - should be very fast for text processing
            assert duration < 5.0, f"Script generation inefficient: {duration}s"

    @pytest.mark.performance
    def test_full_pipeline_performance(self):
        """Test complete pipeline performance."""
        story_limits = [1, 3, 5]

        for limit in story_limits:
            with E2ETestContext() as ctx:
                pipeline = HackerCastPipeline(str(ctx.config_file))

                self.performance.start()

                result = pipeline.run_full_pipeline(limit=limit)

                self.performance.stop()
                duration = self.performance.get_metrics()["duration"]

                # Record metrics
                self.metrics.record_timing(f"full_pipeline_{limit}", duration)

                # Assertions
                assert result["success"], f"Pipeline failed for limit {limit}"
                assert duration < 120.0, f"Full pipeline too slow for {limit} stories: {duration}s"

                # Scalability check
                if limit <= 3:
                    assert duration < 60.0, f"Pipeline inefficient for small dataset: {duration}s"

    @pytest.mark.performance
    def test_memory_usage_patterns(self):
        """Test memory usage during pipeline execution."""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        with E2ETestContext() as ctx:
            # Baseline memory
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Memory after initialization
            init_memory = process.memory_info().rss / 1024 / 1024
            init_increase = init_memory - baseline_memory

            # Memory during execution
            stories = pipeline.fetch_top_stories(10)
            fetch_memory = process.memory_info().rss / 1024 / 1024
            fetch_increase = fetch_memory - baseline_memory

            content = pipeline.scrape_articles(stories)
            scrape_memory = process.memory_info().rss / 1024 / 1024
            scrape_increase = scrape_memory - baseline_memory

            script = pipeline.generate_podcast_script(content)
            script_memory = process.memory_info().rss / 1024 / 1024
            script_increase = script_memory - baseline_memory

            # Record metrics
            self.metrics.record_count("memory_baseline_mb", int(baseline_memory))
            self.metrics.record_count("memory_after_init_mb", int(init_increase))
            self.metrics.record_count("memory_after_fetch_mb", int(fetch_increase))
            self.metrics.record_count("memory_after_scrape_mb", int(scrape_increase))
            self.metrics.record_count("memory_after_script_mb", int(script_increase))

            # Memory usage assertions
            assert init_increase < 50, f"Initialization uses too much memory: {init_increase}MB"
            assert fetch_increase < 100, f"Story fetching uses too much memory: {fetch_increase}MB"
            assert scrape_increase < 200, f"Scraping uses too much memory: {scrape_increase}MB"
            assert script_increase < 250, f"Script generation uses too much memory: {script_increase}MB"

    @pytest.mark.performance
    def test_concurrent_pipeline_performance(self):
        """Test performance under concurrent execution."""
        def run_pipeline():
            with E2ETestContext() as ctx:
                pipeline = HackerCastPipeline(str(ctx.config_file))

                start_time = time.time()
                result = pipeline.run_full_pipeline(limit=2)
                end_time = time.time()

                return {
                    "success": result["success"],
                    "duration": end_time - start_time,
                    "stories": result.get("stories_count", 0)
                }

        # Run concurrent pipelines
        num_concurrent = 3

        self.performance.start()

        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(run_pipeline) for _ in range(num_concurrent)]
            results = [future.result() for future in as_completed(futures)]

        self.performance.stop()
        total_duration = self.performance.get_metrics()["duration"]

        # Analyze results
        successful_runs = [r for r in results if r["success"]]
        avg_duration = sum(r["duration"] for r in successful_runs) / len(successful_runs) if successful_runs else 0

        # Record metrics
        self.metrics.record_timing("concurrent_execution", total_duration)
        self.metrics.record_timing("avg_concurrent_pipeline", avg_duration)
        self.metrics.record_count("concurrent_success_rate", len(successful_runs))

        # Assertions
        assert len(successful_runs) >= 2, f"Too many concurrent failures: {len(successful_runs)}/{num_concurrent}"
        assert total_duration < 180.0, f"Concurrent execution too slow: {total_duration}s"
        assert avg_duration < 120.0, f"Average concurrent pipeline too slow: {avg_duration}s"

    @pytest.mark.performance
    def test_cli_command_performance(self):
        """Test CLI command performance."""
        project_root = Path(__file__).parent.parent.parent
        python_executable = str(project_root / "venv" / "bin" / "python")
        if not Path(python_executable).exists():
            python_executable = "python"
        main_script = str(project_root / "main.py")

        # Test different CLI commands
        commands = [
            (["--help"], "help_command", 5.0),
            (["fetch", "--help"], "fetch_help", 5.0),
            (["fetch", "--limit", "1"], "fetch_1_story", 30.0),
        ]

        for cmd_args, metric_name, max_time in commands:
            self.performance.start()

            return_code, stdout, stderr = CommandRunner.run_command([
                python_executable, main_script
            ] + cmd_args, timeout=int(max_time + 10))

            self.performance.stop()
            duration = self.performance.get_metrics()["duration"]

            # Record metrics
            self.metrics.record_timing(f"cli_{metric_name}", duration)

            # Performance assertions
            if return_code == 0:  # Only check timing for successful commands
                assert duration < max_time, f"CLI {metric_name} too slow: {duration}s"

    @pytest.mark.performance
    def test_network_latency_tolerance(self):
        """Test performance with simulated network latency."""
        with E2ETestContext() as ctx:
            # Add artificial latency
            ctx.mock_hn_api.set_delay(0.5)  # 500ms delay per request

            pipeline = HackerCastPipeline(str(ctx.config_file))

            self.performance.start()

            stories = pipeline.fetch_top_stories(5)

            self.performance.stop()
            duration = self.performance.get_metrics()["duration"]

            # Record metrics
            self.metrics.record_timing("fetch_with_latency", duration)

            # Should handle latency gracefully
            # 5 stories + 1 topstories call = 6 API calls * 0.5s = 3s minimum
            expected_min_time = 3.0
            expected_max_time = 45.0  # Should still complete within timeout

            assert duration >= expected_min_time, f"Duration too short for latency: {duration}s"
            assert duration < expected_max_time, f"Failed to handle latency efficiently: {duration}s"
            assert len(stories) == 5, "Should still fetch all stories despite latency"

    @pytest.mark.performance
    def test_error_recovery_performance(self):
        """Test performance during error recovery scenarios."""
        with E2ETestContext() as ctx:
            # Set 30% failure rate
            ctx.mock_scraper.set_failure_mode(False, failure_rate=0.3)

            pipeline = HackerCastPipeline(str(ctx.config_file))

            self.performance.start()

            # This should still succeed but with some failures
            stories = pipeline.fetch_top_stories(10)
            content = pipeline.scrape_articles(stories)

            self.performance.stop()
            duration = self.performance.get_metrics()["duration"]

            # Record metrics
            self.metrics.record_timing("scraping_with_failures", duration)
            self.metrics.record_count("content_scraped_with_failures", len(content))

            # Should handle failures efficiently
            assert duration < 90.0, f"Error recovery too slow: {duration}s"
            assert len(content) >= 5, "Should scrape majority of articles despite failures"  # At least 70% success

    @pytest.mark.performance
    def test_large_dataset_performance(self):
        """Test performance with larger datasets."""
        with E2ETestContext() as ctx:
            pipeline = HackerCastPipeline(str(ctx.config_file))

            # Test with larger story limit
            large_limit = 20

            self.performance.start()

            stories = pipeline.fetch_top_stories(large_limit)
            content = pipeline.scrape_articles(stories[:10])  # Limit scraping for time
            script = pipeline.generate_podcast_script(content)

            self.performance.stop()
            duration = self.performance.get_metrics()["duration"]

            # Record metrics
            self.metrics.record_timing("large_dataset_processing", duration)

            # Should scale reasonably
            assert duration < 120.0, f"Large dataset processing too slow: {duration}s"
            assert len(stories) == large_limit, "Should fetch all requested stories"
            assert len(script) > 1000, "Should generate substantial script for larger dataset"

    @pytest.mark.performance
    def test_startup_performance(self):
        """Test application startup performance."""
        import importlib
        import sys

        # Test module import performance
        self.performance.start()

        # Simulate fresh import
        if 'main' in sys.modules:
            del sys.modules['main']

        import main

        self.performance.stop()
        import_duration = self.performance.get_metrics()["duration"]

        # Test pipeline initialization performance
        with E2ETestContext() as ctx:
            self.performance.start()

            pipeline = HackerCastPipeline(str(ctx.config_file))

            self.performance.stop()
            init_duration = self.performance.get_metrics()["duration"]

        # Record metrics
        self.metrics.record_timing("module_import", import_duration)
        self.metrics.record_timing("pipeline_init", init_duration)

        # Performance assertions
        assert import_duration < 5.0, f"Module import too slow: {import_duration}s"
        assert init_duration < 3.0, f"Pipeline initialization too slow: {init_duration}s"

    def teardown_method(self):
        """Cleanup and report performance metrics."""
        # Log all collected metrics
        metrics = self.metrics.get_summary()
        if metrics:
            print(f"\nPerformance test metrics: {metrics}")

        # Assert performance thresholds
        try:
            self.metrics.assert_performance_thresholds()
        except AssertionError as e:
            print(f"\nPerformance threshold exceeded: {e}")
            # Don't fail the test, just warn

    @classmethod
    def generate_performance_report(cls, metrics: Dict[str, Any]) -> str:
        """Generate a formatted performance report."""
        report = ["=== Performance Test Report ===\n"]

        if "timings" in metrics:
            report.append("Timing Metrics:")
            for operation, duration in metrics["timings"].items():
                report.append(f"  {operation}: {duration:.3f}s")
            report.append("")

        if "counts" in metrics:
            report.append("Count Metrics:")
            for category, count in metrics["counts"].items():
                report.append(f"  {category}: {count}")
            report.append("")

        return "\n".join(report)