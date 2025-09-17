"""Integration tests for the complete HackerCast pipeline."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from main import HackerCastPipeline
from hn_api import HackerNewsStory
from scraper import ScrapedContent


class TestHackerCastPipelineIntegration:
    """Integration tests for the HackerCast pipeline."""

    @pytest.fixture
    def mock_pipeline_components(self):
        """Mock all external dependencies for integration tests."""
        with patch('main.HackerNewsAPI') as mock_hn_api, \
             patch('main.ArticleScraper') as mock_scraper, \
             patch('main.TTSConverter') as mock_tts:

            # Mock HN API
            mock_hn_instance = Mock()
            mock_hn_api.return_value = mock_hn_instance

            # Mock scraper
            mock_scraper_instance = Mock()
            mock_scraper.return_value = mock_scraper_instance

            # Mock TTS
            mock_tts_instance = Mock()
            mock_tts.return_value = mock_tts_instance

            yield {
                'hn_api': mock_hn_instance,
                'scraper': mock_scraper_instance,
                'tts': mock_tts_instance
            }

    def test_pipeline_initialization(self, test_config):
        """Test pipeline initialization."""
        with patch('main.initialize_config') as mock_init_config:
            mock_config_manager = Mock()
            mock_config_manager.config = test_config
            mock_config_manager.get_log_config_dict.return_value = {
                'version': 1,
                'disable_existing_loggers': False,
                'formatters': {'standard': {'format': '%(message)s'}},
                'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'standard'}},
                'loggers': {'': {'level': 'INFO', 'handlers': ['console']}}
            }
            mock_init_config.return_value = mock_config_manager

            pipeline = HackerCastPipeline()

            assert pipeline.config == test_config
            assert pipeline.stories == []
            assert pipeline.scraped_content == []
            assert pipeline.audio_files == []

    def test_fetch_top_stories_success(self, mock_pipeline_components, test_config):
        """Test successful story fetching."""
        # Create mock stories
        mock_stories = [
            HackerNewsStory(
                id=12345,
                title="Test Story 1",
                url="https://example1.com",
                score=100,
                by="user1",
                time=1642608000,
                descendants=10
            ),
            HackerNewsStory(
                id=12346,
                title="Test Story 2",
                url="https://example2.com",
                score=200,
                by="user2",
                time=1642608100,
                descendants=20
            )
        ]

        mock_pipeline_components['hn_api'].get_top_stories.return_value = mock_stories

        with patch('main.initialize_config') as mock_init_config:
            mock_config_manager = Mock()
            mock_config_manager.config = test_config
            mock_init_config.return_value = mock_config_manager

            pipeline = HackerCastPipeline()
            pipeline.hn_api = mock_pipeline_components['hn_api']

            stories = pipeline.fetch_top_stories(2)

            assert len(stories) == 2
            assert stories[0].title == "Test Story 1"
            assert stories[1].title == "Test Story 2"
            assert pipeline.stories == mock_stories

    def test_fetch_top_stories_failure(self, mock_pipeline_components, test_config):
        """Test story fetching failure."""
        mock_pipeline_components['hn_api'].get_top_stories.return_value = []

        with patch('main.initialize_config') as mock_init_config:
            mock_config_manager = Mock()
            mock_config_manager.config = test_config
            mock_init_config.return_value = mock_config_manager

            pipeline = HackerCastPipeline()
            pipeline.hn_api = mock_pipeline_components['hn_api']

            stories = pipeline.fetch_top_stories(5)

            assert stories == []
            assert pipeline.stories == []

    def test_scrape_articles_success(self, mock_pipeline_components, test_config):
        """Test successful article scraping."""
        # Create mock stories with URLs
        mock_stories = [
            HackerNewsStory(
                id=12345,
                title="Test Story 1",
                url="https://example1.com",
                score=100,
                by="user1",
                time=1642608000,
                descendants=10
            ),
            HackerNewsStory(
                id=12346,
                title="Test Story 2",
                url="https://example2.com",
                score=200,
                by="user2",
                time=1642608100,
                descendants=20
            )
        ]

        # Create mock scraped content
        mock_content = [
            ScrapedContent(
                url="https://example1.com",
                title="Test Story 1",
                content="This is test content for story 1. " * 20,
                scraping_method="mock"
            ),
            ScrapedContent(
                url="https://example2.com",
                title="Test Story 2",
                content="This is test content for story 2. " * 25,
                scraping_method="mock"
            )
        ]

        mock_pipeline_components['scraper'].scrape_article.side_effect = mock_content

        with patch('main.initialize_config') as mock_init_config:
            mock_config_manager = Mock()
            mock_config_manager.config = test_config
            mock_init_config.return_value = mock_config_manager

            pipeline = HackerCastPipeline()
            pipeline.scraper = mock_pipeline_components['scraper']

            content = pipeline.scrape_articles(mock_stories)

            assert len(content) == 2
            assert content[0].title == "Test Story 1"
            assert content[1].title == "Test Story 2"
            assert pipeline.scraped_content == content

    def test_scrape_articles_no_urls(self, mock_pipeline_components, test_config):
        """Test scraping articles when stories have no URLs."""
        # Create mock stories without URLs
        mock_stories = [
            HackerNewsStory(
                id=12345,
                title="Ask HN: Question",
                url=None,  # No URL
                score=100,
                by="user1",
                time=1642608000,
                descendants=10
            )
        ]

        with patch('main.initialize_config') as mock_init_config:
            mock_config_manager = Mock()
            mock_config_manager.config = test_config
            mock_init_config.return_value = mock_config_manager

            pipeline = HackerCastPipeline()
            pipeline.scraper = mock_pipeline_components['scraper']

            content = pipeline.scrape_articles(mock_stories)

            assert content == []
            # Scraper should not be called since no URLs
            mock_pipeline_components['scraper'].scrape_article.assert_not_called()

    def test_generate_podcast_script(self, test_config):
        """Test podcast script generation."""
        mock_content = [
            ScrapedContent(
                url="https://example1.com",
                title="AI Breakthrough",
                content="Scientists have made a breakthrough in AI. This could revolutionize technology. The implications are vast.",
                scraping_method="mock"
            ),
            ScrapedContent(
                url="https://example2.com",
                title="Space Discovery",
                content="New planet discovered. It has unique properties. Could support life.",
                scraping_method="mock"
            )
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('main.initialize_config') as mock_init_config:
                mock_config_manager = Mock()
                mock_config_manager.config = test_config
                mock_config_manager.get_output_path.return_value = Path(temp_dir) / 'script.txt'
                mock_init_config.return_value = mock_config_manager

                pipeline = HackerCastPipeline()
                pipeline.config_manager = mock_config_manager
                script = pipeline.generate_podcast_script(mock_content)

                assert "Welcome to HackerCast" in script
                assert "AI Breakthrough" in script
                assert "Space Discovery" in script
                assert "Story 1:" in script
                assert "Story 2:" in script
                assert "Thank you for listening" in script

    def test_generate_podcast_script_empty_content(self, test_config):
        """Test script generation with empty content."""
        with patch('main.initialize_config') as mock_init_config:
            mock_config_manager = Mock()
            mock_config_manager.config = test_config
            mock_init_config.return_value = mock_config_manager

            pipeline = HackerCastPipeline()

            script = pipeline.generate_podcast_script([])

            assert script == ""

    def test_convert_to_audio_success(self, mock_pipeline_components, test_config):
        """Test successful audio conversion."""
        test_script = "Welcome to HackerCast. Today we have great stories."

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_file_path = Path(temp_dir) / 'test_audio.mp3'

            mock_pipeline_components['tts'].convert_text_to_speech.return_value = True

            with patch('main.initialize_config') as mock_init_config:
                mock_config_manager = Mock()
                mock_config_manager.config = test_config
                mock_config_manager.get_output_path.return_value = audio_file_path
                mock_init_config.return_value = mock_config_manager

                pipeline = HackerCastPipeline()
                pipeline.config_manager = mock_config_manager
                pipeline.tts_converter = mock_pipeline_components['tts']

                result_path = pipeline.convert_to_audio(test_script)

                assert result_path == audio_file_path
                assert audio_file_path in pipeline.audio_files
                mock_pipeline_components['tts'].convert_text_to_speech.assert_called_once()

    def test_convert_to_audio_failure(self, mock_pipeline_components, test_config):
        """Test audio conversion failure."""
        test_script = "Test script"

        mock_pipeline_components['tts'].convert_text_to_speech.return_value = False

        with patch('main.initialize_config') as mock_init_config:
            mock_config_manager = Mock()
            mock_config_manager.config = test_config
            mock_config_manager.get_output_path.return_value = Path('/tmp/test.mp3')
            mock_init_config.return_value = mock_config_manager

            pipeline = HackerCastPipeline()
            pipeline.config_manager = mock_config_manager
            pipeline.tts_converter = mock_pipeline_components['tts']

            result_path = pipeline.convert_to_audio(test_script)

            assert result_path is None
            assert len(pipeline.audio_files) == 0

    def test_convert_to_audio_empty_script(self, test_config):
        """Test audio conversion with empty script."""
        with patch('main.initialize_config') as mock_init_config:
            mock_config_manager = Mock()
            mock_config_manager.config = test_config
            mock_init_config.return_value = mock_config_manager

            pipeline = HackerCastPipeline()

            result_path = pipeline.convert_to_audio("")

            assert result_path is None

    def test_save_pipeline_data(self, test_config):
        """Test saving pipeline data to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_file_path = Path(temp_dir) / 'pipeline_data.json'

            with patch('main.initialize_config') as mock_init_config:
                mock_config_manager = Mock()
                mock_config_manager.config = test_config
                mock_config_manager.get_output_path.return_value = data_file_path
                mock_init_config.return_value = mock_config_manager

                pipeline = HackerCastPipeline()
                pipeline.config_manager = mock_config_manager

                # Set up some test data
                pipeline.stories = [
                    HackerNewsStory(
                        id=12345,
                        title="Test Story",
                        url="https://example.com",
                        score=100,
                        by="user",
                        time=1642608000,
                        descendants=10
                    )
                ]
                pipeline.scraped_content = [
                    ScrapedContent(
                        url="https://example.com",
                        title="Test Story",
                        content="Test content",
                        scraping_method="mock"
                    )
                ]
                pipeline.audio_files = [Path('/tmp/audio.mp3')]

                result_path = pipeline.save_pipeline_data()

                assert result_path == data_file_path
                assert data_file_path.exists()

                # Verify the saved data
                with open(data_file_path, 'r') as f:
                    saved_data = json.load(f)

                assert 'timestamp' in saved_data
                assert 'stories' in saved_data
                assert 'scraped_content' in saved_data
                assert 'audio_files' in saved_data
                assert 'stats' in saved_data
                assert len(saved_data['stories']) == 1
                assert len(saved_data['scraped_content']) == 1

    def test_run_full_pipeline_success(self, mock_pipeline_components, test_config):
        """Test complete successful pipeline execution."""
        # Mock stories
        mock_stories = [
            HackerNewsStory(
                id=12345,
                title="Test Story",
                url="https://example.com",
                score=100,
                by="user",
                time=1642608000,
                descendants=10
            )
        ]

        # Mock content
        mock_content = [
            ScrapedContent(
                url="https://example.com",
                title="Test Story",
                content="This is test content. " * 30,
                scraping_method="mock"
            )
        ]

        # Configure mocks
        mock_pipeline_components['hn_api'].get_top_stories.return_value = mock_stories
        mock_pipeline_components['scraper'].scrape_article.return_value = mock_content[0]
        mock_pipeline_components['tts'].convert_text_to_speech.return_value = True

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('main.initialize_config') as mock_init_config:
                mock_config_manager = Mock()
                mock_config_manager.config = test_config
                mock_config_manager.get_output_path.side_effect = lambda file_type, filename: Path(temp_dir) / filename
                mock_init_config.return_value = mock_config_manager

                pipeline = HackerCastPipeline()
                pipeline.config_manager = mock_config_manager
                pipeline.hn_api = mock_pipeline_components['hn_api']
                pipeline.scraper = mock_pipeline_components['scraper']
                pipeline.tts_converter = mock_pipeline_components['tts']

                result = pipeline.run_full_pipeline(1)

                assert result['success'] is True
                assert result['stories_count'] == 1
                assert result['scraped_count'] == 1
                assert result['script_length'] > 0
                assert result['audio_file'] is not None
                assert result['data_file'] is not None
                assert 'runtime' in result

    def test_run_full_pipeline_no_stories(self, mock_pipeline_components, test_config):
        """Test pipeline execution when no stories are fetched."""
        mock_pipeline_components['hn_api'].get_top_stories.return_value = []

        with patch('main.initialize_config') as mock_init_config:
            mock_config_manager = Mock()
            mock_config_manager.config = test_config
            mock_init_config.return_value = mock_config_manager

            pipeline = HackerCastPipeline()
            pipeline.config_manager = mock_config_manager
            pipeline.hn_api = mock_pipeline_components['hn_api']

            result = pipeline.run_full_pipeline(5)

            assert result['success'] is False
            assert 'No stories fetched' in result['error']

    def test_run_full_pipeline_no_content(self, mock_pipeline_components, test_config):
        """Test pipeline execution when no content is scraped."""
        # Mock stories but no scraped content
        mock_stories = [
            HackerNewsStory(
                id=12345,
                title="Test Story",
                url="https://example.com",
                score=100,
                by="user",
                time=1642608000,
                descendants=10
            )
        ]

        mock_pipeline_components['hn_api'].get_top_stories.return_value = mock_stories
        mock_pipeline_components['scraper'].scrape_article.return_value = None

        with patch('main.initialize_config') as mock_init_config:
            mock_config_manager = Mock()
            mock_config_manager.config = test_config
            mock_init_config.return_value = mock_config_manager

            pipeline = HackerCastPipeline()
            pipeline.config_manager = mock_config_manager
            pipeline.hn_api = mock_pipeline_components['hn_api']
            pipeline.scraper = mock_pipeline_components['scraper']

            result = pipeline.run_full_pipeline(1)

            assert result['success'] is False
            assert 'No articles scraped' in result['error']

    def test_pipeline_cleanup(self, mock_pipeline_components, test_config):
        """Test pipeline cleanup."""
        with patch('main.initialize_config') as mock_init_config:
            mock_config_manager = Mock()
            mock_config_manager.config = test_config
            mock_init_config.return_value = mock_config_manager

            pipeline = HackerCastPipeline()
            pipeline.scraper = mock_pipeline_components['scraper']

            pipeline.cleanup()

            mock_pipeline_components['scraper'].cleanup.assert_called_once()