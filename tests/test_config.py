"""Tests for configuration module."""

import os
import tempfile
import pytest
from unittest.mock import patch
from pathlib import Path

from config import (
    ConfigManager, AppConfig, HackerNewsConfig, ScrapingConfig,
    TTSConfig, LoggingConfig, OutputConfig, get_config, initialize_config
)


class TestAppConfig:
    """Test AppConfig dataclass."""

    def test_app_config_defaults(self):
        """Test default configuration values."""
        config = AppConfig()

        assert config.environment == 'development'
        assert config.debug is False
        assert isinstance(config.hackernews, HackerNewsConfig)
        assert isinstance(config.scraping, ScrapingConfig)
        assert isinstance(config.tts, TTSConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.output, OutputConfig)


class TestHackerNewsConfig:
    """Test HackerNewsConfig dataclass."""

    def test_hackernews_config_defaults(self):
        """Test default HN configuration values."""
        config = HackerNewsConfig()

        assert config.base_url == "https://hacker-news.firebaseio.com/v0"
        assert config.max_stories == 20
        assert config.timeout == 30
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0


class TestScrapingConfig:
    """Test ScrapingConfig dataclass."""

    def test_scraping_config_defaults(self):
        """Test default scraping configuration values."""
        config = ScrapingConfig()

        assert "HackerCast" in config.user_agent
        assert config.timeout == 30
        assert config.retry_attempts == 3
        assert config.max_content_length == 1048576
        assert 'text/html' in config.allowed_content_types


class TestTTSConfig:
    """Test TTSConfig dataclass."""

    def test_tts_config_defaults(self):
        """Test default TTS configuration values."""
        config = TTSConfig()

        assert config.language_code == 'en-US'
        assert config.voice_name == 'en-US-Neural2-D'
        assert config.speaking_rate == 1.0
        assert config.pitch == 0.0
        assert config.max_text_length == 5000
        assert config.audio_format == 'MP3'


class TestLoggingConfig:
    """Test LoggingConfig dataclass."""

    def test_logging_config_defaults(self):
        """Test default logging configuration values."""
        config = LoggingConfig()

        assert config.level == 'INFO'
        assert '%(asctime)s' in config.format
        assert config.log_file is None
        assert config.max_log_size == 10485760
        assert config.backup_count == 5


class TestOutputConfig:
    """Test OutputConfig dataclass."""

    def test_output_config_defaults(self):
        """Test default output configuration values."""
        config = OutputConfig()

        assert config.base_dir == 'output'
        assert config.audio_dir == 'audio'
        assert config.data_dir == 'data'
        assert config.logs_dir == 'logs'
        assert config.date_format == '%Y-%m-%d'


class TestConfigManager:
    """Test ConfigManager class."""

    def test_config_manager_initialization(self):
        """Test config manager initialization with defaults."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict('os.environ', {
                'OUTPUT_BASE_DIR': temp_dir,
                'HACKERCAST_ENV': 'test'
            }):
                config_manager = ConfigManager()

                assert config_manager.config.environment == 'test'
                assert isinstance(config_manager.config, AppConfig)

                # Check that directories were created
                output_path = Path(temp_dir)
                assert (output_path / 'audio').exists()
                assert (output_path / 'data').exists()
                assert (output_path / 'logs').exists()

    def test_load_from_environment(self):
        """Test loading configuration from environment variables."""
        with patch.dict('os.environ', {
            'HACKERCAST_ENV': 'production',
            'HACKERCAST_DEBUG': 'true',
            'HN_MAX_STORIES': '10',
            'HN_TIMEOUT': '60',
            'SCRAPING_USER_AGENT': 'TestAgent/1.0',
            'TTS_LANGUAGE_CODE': 'en-GB',
            'TTS_VOICE_NAME': 'en-GB-Neural2-A',
            'TTS_SPEAKING_RATE': '1.2',
            'LOG_LEVEL': 'DEBUG',
            'OUTPUT_BASE_DIR': '/tmp/test'
        }):
            config_manager = ConfigManager()
            config = config_manager.config

            assert config.environment == 'production'
            assert config.debug is True
            assert config.hackernews.max_stories == 10
            assert config.hackernews.timeout == 60
            assert config.scraping.user_agent == 'TestAgent/1.0'
            assert config.tts.language_code == 'en-GB'
            assert config.tts.voice_name == 'en-GB-Neural2-A'
            assert config.tts.speaking_rate == 1.2
            assert config.logging.level == 'DEBUG'
            assert config.output.base_dir == '/tmp/test'

    def test_validate_config_success(self):
        """Test configuration validation with valid values."""
        with patch.dict('os.environ', {
            'HN_MAX_STORIES': '5',
            'SCRAPING_TIMEOUT': '30',
            'TTS_SPEAKING_RATE': '1.0',
            'TTS_PITCH': '0.0',
            'LOG_LEVEL': 'INFO'
        }):
            # Should not raise any exceptions
            config_manager = ConfigManager()
            assert config_manager.config is not None

    def test_validate_config_invalid_hn_max_stories(self):
        """Test configuration validation with invalid HN max stories."""
        with patch.dict('os.environ', {'HN_MAX_STORIES': '-1'}):
            with pytest.raises(ValueError, match="HN max_stories must be positive"):
                ConfigManager()

    def test_validate_config_invalid_speaking_rate(self):
        """Test configuration validation with invalid speaking rate."""
        with patch.dict('os.environ', {'TTS_SPEAKING_RATE': '5.0'}):
            with pytest.raises(ValueError, match="TTS speaking rate must be between"):
                ConfigManager()

    def test_validate_config_invalid_pitch(self):
        """Test configuration validation with invalid pitch."""
        with patch.dict('os.environ', {'TTS_PITCH': '25.0'}):
            with pytest.raises(ValueError, match="TTS pitch must be between"):
                ConfigManager()

    def test_validate_config_invalid_log_level(self):
        """Test configuration validation with invalid log level."""
        with patch.dict('os.environ', {'LOG_LEVEL': 'INVALID'}):
            with pytest.raises(ValueError, match="Log level must be one of"):
                ConfigManager()

    def test_get_output_path(self):
        """Test getting output file paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict('os.environ', {'OUTPUT_BASE_DIR': temp_dir}):
                config_manager = ConfigManager()

                audio_path = config_manager.get_output_path('audio', 'test.mp3')
                data_path = config_manager.get_output_path('data', 'test.json')
                logs_path = config_manager.get_output_path('logs', 'test.log')

                assert audio_path == Path(temp_dir) / 'audio' / 'test.mp3'
                assert data_path == Path(temp_dir) / 'data' / 'test.json'
                assert logs_path == Path(temp_dir) / 'logs' / 'test.log'

    def test_get_output_path_invalid_type(self):
        """Test getting output path with invalid file type."""
        config_manager = ConfigManager()

        with pytest.raises(ValueError, match="Unknown file type"):
            config_manager.get_output_path('invalid', 'test.txt')

    def test_get_log_config_dict(self):
        """Test getting logging configuration dictionary."""
        with patch.dict('os.environ', {
            'LOG_LEVEL': 'DEBUG',
            'LOG_FILE': 'test.log'
        }):
            config_manager = ConfigManager()
            log_config = config_manager.get_log_config_dict()

            assert log_config['version'] == 1
            assert 'formatters' in log_config
            assert 'handlers' in log_config
            assert 'loggers' in log_config

            # Check that file handler is included when log file is specified
            assert 'file' in log_config['handlers']
            assert 'file' in log_config['loggers']['']['handlers']

    def test_get_log_config_dict_console_only(self):
        """Test getting logging configuration with console handler only."""
        config_manager = ConfigManager()
        log_config = config_manager.get_log_config_dict()

        assert 'console' in log_config['handlers']
        assert 'file' not in log_config['handlers']
        assert log_config['loggers']['']['handlers'] == ['console']


class TestGlobalFunctions:
    """Test global configuration functions."""

    def test_get_config_singleton(self):
        """Test that get_config returns the same instance."""
        # Reset global state
        import config
        config._config_manager = None

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_initialize_config(self):
        """Test explicit configuration initialization."""
        # Reset global state
        import config
        config._config_manager = None

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict('os.environ', {
                'OUTPUT_BASE_DIR': temp_dir,
                'HACKERCAST_ENV': 'test'
            }):
                config_manager = initialize_config()

                assert isinstance(config_manager, ConfigManager)
                assert config_manager.config.environment == 'test'

    def test_initialize_config_with_file(self):
        """Test configuration initialization with config file."""
        # Reset global state
        import config
        config._config_manager = None

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"test": "config"}')
            config_file = f.name

        try:
            config_manager = initialize_config(config_file)
            assert isinstance(config_manager, ConfigManager)
        finally:
            os.unlink(config_file)