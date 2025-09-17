#!/usr/bin/env python
"""
Simple integration test for NotebookLM functionality.
This test validates the configuration and module imports work correctly.
"""

import sys
import os
from unittest.mock import patch, MagicMock


def test_notebooklm_imports():
    """Test that all NotebookLM modules can be imported."""
    try:
        from notebooklm_client import NotebookLMClient, NotebookLMPodcastGenerator
        from config import NotebookLMConfig, AppConfig
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_config_validation():
    """Test NotebookLM configuration validation."""
    try:
        from config import AppConfig, NotebookLMConfig

        # Test default configuration
        config = AppConfig()
        assert config.audio_generator == "tts"
        assert config.notebooklm.podcast_length == "STANDARD"
        assert config.notebooklm.location == "global"
        print("✅ Default configuration validation passed")

        # Test NotebookLM configuration
        config.audio_generator = "notebooklm"
        config.notebooklm.project_number = "123456789"
        print("✅ NotebookLM configuration setup successful")

        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_pipeline_integration():
    """Test pipeline integration with NotebookLM."""
    try:
        from main import HackerCastPipeline
        from config import initialize_config

        # Mock the config to avoid requiring actual credentials
        with patch.dict(os.environ, {
            'AUDIO_GENERATOR': 'notebooklm',
            'NOTEBOOKLM_PROJECT_NUMBER': '123456789',
            'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path/to/creds.json'
        }):
            config_manager = initialize_config()
            config_manager.config.audio_generator = "notebooklm"
            config_manager.config.notebooklm.project_number = "123456789"

            pipeline = HackerCastPipeline()
            assert pipeline.config.audio_generator == "notebooklm"
            print("✅ Pipeline integration successful")

        return True
    except Exception as e:
        print(f"❌ Pipeline integration test failed: {e}")
        return False


def test_cli_commands():
    """Test that CLI commands are available."""
    try:
        from main import cli

        # Check if notebooklm command is registered
        commands = [cmd.name for cmd in cli.commands.values()]
        assert "notebooklm" in commands
        assert "run" in commands
        assert "tts" in commands
        print("✅ CLI commands available")

        return True
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("🧪 Running NotebookLM Integration Tests\n")

    tests = [
        ("Module Imports", test_notebooklm_imports),
        ("Configuration Validation", test_config_validation),
        ("Pipeline Integration", test_pipeline_integration),
        ("CLI Commands", test_cli_commands),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        try:
            if test_func():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}\n")

    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All integration tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())