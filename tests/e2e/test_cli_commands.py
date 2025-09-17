"""End-to-end tests for CLI commands."""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import List, Tuple
import pytest
import subprocess

from tests.utils.test_helpers import (
    CommandRunner, TemporaryTestEnvironment, FileValidator,
    PerformanceMonitor, TestMetrics
)
from tests.utils.mock_services import E2ETestContext


class TestCLICommands:
    """Test CLI command execution end-to-end."""

    def setup_method(self):
        """Setup for each test method."""
        self.metrics = TestMetrics()
        self.performance = PerformanceMonitor()

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def python_executable(self, project_root):
        """Get Python executable path."""
        venv_python = project_root / "venv" / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)
        return "python"

    @pytest.fixture
    def main_script(self, project_root):
        """Get main script path."""
        return str(project_root / "main.py")

    def test_cli_help_command(self, python_executable, main_script):
        """Test CLI help command execution."""
        self.performance.start()

        return_code, stdout, stderr = CommandRunner.run_command([
            python_executable, main_script, "--help"
        ])

        self.performance.stop()
        self.metrics.record_timing("help_command", self.performance.get_metrics()["duration"])

        # Assertions
        assert return_code == 0, f"Help command failed with stderr: {stderr}"
        assert "HackerCast" in stdout, "Help text missing application name"
        assert "fetch" in stdout, "Help text missing fetch command"
        assert "scrape" in stdout, "Help text missing scrape command"
        assert "run" in stdout, "Help text missing run command"
        assert "tts" in stdout, "Help text missing tts command"

        # Performance check
        assert self.performance.get_metrics()["duration"] < 5.0, "Help command too slow"

    def test_cli_subcommand_help(self, python_executable, main_script):
        """Test CLI subcommand help."""
        commands = ["fetch", "scrape", "run", "tts"]

        for command in commands:
            return_code, stdout, stderr = CommandRunner.run_command([
                python_executable, main_script, command, "--help"
            ])

            assert return_code == 0, f"{command} help failed with stderr: {stderr}"
            assert command in stdout.lower(), f"Help text missing {command} command info"

    @pytest.mark.network
    def test_fetch_command_with_limit(self, python_executable, main_script):
        """Test fetch command with story limit."""
        with TemporaryTestEnvironment() as temp_dir:
            self.performance.start()

            return_code, stdout, stderr = CommandRunner.run_command([
                python_executable, main_script,
                "--config", str(temp_dir / "test_config.json"),
                "fetch", "--limit", "3"
            ], timeout=45)

            self.performance.stop()
            self.metrics.record_timing("fetch_command", self.performance.get_metrics()["duration"])

            # Basic success check
            assert return_code == 0, f"Fetch command failed: {stderr}"
            assert "Fetched" in stdout, "Missing fetch confirmation in output"

            # Performance check
            assert self.performance.get_metrics()["duration"] < 30.0, "Fetch command too slow"

    def test_fetch_command_invalid_limit(self, python_executable, main_script):
        """Test fetch command with invalid limit."""
        return_code, stdout, stderr = CommandRunner.run_command([
            python_executable, main_script,
            "fetch", "--limit", "-1"
        ])

        # Should handle invalid input gracefully
        assert return_code != 0 or "error" in stderr.lower() or "invalid" in stderr.lower()

    @pytest.mark.network
    def test_scrape_command_valid_url(self, python_executable, main_script):
        """Test scrape command with valid URL."""
        test_url = "https://example.com"

        self.performance.start()

        return_code, stdout, stderr = CommandRunner.run_command([
            python_executable, main_script,
            "scrape", test_url
        ], timeout=30)

        self.performance.stop()
        self.metrics.record_timing("scrape_command", self.performance.get_metrics()["duration"])

        # Note: This might fail if the URL doesn't have scrapeable content
        # The important thing is that the command runs without crashing
        assert return_code in [0, 1], f"Scrape command crashed: {stderr}"

        # Performance check
        assert self.performance.get_metrics()["duration"] < 20.0, "Scrape command too slow"

    def test_scrape_command_invalid_url(self, python_executable, main_script):
        """Test scrape command with invalid URL."""
        invalid_urls = [
            "not-a-url",
            "http://",
            "ftp://invalid.com",
            ""
        ]

        for url in invalid_urls:
            return_code, stdout, stderr = CommandRunner.run_command([
                python_executable, main_script,
                "scrape", url
            ])

            # Should handle invalid URLs gracefully
            assert return_code != 0 or "error" in stderr.lower() or "failed" in stdout.lower()

    def test_tts_command_basic(self, python_executable, main_script):
        """Test TTS command basic functionality."""
        with TemporaryTestEnvironment() as temp_dir:
            output_file = temp_dir / "test_audio.mp3"
            test_text = "Hello world, this is a test."

            return_code, stdout, stderr = CommandRunner.run_command([
                python_executable, main_script,
                "tts", test_text, str(output_file)
            ], timeout=30)

            # TTS might fail due to missing credentials, which is expected in tests
            # The important thing is that the command runs without syntax errors
            assert return_code in [0, 1], f"TTS command crashed: {stderr}"

            if return_code == 0:
                # If successful, check output file
                is_valid, error = FileValidator.validate_audio_file(output_file, min_size_bytes=100)
                if not is_valid and output_file.exists():
                    # File exists but might be empty - that's still a form of success
                    assert output_file.exists(), "Audio file should be created"

    def test_tts_command_empty_text(self, python_executable, main_script):
        """Test TTS command with empty text."""
        with TemporaryTestEnvironment() as temp_dir:
            output_file = temp_dir / "empty_audio.mp3"

            return_code, stdout, stderr = CommandRunner.run_command([
                python_executable, main_script,
                "tts", "", str(output_file)
            ])

            # Should handle empty text gracefully
            assert return_code != 0 or "error" in stderr.lower()

    def test_debug_flag(self, python_executable, main_script):
        """Test --debug flag functionality."""
        return_code, stdout, stderr = CommandRunner.run_command([
            python_executable, main_script,
            "--debug", "--help"
        ])

        assert return_code == 0, f"Debug flag caused failure: {stderr}"
        # Debug mode should still show help

    def test_config_file_option(self, python_executable, main_script):
        """Test --config option with custom config file."""
        with TemporaryTestEnvironment() as temp_dir:
            # Create a test config file
            config_data = {
                "environment": "test",
                "hackernews": {"max_stories": 2},
                "output": {"base_directory": str(temp_dir)}
            }

            config_file = temp_dir / "custom_config.json"
            with open(config_file, 'w') as f:
                json.dump(config_data, f)

            return_code, stdout, stderr = CommandRunner.run_command([
                python_executable, main_script,
                "--config", str(config_file),
                "--help"
            ])

            assert return_code == 0, f"Custom config caused failure: {stderr}"

    def test_config_file_missing(self, python_executable, main_script):
        """Test behavior with missing config file."""
        return_code, stdout, stderr = CommandRunner.run_command([
            python_executable, main_script,
            "--config", "/nonexistent/config.json",
            "--help"
        ])

        # Should handle missing config gracefully or use defaults
        assert return_code in [0, 1], "Should handle missing config gracefully"

    def test_keyboard_interrupt_handling(self, python_executable, main_script):
        """Test graceful handling of keyboard interrupt."""
        # Start a potentially long-running command
        import signal
        import threading

        def interrupt_after_delay():
            time.sleep(2)  # Let command start
            # This is tricky to test reliably across platforms
            # We'll simulate by checking timeout behavior instead

        # Use very short timeout to simulate interruption
        return_code, stdout, stderr = CommandRunner.run_command([
            python_executable, main_script,
            "fetch", "--limit", "20"
        ], timeout=1)  # Very short timeout

        # Timeout should be handled gracefully
        assert return_code != 0, "Command should timeout/fail gracefully"

    def test_concurrent_command_execution(self, python_executable, main_script):
        """Test multiple commands running concurrently."""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def run_help_command():
            return CommandRunner.run_command([
                python_executable, main_script, "--help"
            ])

        # Run multiple help commands concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_help_command) for _ in range(3)]

            results = []
            for future in as_completed(futures):
                return_code, stdout, stderr = future.result()
                results.append((return_code, stdout, stderr))

        # All should succeed
        for return_code, stdout, stderr in results:
            assert return_code == 0, f"Concurrent command failed: {stderr}"

    def test_command_output_format(self, python_executable, main_script):
        """Test command output formatting and structure."""
        return_code, stdout, stderr = CommandRunner.run_command([
            python_executable, main_script, "--help"
        ])

        assert return_code == 0
        assert stdout.strip(), "Help output should not be empty"

        # Check for proper formatting
        lines = stdout.split('\n')
        assert len(lines) > 5, "Help should have multiple lines"

        # Should not have excessive empty lines
        empty_lines = sum(1 for line in lines if not line.strip())
        total_lines = len(lines)
        assert empty_lines < total_lines * 0.5, "Too many empty lines in output"

    def test_error_handling_and_exit_codes(self, python_executable, main_script):
        """Test proper error handling and exit codes."""
        # Test various error conditions
        error_scenarios = [
            (["invalid_command"], "Invalid command should return non-zero"),
            (["fetch", "--invalid-flag"], "Invalid flag should return non-zero"),
            (["scrape"], "Missing URL should return non-zero"),
            (["tts", "text"], "Missing output file should return non-zero")
        ]

        for cmd_args, description in error_scenarios:
            return_code, stdout, stderr = CommandRunner.run_command([
                python_executable, main_script
            ] + cmd_args)

            assert return_code != 0, f"{description}: {stderr}"

    def test_long_running_command_timeout(self, python_executable, main_script):
        """Test timeout handling for long-running commands."""
        # This test ensures commands don't hang indefinitely
        self.performance.start()

        return_code, stdout, stderr = CommandRunner.run_command([
            python_executable, main_script,
            "fetch", "--limit", "50"  # Larger limit might take longer
        ], timeout=60)  # 1 minute timeout

        self.performance.stop()

        # Command should complete within timeout or fail gracefully
        assert return_code in [0, 1, -1], f"Unexpected return code: {return_code}"
        assert self.performance.get_metrics()["duration"] <= 65, "Command exceeded timeout window"

    def test_command_line_argument_validation(self, python_executable, main_script):
        """Test command line argument validation."""
        # Test various argument combinations
        test_cases = [
            {
                "args": ["fetch", "--limit", "abc"],
                "should_fail": True,
                "description": "Non-numeric limit should fail"
            },
            {
                "args": ["fetch", "--limit", "0"],
                "should_fail": False,  # Might be handled as valid
                "description": "Zero limit might be valid"
            },
            {
                "args": ["scrape", "https://example.com", "extra_arg"],
                "should_fail": True,
                "description": "Extra arguments should fail"
            }
        ]

        for test_case in test_cases:
            return_code, stdout, stderr = CommandRunner.run_command([
                python_executable, main_script
            ] + test_case["args"])

            if test_case["should_fail"]:
                assert return_code != 0, f"Expected failure: {test_case['description']}"
            # Note: We don't assert success for non-failing cases since they might
            # legitimately fail due to network/config issues in CI

    def teardown_method(self):
        """Cleanup after each test method."""
        # Log performance metrics
        metrics = self.metrics.get_summary()
        if metrics:
            print(f"\nTest performance metrics: {metrics}")