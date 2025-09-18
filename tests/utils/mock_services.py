"""Mock services for external APIs and dependencies."""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, MagicMock
import requests
import tempfile

from hn_api import HackerNewsStory
from scraper import ScrapedContent
from .test_helpers import TemporaryTestEnvironment


class MockHackerNewsAPI:
    """Mock Hacker News API for testing."""

    def __init__(self):
        self.mock_stories = self._generate_mock_stories()
        self.request_count = 0
        self.should_fail = False
        self.delay_seconds = 0

    def _generate_mock_stories(self) -> List[Dict[str, Any]]:
        """Generate realistic mock story data."""
        base_time = int(time.time())
        stories = []

        mock_data = [
            {
                "id": 40001,
                "title": "Revolutionary AI Framework Achieves Human-Level Performance",
                "by": "techpioneer",
                "score": 1250,
                "url": "https://example.com/ai-framework-breakthrough",
                "type": "story",
                "time": base_time - 1800,
            },
            {
                "id": 40002,
                "title": "New Programming Language Promises 10x Performance Gains",
                "by": "langdev",
                "score": 980,
                "url": "https://example.com/new-programming-language",
                "type": "story",
                "time": base_time - 3600,
            },
            {
                "id": 40003,
                "title": "Quantum Computing Breakthrough: 1000-Qubit Processor Unveiled",
                "by": "quantumresearcher",
                "score": 1500,
                "url": "https://example.com/quantum-breakthrough",
                "type": "story",
                "time": base_time - 5400,
            },
            {
                "id": 40004,
                "title": "Open Source Security Tool Prevents 99% of Cyber Attacks",
                "by": "securityexpert",
                "score": 750,
                "url": "https://example.com/security-tool",
                "type": "story",
                "time": base_time - 7200,
            },
            {
                "id": 40005,
                "title": "Startup Disrupts Cloud Computing with Edge-First Architecture",
                "by": "cloudstartup",
                "score": 650,
                "url": "https://example.com/edge-computing",
                "type": "story",
                "time": base_time - 9000,
            },
            {
                "id": 40006,
                "title": "Machine Learning Model Predicts Software Bugs with 95% Accuracy",
                "by": "mlresearcher",
                "score": 820,
                "url": "https://example.com/ml-bug-prediction",
                "type": "story",
                "time": base_time - 10800,
            },
            {
                "id": 40007,
                "title": "Blockchain Technology Revolutionizes Supply Chain Management",
                "by": "blockchaindev",
                "score": 590,
                "url": "https://example.com/blockchain-supply-chain",
                "type": "story",
                "time": base_time - 12600,
            },
            {
                "id": 40008,
                "title": "Developer Tools Company Raises $100M Series B",
                "by": "vcnews",
                "score": 420,
                "url": "https://example.com/developer-tools-funding",
                "type": "story",
                "time": base_time - 14400,
            },
            {
                "id": 40009,
                "title": "WebAssembly Runtime Achieves Native Performance in Browsers",
                "by": "wasmdev",
                "score": 380,
                "url": "https://example.com/wasm-performance",
                "type": "story",
                "time": base_time - 16200,
            },
            {
                "id": 40010,
                "title": "Database Innovation: New Storage Engine Reduces Latency by 50%",
                "by": "dbarchitect",
                "score": 710,
                "url": "https://example.com/database-innovation",
                "type": "story",
                "time": base_time - 18000,
            },
        ]

        return mock_data

    def mock_requests_get(self, url: str, **kwargs) -> Mock:
        """Mock requests.get for HN API calls."""
        self.request_count += 1

        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        if self.should_fail:
            raise requests.exceptions.RequestException("Simulated network failure")

        response = Mock()
        response.status_code = 200
        response.raise_for_status = Mock()

        if "topstories" in url:
            # Return list of story IDs
            story_ids = [story["id"] for story in self.mock_stories]
            response.json.return_value = story_ids
        elif "item" in url:
            # Extract story ID from URL
            story_id = int(url.split("/")[-1].replace(".json", ""))
            story_data = next(
                (s for s in self.mock_stories if s["id"] == story_id), None
            )
            if story_data:
                response.json.return_value = story_data
            else:
                response.status_code = 404
                response.json.return_value = None

        return response

    def set_failure_mode(self, should_fail: bool = True):
        """Enable/disable failure simulation."""
        self.should_fail = should_fail

    def set_delay(self, seconds: float):
        """Set artificial delay for requests."""
        self.delay_seconds = seconds

    def get_request_count(self) -> int:
        """Get number of requests made."""
        return self.request_count


class MockArticleScraper:
    """Mock article scraper for testing."""

    def __init__(self):
        self.scraped_articles = self._generate_mock_articles()
        self.should_fail = False
        self.failure_rate = 0.0  # 0.0 = no failures, 1.0 = all failures

    def _generate_mock_articles(self) -> Dict[str, ScrapedContent]:
        """Generate mock scraped content."""
        articles = {}

        mock_content_data = [
            {
                "url": "https://example.com/ai-framework-breakthrough",
                "title": "Revolutionary AI Framework Achieves Human-Level Performance",
                "content": """
                Researchers at TechCorp have unveiled a groundbreaking artificial intelligence framework
                that has achieved human-level performance across multiple cognitive tasks. The new system,
                called CogniAI, represents a significant leap forward in machine learning capabilities.

                The framework combines advanced neural network architectures with novel training
                methodologies to achieve unprecedented results. In benchmark tests, CogniAI scored
                within 2% of human performance on complex reasoning tasks, visual recognition challenges,
                and natural language understanding assessments.

                "This represents a paradigm shift in how we approach artificial intelligence," said
                Dr. Sarah Chen, lead researcher on the project. "We're not just improving existing
                models; we're fundamentally reimagining how machines can think and learn."

                The implications for industries ranging from healthcare to autonomous vehicles are
                enormous. Early adopters in the medical field have already begun integrating CogniAI
                into diagnostic systems, with preliminary results showing 95% accuracy in detecting
                rare diseases from medical imaging.
                """,
                "author": "Tech Reporter",
                "word_count": 150,
            },
            {
                "url": "https://example.com/new-programming-language",
                "title": "New Programming Language Promises 10x Performance Gains",
                "content": """
                A team of compiler engineers has introduced Velocity, a new systems programming language
                that claims to deliver performance improvements of up to 10x over traditional languages
                while maintaining memory safety and developer productivity.

                Velocity combines the performance characteristics of C++ with the safety guarantees of
                Rust, using innovative static analysis techniques to eliminate common programming errors
                at compile time. The language introduces a unique ownership model that allows for
                zero-cost abstractions without sacrificing safety.

                Early benchmarks show impressive results across various computational tasks. Sorting
                algorithms implemented in Velocity run 8.5x faster than equivalent Python code and
                2.3x faster than optimized C++ implementations. Memory usage is also significantly
                reduced, with some applications showing 40% lower memory footprint.

                Major technology companies are already expressing interest in adopting Velocity for
                performance-critical applications. The language's standard library includes built-in
                support for parallel processing, making it ideal for modern multi-core architectures.
                """,
                "author": "Language Design Team",
                "word_count": 165,
            },
            {
                "url": "https://example.com/quantum-breakthrough",
                "title": "Quantum Computing Breakthrough: 1000-Qubit Processor Unveiled",
                "content": """
                QuantumTech Industries has achieved a major milestone in quantum computing with the
                unveiling of their 1000-qubit quantum processor, marking the largest operational
                quantum computer ever built. This achievement brings practical quantum computing
                applications significantly closer to reality.

                The new processor, dubbed QuantumForce-1000, utilizes advanced error correction
                techniques to maintain quantum coherence across all 1000 qubits simultaneously.
                This represents a 5x increase in qubit count compared to the previous industry
                leader and opens up possibilities for solving previously intractable problems.

                Potential applications include drug discovery, financial modeling, and optimization
                problems that are currently beyond the reach of classical computers. The system
                has already demonstrated quantum advantage in specific algorithmic tasks, completing
                calculations in minutes that would take classical supercomputers thousands of years.

                "We're entering a new era of computation," explained Dr. Michael Rodriguez, Chief
                Quantum Scientist at QuantumTech. "This isn't just an incremental improvement;
                it's a fundamental shift in what's computationally possible."
                """,
                "author": "Quantum Physics Reporter",
                "word_count": 175,
            },
        ]

        for article_data in mock_content_data:
            content = ScrapedContent(
                url=article_data["url"],
                title=article_data["title"],
                content=article_data["content"].strip(),
                author=article_data["author"],
                published_date=None,
                scraping_method="mock",
            )
            articles[article_data["url"]] = content

        return articles

    def mock_scrape_article(self, url: str) -> Optional[ScrapedContent]:
        """Mock article scraping."""
        import random

        if self.should_fail or random.random() < self.failure_rate:
            return None

        if url in self.scraped_articles:
            return self.scraped_articles[url]

        # Generate generic content for unknown URLs
        return ScrapedContent(
            url=url,
            title="Generic Test Article",
            content="This is generic test content for URL: " + url + ". " * 50,
            author="Test Author",
            published_date=None,
            scraping_method="mock",
        )

    def set_failure_mode(self, should_fail: bool = True, failure_rate: float = 0.0):
        """Set failure simulation parameters."""
        self.should_fail = should_fail
        self.failure_rate = max(0.0, min(1.0, failure_rate))


class MockTTSConverter:
    """Mock TTS converter for testing."""

    def __init__(self):
        self.conversion_count = 0
        self.should_fail = False
        self.generated_files = []

    def mock_convert_text_to_speech(
        self,
        text: str,
        output_file: str,
        language_code: str = "en-US",
        voice_name: str = "en-US-Standard-A",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bool:
        """Mock TTS conversion."""
        self.conversion_count += 1

        if self.should_fail:
            return False

        # Create a dummy audio file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write minimal MP3-like header and some data
        with open(output_path, "wb") as f:
            # Write a minimal fake MP3 header
            f.write(b"ID3\x03\x00\x00\x00")
            f.write(b"\x00" * 100)  # Padding
            f.write(f"Mock TTS audio for: {text[:50]}...".encode("utf-8"))
            f.write(b"\x00" * 1000)  # More padding to make it look like audio

        self.generated_files.append(output_path)
        return True

    def set_failure_mode(self, should_fail: bool = True):
        """Enable/disable failure simulation."""
        self.should_fail = should_fail

    def get_conversion_count(self) -> int:
        """Get number of conversions performed."""
        return self.conversion_count

    def cleanup_generated_files(self):
        """Clean up generated test files."""
        for file_path in self.generated_files:
            if file_path.exists():
                file_path.unlink()
        self.generated_files.clear()


class MockNetworkConditions:
    """Simulate various network conditions for testing."""

    def __init__(self):
        self.latency_ms = 0
        self.packet_loss_rate = 0.0
        self.bandwidth_limit_kbps = None

    def set_latency(self, milliseconds: int):
        """Set network latency simulation."""
        self.latency_ms = milliseconds

    def set_packet_loss(self, loss_rate: float):
        """Set packet loss rate (0.0 to 1.0)."""
        self.packet_loss_rate = max(0.0, min(1.0, loss_rate))

    def set_bandwidth_limit(self, kbps: Optional[int]):
        """Set bandwidth limit in Kbps."""
        self.bandwidth_limit_kbps = kbps

    def apply_to_request(self, original_function):
        """Apply network conditions to a request function."""

        def wrapper(*args, **kwargs):
            import random

            # Simulate packet loss
            if random.random() < self.packet_loss_rate:
                raise requests.exceptions.ConnectionError("Simulated packet loss")

            # Simulate latency
            if self.latency_ms > 0:
                time.sleep(self.latency_ms / 1000.0)

            # Call original function
            return original_function(*args, **kwargs)

        return wrapper


def create_test_config_file(temp_dir: Path) -> Path:
    """Create a test configuration file."""
    config_content = {
        "environment": "test",
        "debug": True,
        "hackernews": {
            "api_base_url": "https://hacker-news.firebaseio.com/v0",
            "max_stories": 10,
            "request_timeout": 30,
        },
        "scraping": {
            "request_timeout": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "user_agent": "HackerCast-Test/1.0",
        },
        "tts": {
            "enabled": False,  # Disable for most tests
            "language_code": "en-US",
            "voice_name": "en-US-Standard-A",
            "speaking_rate": 1.0,
            "pitch": 0.0,
        },
        "output": {
            "base_directory": str(temp_dir),
            "data_subdir": "data",
            "audio_subdir": "audio",
            "logs_subdir": "logs",
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file_enabled": True,
        },
    }

    config_file = temp_dir / "test_config.json"
    with open(config_file, "w") as f:
        json.dump(config_content, f, indent=2)

    return config_file


class E2ETestContext:
    """Context manager for E2E test setup and teardown."""

    def __init__(self):
        self.temp_env = TemporaryTestEnvironment()
        self.mock_hn_api = MockHackerNewsAPI()
        self.mock_scraper = MockArticleScraper()
        self.mock_tts = MockTTSConverter()
        self.mock_network = MockNetworkConditions()
        self.config_file = None
        self.patches = []

    def __enter__(self):
        """Setup test context."""
        self.temp_dir = self.temp_env.__enter__()
        self.config_file = create_test_config_file(self.temp_dir)

        # Setup patches
        from unittest.mock import patch

        self.patches = [
            patch("requests.Session.get", side_effect=self.mock_hn_api.mock_requests_get),
            patch(
                "scraper.ArticleScraper.scrape_article",
                side_effect=self.mock_scraper.mock_scrape_article,
            ),
            patch(
                "tts_converter.TTSConverter.convert_text_to_speech",
                side_effect=self.mock_tts.mock_convert_text_to_speech,
            ),
        ]

        for p in self.patches:
            p.__enter__()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test context."""
        # Stop patches
        for p in reversed(self.patches):
            p.__exit__(exc_type, exc_val, exc_tb)

        # Cleanup mock files
        self.mock_tts.cleanup_generated_files()

        # Cleanup temp environment
        self.temp_env.__exit__(exc_type, exc_val, exc_tb)

    @property
    def output_dir(self) -> Path:
        """Get test output directory."""
        return self.temp_dir
