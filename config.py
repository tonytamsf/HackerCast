#!/usr/bin/env python

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class HackerNewsConfig:
    """Configuration for Hacker News API."""

    base_url: str = "https://hacker-news.firebaseio.com/v0"
    max_stories: int = 20
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class ScrapingConfig:
    """Configuration for web scraping."""

    user_agent: str = "HackerCast/1.0 (https://github.com/tonytam/hackercast)"
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 2.0
    max_content_length: int = 1048576  # 1MB
    allowed_content_types: list = field(
        default_factory=lambda: ["text/html", "application/xhtml+xml"]
    )


@dataclass
class TTSConfig:
    """Configuration for Text-to-Speech."""

    language_code: str = "en-US"
    voice_name: str = "en-US-Neural2-D"
    speaking_rate: float = 1.0
    pitch: float = 0.0
    max_text_length: int = 5000
    audio_format: str = "MP3"


@dataclass
class LoggingConfig:
    """Configuration for logging."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    log_file: Optional[str] = None
    max_log_size: int = 10485760  # 10MB
    backup_count: int = 5


@dataclass
class PodcastPublishingConfig:
    """Configuration for podcast publishing."""

    enabled: bool = False
    api_key: Optional[str] = None
    default_show_id: Optional[str] = None
    base_url: str = "https://api.transistor.fm/v1"
    auto_publish: bool = True
    default_season: Optional[int] = None


@dataclass
class OutputConfig:
    """Configuration for output files."""

    base_dir: str = "output"
    audio_dir: str = "audio"
    data_dir: str = "data"
    logs_dir: str = "logs"
    date_format: str = "%Y-%m-%d"


@dataclass
class AppConfig:
    """Main application configuration."""

    # Environment
    environment: str = "development"
    debug: bool = False

    # Component configurations
    hackernews: HackerNewsConfig = field(default_factory=HackerNewsConfig)
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    podcast_publishing: PodcastPublishingConfig = field(default_factory=PodcastPublishingConfig)

    # Google Cloud
    google_credentials_path: Optional[str] = None
    google_project_id: Optional[str] = None


class ConfigManager:
    """Centralized configuration manager."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Optional path to configuration file
        """
        # Load environment variables from .env file
        load_dotenv()

        self._config = AppConfig()
        self._load_from_environment()

        if config_file and os.path.exists(config_file):
            self._load_from_file(config_file)

        self._validate_config()
        self._setup_directories()

    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        # Environment
        self._config.environment = os.getenv("HACKERCAST_ENV", self._config.environment)
        self._config.debug = os.getenv("HACKERCAST_DEBUG", "").lower() in (
            "true",
            "1",
            "yes",
        )

        # Hacker News API
        if os.getenv("HN_MAX_STORIES"):
            self._config.hackernews.max_stories = int(os.getenv("HN_MAX_STORIES"))
        if os.getenv("HN_TIMEOUT"):
            self._config.hackernews.timeout = int(os.getenv("HN_TIMEOUT"))

        # Scraping
        if os.getenv("SCRAPING_USER_AGENT"):
            self._config.scraping.user_agent = os.getenv("SCRAPING_USER_AGENT")
        if os.getenv("SCRAPING_TIMEOUT"):
            self._config.scraping.timeout = int(os.getenv("SCRAPING_TIMEOUT"))

        # TTS
        if os.getenv("TTS_LANGUAGE_CODE"):
            self._config.tts.language_code = os.getenv("TTS_LANGUAGE_CODE")
        if os.getenv("TTS_VOICE_NAME"):
            self._config.tts.voice_name = os.getenv("TTS_VOICE_NAME")
        if os.getenv("TTS_SPEAKING_RATE"):
            self._config.tts.speaking_rate = float(os.getenv("TTS_SPEAKING_RATE"))
        if os.getenv("TTS_PITCH"):
            self._config.tts.pitch = float(os.getenv("TTS_PITCH"))

        # Google Cloud
        self._config.google_credentials_path = os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )
        self._config.google_project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

        # Logging
        if os.getenv("LOG_LEVEL"):
            self._config.logging.level = os.getenv("LOG_LEVEL").upper()
        if os.getenv("LOG_FILE"):
            self._config.logging.log_file = os.getenv("LOG_FILE")

        # Output
        if os.getenv("OUTPUT_BASE_DIR"):
            self._config.output.base_dir = os.getenv("OUTPUT_BASE_DIR")

        # Podcast Publishing
        self._config.podcast_publishing.enabled = os.getenv("PODCAST_PUBLISHING_ENABLED", "").lower() in (
            "true", "1", "yes"
        )
        if os.getenv("TRANSISTOR_API_KEY"):
            self._config.podcast_publishing.api_key = os.getenv("TRANSISTOR_API_KEY")
        if os.getenv("TRANSISTOR_SHOW_ID"):
            self._config.podcast_publishing.default_show_id = os.getenv("TRANSISTOR_SHOW_ID")
        if os.getenv("TRANSISTOR_BASE_URL"):
            self._config.podcast_publishing.base_url = os.getenv("TRANSISTOR_BASE_URL")
        self._config.podcast_publishing.auto_publish = os.getenv("PODCAST_AUTO_PUBLISH", "true").lower() in (
            "true", "1", "yes"
        )
        if os.getenv("PODCAST_DEFAULT_SEASON"):
            self._config.podcast_publishing.default_season = int(os.getenv("PODCAST_DEFAULT_SEASON"))

    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from file (JSON/YAML)."""
        # This would implement file-based configuration loading
        # For now, we'll use environment variables only
        logger.info(f"Configuration file loading not yet implemented: {config_file}")

    def _validate_config(self) -> None:
        """Validate configuration values."""
        errors = []

        # Validate HN config
        if self._config.hackernews.max_stories <= 0:
            errors.append("HN max_stories must be positive")
        if self._config.hackernews.timeout <= 0:
            errors.append("HN timeout must be positive")

        # Validate scraping config
        if self._config.scraping.timeout <= 0:
            errors.append("Scraping timeout must be positive")
        if self._config.scraping.max_content_length <= 0:
            errors.append("Max content length must be positive")

        # Validate TTS config
        if not (0.25 <= self._config.tts.speaking_rate <= 4.0):
            errors.append("TTS speaking rate must be between 0.25 and 4.0")
        if not (-20.0 <= self._config.tts.pitch <= 20.0):
            errors.append("TTS pitch must be between -20.0 and 20.0")

        # Validate logging config
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self._config.logging.level not in valid_log_levels:
            errors.append(f"Log level must be one of: {valid_log_levels}")

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

    def _setup_directories(self) -> None:
        """Create necessary output directories."""
        base_path = Path(self._config.output.base_dir)
        directories = [
            base_path,
            base_path / self._config.output.audio_dir,
            base_path / self._config.output.data_dir,
            base_path / self._config.output.logs_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")

    @property
    def config(self) -> AppConfig:
        """Get the current configuration."""
        return self._config

    def get_output_path(self, file_type: str, filename: str) -> Path:
        """
        Get the full path for an output file.

        Args:
            file_type: Type of file ('audio', 'data', 'logs')
            filename: Name of the file

        Returns:
            Full path to the file
        """
        base_path = Path(self._config.output.base_dir)

        if file_type == "audio":
            return base_path / self._config.output.audio_dir / filename
        elif file_type == "data":
            return base_path / self._config.output.data_dir / filename
        elif file_type == "logs":
            return base_path / self._config.output.logs_dir / filename
        else:
            raise ValueError(f"Unknown file type: {file_type}")

    def get_dated_output_path(self, file_type: str, extension: str, date_str: Optional[str] = None) -> Path:
        """
        Get a date-based output path with 'latest' naming convention.

        This creates paths like: output/audio/YYYYMMDD/latest.mp3

        If a 'latest' file already exists for today, it will be renamed to a timestamped
        version before the new file is created.

        Args:
            file_type: Type of file ('audio', 'data', 'logs')
            extension: File extension (e.g., 'mp3', 'txt', 'json')
            date_str: Optional date string in YYYYMMDD format (defaults to today)

        Returns:
            Path object for the latest file
        """
        from datetime import datetime
        import shutil

        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")

        # Get base directory for this file type
        base_path = Path(self._config.output.base_dir)
        if file_type == "audio":
            type_dir = base_path / self._config.output.audio_dir
        elif file_type == "data":
            type_dir = base_path / self._config.output.data_dir
        elif file_type == "logs":
            type_dir = base_path / self._config.output.logs_dir
        else:
            raise ValueError(f"Unknown file type: {file_type}")

        # Create date-based subdirectory
        date_dir = type_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        # Path for the latest file
        latest_file = date_dir / f"latest.{extension}"

        # If latest file exists, archive it with a timestamp
        if latest_file.exists():
            # Get modification time of existing file
            mtime = latest_file.stat().st_mtime
            time_mod = datetime.fromtimestamp(mtime).strftime("%H%M%S")
            archived_file = date_dir / f"{time_mod}.{extension}"

            # Rename existing latest to timestamped version
            shutil.move(str(latest_file), str(archived_file))
            logger.info(f"Archived existing file: {latest_file} -> {archived_file}")

        return latest_file

    def get_log_config_dict(self) -> Dict[str, Any]:
        """Get logging configuration as a dictionary for logging.dictConfig."""
        config_dict = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": self._config.logging.format,
                    "datefmt": self._config.logging.date_format,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": self._config.logging.level,
                    "formatter": "standard",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "": {  # root logger
                    "level": self._config.logging.level,
                    "handlers": ["console"],
                    "propagate": False,
                },
            },
        }

        # Add file handler if log file is specified
        if self._config.logging.log_file:
            log_path = self.get_output_path("logs", self._config.logging.log_file)
            config_dict["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": self._config.logging.level,
                "formatter": "standard",
                "filename": str(log_path),
                "maxBytes": self._config.logging.max_log_size,
                "backupCount": self._config.logging.backup_count,
            }
            config_dict["loggers"][""]["handlers"].append("file")

        return config_dict


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.config


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def initialize_config(config_file: Optional[str] = None) -> ConfigManager:
    """Initialize the global configuration."""
    global _config_manager
    _config_manager = ConfigManager(config_file)
    return _config_manager


if __name__ == "__main__":
    # Test configuration loading
    config_manager = ConfigManager()
    print("Configuration loaded successfully:")
    print(f"Environment: {config_manager.config.environment}")
    print(f"Debug: {config_manager.config.debug}")
    print(f"HN Max Stories: {config_manager.config.hackernews.max_stories}")
    print(f"Log Level: {config_manager.config.logging.level}")
