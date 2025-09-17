#!/usr/bin/env python

import logging
import re
import sys
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from goose3 import Goose

from config import get_config

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ScrapedContent:
    """Represents scraped content from a web page."""

    url: str
    title: str
    content: str
    author: Optional[str] = None
    published_date: Optional[str] = None
    meta_description: Optional[str] = None
    word_count: int = 0
    scraping_method: str = "unknown"

    def __post_init__(self):
        """Calculate word count after initialization."""
        if self.content:
            self.word_count = len(self.content.split())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "published_date": self.published_date,
            "meta_description": self.meta_description,
            "word_count": self.word_count,
            "scraping_method": self.scraping_method,
        }


class ArticleScraper:
    """Enhanced web scraper with multiple extraction strategies and fallbacks."""

    def __init__(self):
        """Initialize the scraper with configuration."""
        self.config = get_config()

        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.config.scraping.retry_attempts,
            backoff_factor=self.config.scraping.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set headers
        self.session.headers.update(
            {
                "User-Agent": self.config.scraping.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
        )

        # Initialize Goose for content extraction
        self.goose = Goose()

        logger.info("Initialized article scraper")

    def _validate_url(self, url: str) -> bool:
        """
        Validate URL format.

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _fetch_page(self, url: str) -> Optional[requests.Response]:
        """
        Fetch a web page with error handling.

        Args:
            url: URL to fetch

        Returns:
            Response object or None if failed
        """
        try:
            logger.debug(f"Fetching page: {url}")

            response = self.session.get(
                url, timeout=self.config.scraping.timeout, stream=True
            )
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            if not any(
                allowed_type in content_type
                for allowed_type in self.config.scraping.allowed_content_types
            ):
                logger.warning(f"Unsupported content type: {content_type}")
                return None

            # Check content length
            content_length = response.headers.get("content-length")
            if (
                content_length
                and int(content_length) > self.config.scraping.max_content_length
            ):
                logger.warning(f"Content too large: {content_length} bytes")
                return None

            logger.debug(f"Successfully fetched page: {url}")
            return response

        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error for {url}: {e}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for {url}: {e}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    def _extract_with_goose(self, url: str) -> Optional[ScrapedContent]:
        """
        Extract content using Goose3 library.

        Args:
            url: URL to scrape

        Returns:
            ScrapedContent or None if failed
        """
        try:
            logger.debug(f"Extracting content with Goose: {url}")
            article = self.goose.extract(url)

            if not article.cleaned_text:
                logger.warning(f"Goose extracted no content from: {url}")
                return None

            content = ScrapedContent(
                url=url,
                title=article.title or "No Title",
                content=article.cleaned_text,
                author=article.authors[0] if article.authors else None,
                published_date=(
                    article.publish_date.isoformat() if article.publish_date else None
                ),
                meta_description=article.meta_description,
                scraping_method="goose3",
            )

            logger.debug(f"Goose extracted {content.word_count} words")
            return content

        except Exception as e:
            logger.error(f"Goose extraction failed for {url}: {e}")
            return None

    def _extract_with_beautifulsoup(
        self, url: str, response: requests.Response
    ) -> Optional[ScrapedContent]:
        """
        Extract content using BeautifulSoup as fallback.

        Args:
            url: URL being scraped
            response: HTTP response object

        Returns:
            ScrapedContent or None if failed
        """
        try:
            logger.debug(f"Extracting content with BeautifulSoup: {url}")
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract title
            title_tag = soup.find("title")
            title = title_tag.get_text().strip() if title_tag else "No Title"

            # Extract meta description
            meta_desc_tag = soup.find("meta", attrs={"name": "description"})
            meta_description = meta_desc_tag.get("content") if meta_desc_tag else None

            # Extract author
            author = None
            author_tag = soup.find("meta", attrs={"name": "author"})
            if author_tag:
                author = author_tag.get("content")

            # Remove unwanted elements
            for element in soup(
                ["script", "style", "nav", "header", "footer", "aside", "form"]
            ):
                element.decompose()

            # Try to find main content area
            content_selectors = [
                "article",
                '[role="main"]',
                ".content",
                ".post-content",
                ".entry-content",
                ".article-content",
                "main",
                ".main",
            ]

            content_element = None
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    break

            # Fallback to body if no content area found
            if not content_element:
                content_element = soup.find("body")

            if not content_element:
                logger.warning(f"No content element found for: {url}")
                return None

            # Extract and clean text
            text = content_element.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            cleaned_text = "\n".join(chunk for chunk in chunks if chunk)

            # Remove excessive whitespace
            cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

            if not cleaned_text.strip():
                logger.warning(f"No text content extracted from: {url}")
                return None

            content = ScrapedContent(
                url=url,
                title=title,
                content=cleaned_text,
                author=author,
                meta_description=meta_description,
                scraping_method="beautifulsoup",
            )

            logger.debug(f"BeautifulSoup extracted {content.word_count} words")
            return content

        except Exception as e:
            logger.error(f"BeautifulSoup extraction failed for {url}: {e}")
            return None

    def scrape_article(self, url: str) -> Optional[ScrapedContent]:
        """
        Scrape article content from a URL using multiple strategies.

        Args:
            url: URL to scrape

        Returns:
            ScrapedContent or None if failed
        """
        if not self._validate_url(url):
            logger.error(f"Invalid URL: {url}")
            return None

        logger.info(f"Scraping article: {url}")

        # Strategy 1: Try Goose3 first (most sophisticated)
        content = self._extract_with_goose(url)
        if content and content.word_count > 50:  # Minimum viable content
            logger.info(f"Successfully scraped with Goose: {content.word_count} words")
            return content

        # Strategy 2: Fallback to BeautifulSoup
        response = self._fetch_page(url)
        if response:
            content = self._extract_with_beautifulsoup(url, response)
            if content and content.word_count > 50:
                logger.info(
                    f"Successfully scraped with BeautifulSoup: {content.word_count} words"
                )
                return content

        logger.error(f"Failed to scrape content from: {url}")
        return None

    def scrape_multiple_articles(self, urls: List[str]) -> List[ScrapedContent]:
        """
        Scrape multiple articles with progress logging.

        Args:
            urls: List of URLs to scrape

        Returns:
            List of successfully scraped content
        """
        results = []
        failed_count = 0

        logger.info(f"Scraping {len(urls)} articles")

        for i, url in enumerate(urls, 1):
            try:
                content = self.scrape_article(url)
                if content:
                    results.append(content)
                    logger.debug(f"Progress: {i}/{len(urls)} - {content.title}")
                else:
                    failed_count += 1
                    logger.warning(f"Failed to scrape: {url}")

                # Rate limiting - be respectful
                if i < len(urls):
                    time.sleep(1.0)

            except Exception as e:
                failed_count += 1
                logger.error(f"Error scraping {url}: {e}")

        logger.info(
            f"Scraped {len(results)} articles successfully, {failed_count} failed"
        )
        return results

    def cleanup(self):
        """Clean up resources."""
        self.goose.close()
        self.session.close()


def scrape_article(url: str) -> Optional[str]:
    """
    Legacy function for backward compatibility.

    Args:
        url: URL to scrape

    Returns:
        Scraped text or None if failed
    """
    scraper = ArticleScraper()
    try:
        content = scraper.scrape_article(url)
        return content.content if content else None
    finally:
        scraper.cleanup()


def main():
    """Command-line interface for the scraper."""
    if len(sys.argv) != 2:
        print("Usage: python scraper.py <URL>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]

    try:
        scraper = ArticleScraper()
        content = scraper.scrape_article(url)

        if content:
            print(f"Title: {content.title}")
            print(f"Author: {content.author or 'Unknown'}")
            print(f"Word Count: {content.word_count}")
            print(f"Method: {content.scraping_method}")
            print("=" * 50)
            print(content.content)
        else:
            print("Failed to scrape article content", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if "scraper" in locals():
            scraper.cleanup()


if __name__ == "__main__":
    main()
