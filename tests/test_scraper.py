"""Tests for web scraper module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from bs4 import BeautifulSoup

from scraper import ArticleScraper, ScrapedContent, scrape_article


class TestScrapedContent:
    """Test ScrapedContent class."""

    def test_content_creation(self):
        """Test creating scraped content."""
        content = ScrapedContent(
            url="https://example.com",
            title="Test Title",
            content="This is test content with multiple words.",
            author="Test Author"
        )

        assert content.url == "https://example.com"
        assert content.title == "Test Title"
        assert content.author == "Test Author"
        assert content.word_count == 7  # Auto-calculated

    def test_content_word_count_calculation(self):
        """Test automatic word count calculation."""
        content = ScrapedContent(
            url="https://example.com",
            title="Test",
            content="One two three four five."
        )

        assert content.word_count == 5

    def test_content_to_dict(self):
        """Test converting content to dictionary."""
        content = ScrapedContent(
            url="https://example.com",
            title="Test",
            content="Test content",
            author="Author"
        )

        content_dict = content.to_dict()

        assert content_dict['url'] == "https://example.com"
        assert content_dict['title'] == "Test"
        assert content_dict['content'] == "Test content"
        assert content_dict['author'] == "Author"
        assert content_dict['word_count'] == 2


class TestArticleScraper:
    """Test ArticleScraper class."""

    def test_scraper_initialization(self, test_config):
        """Test scraper initialization."""
        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()

            assert scraper.config == test_config
            assert scraper.session is not None
            assert scraper.goose is not None

    def test_validate_url_valid(self, test_config):
        """Test URL validation with valid URL."""
        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()

            assert scraper._validate_url("https://example.com") is True
            assert scraper._validate_url("http://test.org/path") is True

    def test_validate_url_invalid(self, test_config):
        """Test URL validation with invalid URL."""
        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()

            assert scraper._validate_url("not-a-url") is False
            assert scraper._validate_url("") is False
            assert scraper._validate_url("ftp://example.com") is False  # No scheme validation

    @patch('scraper.requests.Session.get')
    def test_fetch_page_success(self, mock_get, test_config, mock_requests_response):
        """Test successful page fetching."""
        mock_get.return_value = mock_requests_response

        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()
            response = scraper._fetch_page("https://example.com")

            assert response == mock_requests_response
            mock_get.assert_called_once()

    @patch('scraper.requests.Session.get')
    def test_fetch_page_timeout(self, mock_get, test_config):
        """Test page fetching with timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()
            response = scraper._fetch_page("https://example.com")

            assert response is None

    @patch('scraper.requests.Session.get')
    def test_fetch_page_unsupported_content_type(self, mock_get, test_config):
        """Test page fetching with unsupported content type."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'application/pdf'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()
            response = scraper._fetch_page("https://example.com")

            assert response is None

    def test_extract_with_goose_success(self, test_config):
        """Test content extraction with Goose3."""
        # Mock Goose article
        mock_article = Mock()
        mock_article.cleaned_text = "This is extracted content from Goose3."
        mock_article.title = "Goose Title"
        mock_article.authors = ["Goose Author"]
        mock_article.publish_date = None
        mock_article.meta_description = "Goose description"

        mock_goose = Mock()
        mock_goose.extract.return_value = mock_article

        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()
            scraper.goose = mock_goose

            content = scraper._extract_with_goose("https://example.com")

            assert content is not None
            assert content.title == "Goose Title"
            assert content.content == "This is extracted content from Goose3."
            assert content.author == "Goose Author"
            assert content.scraping_method == "goose3"

    def test_extract_with_goose_no_content(self, test_config):
        """Test Goose3 extraction with no content."""
        mock_article = Mock()
        mock_article.cleaned_text = ""

        mock_goose = Mock()
        mock_goose.extract.return_value = mock_article

        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()
            scraper.goose = mock_goose

            content = scraper._extract_with_goose("https://example.com")

            assert content is None

    def test_extract_with_beautifulsoup_success(self, test_config):
        """Test content extraction with BeautifulSoup."""
        html_content = """
        <html>
        <head><title>Test Title</title></head>
        <body>
            <article>
                <h1>Article Title</h1>
                <p>This is the main content of the article.</p>
                <p>Another paragraph with more content.</p>
            </article>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.content = html_content.encode('utf-8')

        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()
            content = scraper._extract_with_beautifulsoup("https://example.com", mock_response)

            assert content is not None
            assert content.title == "Test Title"
            assert "Article Title" in content.content
            assert "main content" in content.content
            assert content.scraping_method == "beautifulsoup"

    def test_extract_with_beautifulsoup_no_content(self, test_config):
        """Test BeautifulSoup extraction with no content."""
        html_content = "<html><head><title>Empty</title></head><body></body></html>"

        mock_response = Mock()
        mock_response.content = html_content.encode('utf-8')

        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()
            content = scraper._extract_with_beautifulsoup("https://example.com", mock_response)

            assert content is None

    @patch('scraper.ArticleScraper._extract_with_goose')
    def test_scrape_article_goose_success(self, mock_extract_goose, test_config):
        """Test article scraping with successful Goose3 extraction."""
        mock_content = ScrapedContent(
            url="https://example.com",
            title="Test",
            content="Content with enough words to pass minimum threshold.",
            scraping_method="goose3"
        )
        mock_extract_goose.return_value = mock_content

        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()
            result = scraper.scrape_article("https://example.com")

            assert result == mock_content
            mock_extract_goose.assert_called_once_with("https://example.com")

    @patch('scraper.ArticleScraper._extract_with_beautifulsoup')
    @patch('scraper.ArticleScraper._fetch_page')
    @patch('scraper.ArticleScraper._extract_with_goose')
    def test_scrape_article_fallback_to_beautifulsoup(self, mock_goose, mock_fetch, mock_bs, test_config):
        """Test article scraping falling back to BeautifulSoup."""
        # Goose fails
        mock_goose.return_value = None

        # BeautifulSoup succeeds
        mock_content = ScrapedContent(
            url="https://example.com",
            title="Test",
            content="Content with enough words to pass minimum threshold.",
            scraping_method="beautifulsoup"
        )
        mock_bs.return_value = mock_content
        mock_fetch.return_value = Mock()  # Valid response

        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()
            result = scraper.scrape_article("https://example.com")

            assert result == mock_content
            mock_goose.assert_called_once()
            mock_fetch.assert_called_once()
            mock_bs.assert_called_once()

    def test_scrape_article_invalid_url(self, test_config):
        """Test scraping with invalid URL."""
        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()
            result = scraper.scrape_article("invalid-url")

            assert result is None

    @patch('scraper.ArticleScraper.scrape_article')
    def test_scrape_multiple_articles(self, mock_scrape_single, test_config):
        """Test scraping multiple articles."""
        urls = ["https://example1.com", "https://example2.com", "https://example3.com"]

        # Mock responses
        mock_content1 = ScrapedContent(url=urls[0], title="Title 1", content="Content 1")
        mock_content2 = ScrapedContent(url=urls[1], title="Title 2", content="Content 2")
        mock_scrape_single.side_effect = [mock_content1, mock_content2, None]  # Third fails

        with patch('scraper.get_config', return_value=test_config):
            with patch('time.sleep'):  # Skip actual sleep in tests
                scraper = ArticleScraper()
                results = scraper.scrape_multiple_articles(urls)

                assert len(results) == 2
                assert results[0] == mock_content1
                assert results[1] == mock_content2

    def test_cleanup(self, test_config):
        """Test scraper cleanup."""
        with patch('scraper.get_config', return_value=test_config):
            scraper = ArticleScraper()
            mock_goose = Mock()
            mock_session = Mock()
            scraper.goose = mock_goose
            scraper.session = mock_session

            scraper.cleanup()

            mock_goose.close.assert_called_once()
            mock_session.close.assert_called_once()


class TestLegacyFunctions:
    """Test legacy backward compatibility functions."""

    @patch('scraper.ArticleScraper')
    def test_scrape_article_legacy(self, mock_scraper_class):
        """Test legacy scrape_article function."""
        mock_content = ScrapedContent(
            url="https://example.com",
            title="Test",
            content="Test content"
        )
        mock_scraper = Mock()
        mock_scraper.scrape_article.return_value = mock_content
        mock_scraper_class.return_value = mock_scraper

        result = scrape_article("https://example.com")

        assert result == "Test content"
        mock_scraper.scrape_article.assert_called_once_with("https://example.com")
        mock_scraper.cleanup.assert_called_once()

    @patch('scraper.ArticleScraper')
    def test_scrape_article_legacy_failure(self, mock_scraper_class):
        """Test legacy scrape_article function with failure."""
        mock_scraper = Mock()
        mock_scraper.scrape_article.return_value = None
        mock_scraper_class.return_value = mock_scraper

        result = scrape_article("https://example.com")

        assert result is None
        mock_scraper.cleanup.assert_called_once()