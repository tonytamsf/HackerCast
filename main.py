#!/usr/bin/env python

import json
import logging
import logging.config
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import click
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.logging import RichHandler

from config import initialize_config, get_config_manager
from hn_api import HackerNewsAPI, HackerNewsStory
from scraper import ArticleScraper, ScrapedContent
from tts_converter import TTSConverter
from interactive_selector import InteractiveStorySelector
from podcast_publisher import PodcastPublisher, PodcastPublisherConfig
from podcast_chapters import create_chapter_file

# Initialize rich console
console = Console()

# Global application state
app_start_time = datetime.now()


class HackerCastPipeline:
    """Main orchestrator for the HackerCast pipeline."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the HackerCast pipeline.

        Args:
            config_file: Optional path to configuration file
        """
        # Initialize configuration
        self.config_manager = initialize_config(config_file)
        self.config = self.config_manager.config

        # Setup logging
        self._setup_logging()

        # Initialize components
        self.hn_api = HackerNewsAPI()
        self.scraper = ArticleScraper()
        self.tts_converter = None  # Initialize when needed
        self.podcast_publisher = None  # Initialize when needed

        self.logger = logging.getLogger(__name__)
        self.logger.info("HackerCast pipeline initialized")

        # Pipeline state
        self.stories: List[HackerNewsStory] = []
        self.scraped_content: List[ScrapedContent] = []
        self.audio_files: List[Path] = []
        self.chapters: List[Dict[str, Any]] = []
        self.chapter_file: Optional[Path] = None

    def _setup_logging(self):
        """Configure logging based on configuration."""
        log_config = self.config_manager.get_log_config_dict()
        logging.config.dictConfig(log_config)

        # Add rich handler for console output if in debug mode
        if self.config.debug:
            rich_handler = RichHandler(console=console)
            rich_handler.setLevel(logging.DEBUG)
            logging.getLogger().addHandler(rich_handler)

    def _initialize_tts(self):
        """Initialize TTS converter when needed."""
        if self.tts_converter is None:
            try:
                self.tts_converter = TTSConverter(
                    credentials_path=self.config.google_credentials_path
                )
                self.logger.info("TTS converter initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize TTS converter: {e}")
                raise

    def _initialize_publisher(self):
        """Initialize podcast publisher when needed."""
        if self.podcast_publisher is None:
            try:
                publisher_config = PodcastPublisherConfig(
                    self.config.podcast_publishing.__dict__ if hasattr(self.config, 'podcast_publishing') else {}
                )
                self.podcast_publisher = PodcastPublisher(
                    api_key=publisher_config.api_key,
                    base_url=publisher_config.base_url
                )
                self.logger.info("Podcast publisher initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize podcast publisher: {e}")
                raise

    def fetch_top_stories(self, limit: Optional[int] = None) -> List[HackerNewsStory]:
        """
        Fetch top stories from Hacker News.

        Args:
            limit: Number of stories to fetch

        Returns:
            List of HackerNewsStory objects
        """
        if limit is None:
            limit = self.config.hackernews.max_stories

        console.print(
            f"[bold blue]Fetching top {limit} stories from Hacker News...[/bold blue]"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching stories...", total=None)

            try:
                self.stories = self.hn_api.get_top_stories(limit)

                if not self.stories:
                    console.print("[red]No stories fetched![/red]")
                    return []

                progress.update(
                    task, description=f"Fetched {len(self.stories)} stories"
                )

                # Display stories table
                table = Table(title="Top Hacker News Stories")
                table.add_column("ID", style="cyan")
                table.add_column("Title", style="white", max_width=50)
                table.add_column("Score", justify="right", style="green")
                table.add_column("Author", style="yellow")
                table.add_column("URL", style="blue", max_width=30)

                for story in self.stories[:10]:  # Show first 10
                    table.add_row(
                        str(story.id),
                        story.title,
                        str(story.score),
                        story.by,
                        (
                            story.url[:30] + "..."
                            if story.url and len(story.url) > 30
                            else story.url or "N/A"
                        ),
                    )

                console.print(table)
                self.logger.info(f"Successfully fetched {len(self.stories)} stories")

                return self.stories

            except Exception as e:
                console.print(f"[red]Error fetching stories: {e}[/red]")
                self.logger.error(f"Error fetching stories: {e}")
                return []

    def select_stories_interactively(self, stories: Optional[List[HackerNewsStory]] = None) -> List[HackerNewsStory]:
        """
        Interactive story selection interface.

        Args:
            stories: List of stories to select from (uses self.stories if None)

        Returns:
            List of selected HackerNewsStory objects
        """
        if stories is None:
            stories = self.stories

        # Validate input
        if not isinstance(stories, list):
            console.print("[red]Invalid stories data type[/red]")
            self.logger.error("Stories parameter is not a list")
            return []

        if not stories:
            console.print("[red]No stories available for selection![/red]")
            return []

        # Validate story objects
        valid_stories = []
        for story in stories:
            try:
                # Check required attributes
                if hasattr(story, 'id') and hasattr(story, 'title') and hasattr(story, 'score'):
                    valid_stories.append(story)
                else:
                    self.logger.warning(f"Invalid story object: missing required attributes")
            except Exception as e:
                self.logger.warning(f"Error validating story: {e}")

        if not valid_stories:
            console.print("[red]No valid stories found for selection![/red]")
            return []

        if len(valid_stories) < len(stories):
            skipped = len(stories) - len(valid_stories)
            console.print(f"[yellow]Skipped {skipped} invalid stories[/yellow]")

        console.print(
            f"[bold blue]Interactive story selection ({len(valid_stories)} stories available)[/bold blue]"
        )

        try:
            selector = InteractiveStorySelector(console=console)
            selected_stories = selector.select_stories(valid_stories)

            if selected_stories:
                console.print(
                    f"[green]Selected {len(selected_stories)} stories for processing[/green]"
                )
                self.logger.info(f"User selected {len(selected_stories)} out of {len(valid_stories)} stories")

                # Validate selected stories
                validated_selected = self._validate_selected_stories(selected_stories)
                if len(validated_selected) < len(selected_stories):
                    rejected = len(selected_stories) - len(validated_selected)
                    console.print(f"[yellow]Warning: {rejected} selected stories failed validation[/yellow]")

                return validated_selected
            else:
                console.print("[yellow]No stories selected[/yellow]")
                self.logger.info("User cancelled story selection or selected no stories")
                return []

        except KeyboardInterrupt:
            console.print("\n[yellow]Selection interrupted by user[/yellow]")
            self.logger.info("Interactive selection interrupted by user")
            return []
        except Exception as e:
            console.print(f"[red]Error in interactive selection: {e}[/red]")
            self.logger.error(f"Error in interactive selection: {e}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")

            # Ask user if they want to proceed with all stories or cancel
            from rich.prompt import Confirm
            try:
                fallback = Confirm.ask("Selection failed. Proceed with all stories?", default=False)
                if fallback:
                    console.print("[yellow]Proceeding with all stories[/yellow]")
                    return valid_stories
                else:
                    console.print("[yellow]Cancelling pipeline[/yellow]")
                    return []
            except:
                # If confirm fails, return empty list
                console.print("[yellow]Cancelling pipeline due to interaction failure[/yellow]")
                return []

    def _validate_selected_stories(self, stories: List[HackerNewsStory]) -> List[HackerNewsStory]:
        """
        Validate selected stories for processing.

        Args:
            stories: List of selected stories

        Returns:
            List of validated stories
        """
        validated = []
        for story in stories:
            try:
                # Check basic attributes
                if not hasattr(story, 'id') or not story.id:
                    self.logger.warning(f"Story missing ID: {getattr(story, 'title', 'Unknown')}")
                    continue

                if not hasattr(story, 'title') or not story.title.strip():
                    self.logger.warning(f"Story {story.id} missing title")
                    continue

                if not hasattr(story, 'score') or story.score < 0:
                    self.logger.warning(f"Story {story.id} has invalid score")
                    continue

                # URL is optional but if present should be valid
                if hasattr(story, 'url') and story.url:
                    if not story.url.startswith(('http://', 'https://')):
                        self.logger.warning(f"Story {story.id} has invalid URL format")
                        # Don't skip the story, just note the issue

                validated.append(story)

            except Exception as e:
                self.logger.error(f"Error validating story: {e}")

        return validated

    def scrape_articles(
        self, stories: Optional[List[HackerNewsStory]] = None
    ) -> List[ScrapedContent]:
        """
        Scrape article content from stories.

        Args:
            stories: List of stories to scrape (uses self.stories if None)

        Returns:
            List of ScrapedContent objects
        """
        if stories is None:
            stories = self.stories

        if not stories:
            console.print("[red]No stories to scrape![/red]")
            return []

        # Filter stories that have URLs
        stories_with_urls = [story for story in stories if story.url]
        console.print(
            f"[bold blue]Scraping {len(stories_with_urls)} articles...[/bold blue]"
        )

        scraped_content = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "Scraping articles...", total=len(stories_with_urls)
            )

            for i, story in enumerate(stories_with_urls):
                try:
                    progress.update(
                        task, description=f"Scraping: {story.title[:30]}..."
                    )

                    content = self.scraper.scrape_article(story.url)
                    if content:
                        # Add story metadata to content
                        content.title = story.title  # Use HN title if different
                        scraped_content.append(content)
                        self.logger.debug(f"Scraped: {story.title}")
                    else:
                        self.logger.warning(f"Failed to scrape: {story.title}")

                    progress.advance(task)

                except Exception as e:
                    self.logger.error(f"Error scraping {story.title}: {e}")
                    progress.advance(task)

        console.print(
            f"[green]Successfully scraped {len(scraped_content)} articles[/green]"
        )

        # Display scraping results
        if scraped_content:
            table = Table(title="Scraped Articles")
            table.add_column("Title", style="white", max_width=40)
            table.add_column("Words", justify="right", style="green")
            table.add_column("Method", style="yellow")
            table.add_column("Author", style="cyan")

            for content in scraped_content[:10]:  # Show first 10
                table.add_row(
                    (
                        content.title[:40] + "..."
                        if len(content.title) > 40
                        else content.title
                    ),
                    str(content.word_count),
                    content.scraping_method,
                    content.author or "Unknown",
                )

            console.print(table)

        self.scraped_content = scraped_content
        return scraped_content

    def prepare_podcast_segments(self, content: List[ScrapedContent]) -> List[Dict[str, str]]:
        """
        Prepare podcast segments from scraped content.

        Args:
            content: List of scraped content

        Returns:
            List of segments, where each segment is a dictionary with "title" and "text".
        """
        if not content:
            return []

        console.print("[bold blue]Preparing podcast segments...[/bold blue]")
        segments = []

        # Introduction
        intro_text = (
            f"Welcome to HackerCast, your daily digest of the top stories from Hacker News. "
            f"Today is {datetime.now().strftime('%B %d, %Y')}, and we have {len(content)} "
            f"fascinating stories to share with you."
        )
        segments.append({"title": "Introduction", "text": intro_text})

        # Story segments
        for i, article in enumerate(content, 1):
            story_text = f"Story {i}: {article.title}\n\n{article.content}"
            segments.append({"title": article.title, "text": story_text})

        # Conclusion
        outro_text = (
            f"That wraps up today's HackerCast. Thank you for listening, "
            f"and we'll see you tomorrow with more stories from the world of technology."
        )
        segments.append({"title": "Conclusion", "text": outro_text})

        console.print(f"[green]Prepared {len(segments)} segments.[/green]")
        return segments

    def convert_to_audio(self, segments: List[Dict[str, str]]) -> Optional[Path]:
        """
        Convert segments to audio using TTS and generate chapters.

        Args:
            segments: A list of podcast segments with title and text.

        Returns:
            Path to generated audio file or None if failed.
        """
        if not segments:
            console.print("[red]No segments to convert![/red]")
            return None

        console.print("[bold blue]Converting segments to audio...[/bold blue]")

        try:
            self._initialize_tts()
            audio_file = self.config_manager.get_dated_output_path("audio", "mp3")

            audio_path, chapters = self.tts_converter.convert_segments_to_audio(
                segments=segments,
                output_file=str(audio_file),
                language_code=self.config.tts.language_code,
                voice_name=self.config.tts.voice_name,
                speaking_rate=self.config.tts.speaking_rate,
                pitch=self.config.tts.pitch,
            )

            if audio_path:
                console.print(f"[green]Audio generated successfully: {audio_path}[/green]")
                self.audio_files.append(audio_path)
                self.chapters = chapters
                return audio_path
            else:
                console.print("[red]Failed to generate audio![/red]")
                return None

        except Exception as e:
            console.print(f"[red]Error generating audio: {e}[/red]")
            self.logger.error(f"Error generating audio: {e}")
            return None

    def generate_chapter_file(self) -> Optional[Path]:
        """
        Generate a chapter file from the chapter data.

        Returns:
            Path to the generated chapter file or None if failed.
        """
        if not self.chapters:
            console.print("[yellow]No chapter data available to generate chapter file.[/yellow]")
            return None

        console.print("[bold blue]Generating chapter file...[/bold blue]")

        try:
            # Generate chapter file path, sibling to the audio file
            if not self.audio_files:
                self.logger.error("Cannot generate chapter file without an audio file.")
                return None

            audio_file = self.audio_files[-1]
            chapter_file_path = audio_file.with_suffix('.chapters.json')

            # Create the chapter file
            self.chapter_file = create_chapter_file(self.chapters, chapter_file_path)

            console.print(f"[green]Chapter file generated successfully: {self.chapter_file}[/green]")
            return self.chapter_file
        except Exception as e:
            console.print(f"[red]Error generating chapter file: {e}[/red]")
            self.logger.error(f"Error generating chapter file: {e}")
            return None

    def save_pipeline_data(self) -> Path:
        """
        Save all pipeline data to JSON file.

        Returns:
            Path to saved data file
        """
        console.print("[bold blue]Saving pipeline data...[/bold blue]")

        # Use date-based directory and latest naming for pipeline data
        data_file = self.config_manager.get_dated_output_path("data", "json")

        # Generate timestamp for metadata
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        pipeline_data = {
            "timestamp": timestamp,
            "run_date": datetime.now().isoformat(),
            "config": {
                "environment": self.config.environment,
                "max_stories": self.config.hackernews.max_stories,
                "tts_voice": self.config.tts.voice_name,
            },
            "stories": [story.to_dict() for story in self.stories],
            "scraped_content": [content.to_dict() for content in self.scraped_content],
            "audio_files": [str(file) for file in self.audio_files],
            "chapters": self.chapters,
            "chapter_file": str(self.chapter_file) if self.chapter_file else None,
            "stats": {
                "stories_fetched": len(self.stories),
                "articles_scraped": len(self.scraped_content),
                "total_words": sum(
                    content.word_count for content in self.scraped_content
                ),
                "audio_files_generated": len(self.audio_files),
            },
        }

        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(pipeline_data, f, indent=2, ensure_ascii=False)

        console.print(f"[green]Pipeline data saved: {data_file}[/green]")
        self.logger.info(f"Saved pipeline data to: {data_file}")

        return data_file

    def generate_rss_feed(self) -> Optional[Path]:
        """
        Generate RSS feed for podcast.

        Returns:
            Path to RSS feed file or None if failed
        """
        console.print("[bold blue]Generating RSS feed...[/bold blue]")

        try:
            from rss_generator import RSSFeedGenerator

            # Determine base URL (use environment variable or default)
            base_url = os.getenv('HACKERCAST_BASE_URL', 'http://localhost:5000')

            # Create RSS generator
            generator = RSSFeedGenerator(
                output_dir=str(self.config_manager.config.output.base_dir),
                base_url=base_url,
                podcast_title="HackerCast",
                podcast_description="Your daily digest of the top stories from Hacker News",
                podcast_author="HackerCast",
            )

            # Generate and save RSS feed
            rss_file = generator.generate_and_save(
                output_file=str(self.config_manager.get_output_path("data", "../rss.xml"))
            )

            console.print(f"[green]RSS feed generated: {rss_file}[/green]")
            self.logger.info(f"Generated RSS feed: {rss_file}")

            return rss_file

        except Exception as e:
            console.print(f"[yellow]Warning: Failed to generate RSS feed: {e}[/yellow]")
            self.logger.warning(f"Failed to generate RSS feed: {e}")
            return None

    def publish_to_podcast_host(
        self,
        audio_file: Path,
        script: str,
        story_count: int
    ) -> Optional[Dict[str, Any]]:
        """
        Publish episode to podcast hosting platform.

        Args:
            audio_file: Path to the generated audio file
            script: The podcast script
            story_count: Number of stories in the episode

        Returns:
            Publishing result information or None if failed
        """
        console.print("[bold blue]Publishing episode to podcast host...[/bold blue]")

        try:
            self._initialize_publisher()

            # Generate episode metadata
            today = datetime.now()
            title = f"HackerCast - {today.strftime('%B %d, %Y')}"
            summary = f"Daily digest of the top {story_count} Hacker News stories for {today.strftime('%B %d, %Y')}."

            # Calculate episode number based on date (days since epoch)
            epoch_date = datetime(2024, 1, 1)  # Adjust based on when you started
            episode_number = (today.date() - epoch_date.date()).days

            # Get publisher config
            publisher_config = PodcastPublisherConfig(
                self.config.podcast_publishing.__dict__ if hasattr(self.config, 'podcast_publishing') else {}
            )

            if not publisher_config.default_show_id:
                console.print("[yellow]No default show ID configured. Listing available shows...[/yellow]")
                shows = self.podcast_publisher.get_shows()
                if shows:
                    console.print("[cyan]Available shows:[/cyan]")
                    for show in shows:
                        console.print(f"  ID: {show['id']} - {show['attributes']['title']}")
                    console.print("[yellow]Please configure TRANSISTOR_SHOW_ID environment variable[/yellow]")
                return None

            # Publish episode
            result = self.podcast_publisher.publish_podcast_episode(
                audio_file_path=audio_file,
                show_id=publisher_config.default_show_id,
                title=title,
                summary=summary,
                episode_number=episode_number,
                description=f"{summary}\n\nStories covered:\n" + "\n".join(
                    f"- {story.title}" for story in self.stories[:10]
                ),
                auto_publish=publisher_config.auto_publish
            )

            if result['success']:
                console.print(f"[green]Episode published successfully![/green]")
                console.print(f"[cyan]Episode ID: {result['episode_id']}[/cyan]")
                if result.get('episode_url'):
                    console.print(f"[cyan]Episode URL: {result['episode_url']}[/cyan]")

                self.logger.info(f"Published episode {result['episode_id']} to podcast host")
                return result
            else:
                console.print(f"[red]Failed to publish episode: {result['error']}[/red]")
                return None

        except Exception as e:
            console.print(f"[red]Error publishing to podcast host: {e}[/red]")
            self.logger.error(f"Error publishing to podcast host: {e}")
            return None

    def run_full_pipeline(self, limit: Optional[int] = None, interactive: bool = False) -> Dict[str, Any]:
        """
        Run the complete HackerCast pipeline.

        Args:
            limit: Number of stories to process
            interactive: Whether to use interactive story selection

        Returns:
            Pipeline results summary
        """
        console.print("[bold magenta]Starting HackerCast Pipeline[/bold magenta]")
        pipeline_start = time.time()

        try:
            # Step 1: Fetch stories
            stories = self.fetch_top_stories(limit)
            if not stories:
                raise ValueError("No stories fetched")

            # Step 2: Interactive story selection (if enabled)
            if interactive:
                stories = self.select_stories_interactively(stories)
                if not stories:
                    raise ValueError("No stories selected")

            # Step 3: Scrape articles
            content = self.scrape_articles(stories)
            if not content:
                raise ValueError("No articles scraped")

            # Step 3: Prepare podcast segments
            segments = self.prepare_podcast_segments(content)
            if not segments:
                raise ValueError("No segments prepared")

            # Step 4: Convert to audio
            audio_file = self.convert_to_audio(segments)

            # Step 4.5: Generate chapter file
            if audio_file:
                self.generate_chapter_file()

            # Step 5: Publish to podcast host (if configured)
            episode_info = None
            if audio_file and hasattr(self.config, 'podcast_publishing') and self.config.podcast_publishing.enabled:
                # For publishing, we can just pass an empty script for now.
                # In a future iteration, we could generate a summary.
                episode_info = self.publish_to_podcast_host(audio_file, "", len(stories))

            # Step 6: Save pipeline data
            data_file = self.save_pipeline_data()

            # Step 7: Generate RSS feed
            rss_file = self.generate_rss_feed()

            # Calculate runtime
            runtime = time.time() - pipeline_start

            # Display summary
            self._display_pipeline_summary(runtime, audio_file is not None)

            return {
                "success": True,
                "stories_count": len(stories),
                "scraped_count": len(content),
                "script_length": len(script),
                "audio_file": str(audio_file) if audio_file else None,
                "episode_info": episode_info,
                "data_file": str(data_file),
                "runtime": runtime,
            }

        except Exception as e:
            console.print(f"[red]Pipeline failed: {e}[/red]")
            self.logger.error(f"Pipeline failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "runtime": time.time() - pipeline_start,
            }

    def _display_pipeline_summary(self, runtime: float, audio_success: bool):
        """Display pipeline execution summary."""
        table = Table(title="Pipeline Summary", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Stories Fetched", str(len(self.stories)))
        table.add_row("Articles Scraped", str(len(self.scraped_content)))
        table.add_row(
            "Total Words", str(sum(c.word_count for c in self.scraped_content))
        )
        table.add_row("Audio Generated", "Yes" if audio_success else "No")
        table.add_row("Runtime", f"{runtime:.2f} seconds")

        console.print(table)

    def cleanup(self):
        """Clean up resources."""
        try:
            if hasattr(self.scraper, "cleanup"):
                self.scraper.cleanup()
            self.logger.info("Pipeline cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# CLI Interface
@click.group()
@click.option("--config", help="Configuration file path")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def cli(ctx, config, debug):
    """HackerCast: Generate daily podcasts from Hacker News stories."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["debug"] = debug


@cli.command()
@click.option(
    "--limit", "-l", default=None, type=int, help="Number of stories to fetch"
)
@click.option(
    "--interactive", "-i", is_flag=True, help="Use interactive story selection"
)
@click.pass_context
def run(ctx, limit, interactive):
    """Run the complete HackerCast pipeline."""
    pipeline = None
    try:
        pipeline = HackerCastPipeline(ctx.obj["config"])
        if ctx.obj["debug"]:
            pipeline.config.debug = True

        result = pipeline.run_full_pipeline(limit, interactive=interactive)

        if result["success"]:
            console.print("[bold green]Pipeline completed successfully![/bold green]")
            sys.exit(0)
        else:
            console.print("[bold red]Pipeline failed![/bold red]")
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)
    finally:
        if pipeline:
            pipeline.cleanup()


@cli.command()
@click.option("--limit", "-l", default=10, type=int, help="Number of stories to fetch")
@click.pass_context
def fetch(ctx, limit):
    """Fetch top stories from Hacker News."""
    if limit <= 0:
        console.print("[red]Error: Limit must be a positive integer[/red]")
        raise click.Exit(1)

    pipeline = None
    try:
        pipeline = HackerCastPipeline(ctx.obj["config"])
        stories = pipeline.fetch_top_stories(limit)
        console.print(f"[green]Fetched {len(stories)} stories[/green]")
    finally:
        if pipeline:
            pipeline.cleanup()


@cli.command()
@click.argument("url")
@click.pass_context
def scrape(ctx, url):
    """Scrape content from a single URL."""
    pipeline = None
    try:
        pipeline = HackerCastPipeline(ctx.obj["config"])
        content = pipeline.scraper.scrape_article(url)
        if content:
            console.print(
                f"[green]Scraped {content.word_count} words from: {content.title}[/green]"
            )
        else:
            console.print("[red]Failed to scrape content[/red]")
    finally:
        if pipeline:
            pipeline.cleanup()


@cli.command()
@click.argument("text")
@click.argument("output_file")
@click.option("--topic", default="", help="Topic description for podcast transformation")
@click.pass_context
def tts(ctx, text, output_file, topic):
    """Convert text to speech."""
    pipeline = None
    try:
        pipeline = HackerCastPipeline(ctx.obj["config"])
        pipeline._initialize_tts()
        success = pipeline.tts_converter.convert_text_to_speech(text, output_file, topic=topic)
        if success:
            console.print(f"[green]Audio saved to: {output_file}[/green]")
        else:
            console.print("[red]Failed to generate audio[/red]")
            ctx.exit(1)
    finally:
        if pipeline:
            pipeline.cleanup()


@cli.command()
@click.option("--limit", "-l", default=20, type=int, help="Number of stories to fetch")
@click.pass_context
def interactive(ctx, limit):
    """Run HackerCast with interactive story selection (alias for 'run --interactive')."""
    if limit <= 0:
        console.print("[red]Error: Limit must be a positive integer[/red]")
        raise click.Exit(1)

    pipeline = None
    try:
        pipeline = HackerCastPipeline(ctx.obj["config"])
        if ctx.obj["debug"]:
            pipeline.config.debug = True

        result = pipeline.run_full_pipeline(limit, interactive=True)

        if result["success"]:
            console.print("[bold green]Interactive pipeline completed successfully![/bold green]")
            sys.exit(0)
        else:
            console.print("[bold red]Interactive pipeline failed![/bold red]")
            sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        sys.exit(1)
    finally:
        if pipeline:
            pipeline.cleanup()


@cli.command()
@click.argument("audio_file")
@click.option("--title", "-t", help="Episode title")
@click.option("--summary", "-s", help="Episode summary")
@click.option("--show-id", help="Podcast show ID (overrides config)")
@click.option("--episode-number", "-n", type=int, help="Episode number")
@click.option("--season", type=int, help="Season number")
@click.option("--publish", is_flag=True, default=True, help="Publish episode immediately")
@click.pass_context
def publish(ctx, audio_file, title, summary, show_id, episode_number, season, publish):
    """Publish an audio file to podcast hosting platform."""
    audio_path = Path(audio_file)
    if not audio_path.exists():
        console.print(f"[red]Audio file not found: {audio_file}[/red]")
        raise click.Exit(1)

    pipeline = None
    try:
        pipeline = HackerCastPipeline(ctx.obj["config"])
        pipeline._initialize_publisher()

        # Use provided values or generate defaults
        if not title:
            title = f"HackerCast Episode - {datetime.now().strftime('%B %d, %Y')}"

        if not summary:
            summary = f"HackerCast episode for {datetime.now().strftime('%B %d, %Y')}"

        # Get publisher config
        publisher_config = PodcastPublisherConfig(
            pipeline.config.podcast_publishing.__dict__ if hasattr(pipeline.config, 'podcast_publishing') else {}
        )

        # Use provided show_id or default
        target_show_id = show_id or publisher_config.default_show_id

        if not target_show_id:
            console.print("[yellow]No show ID provided. Listing available shows...[/yellow]")
            shows = pipeline.podcast_publisher.get_shows()
            if shows:
                console.print("[cyan]Available shows:[/cyan]")
                for show in shows:
                    console.print(f"  ID: {show['id']} - {show['attributes']['title']}")
            else:
                console.print("[red]No shows found![/red]")
            raise click.Exit(1)

        # Publish episode
        result = pipeline.podcast_publisher.publish_podcast_episode(
            audio_file_path=audio_path,
            show_id=target_show_id,
            title=title,
            summary=summary,
            episode_number=episode_number,
            season=season,
            auto_publish=publish
        )

        if result['success']:
            console.print(f"[green]Episode published successfully![/green]")
            console.print(f"[cyan]Episode ID: {result['episode_id']}[/cyan]")
            if result.get('episode_url'):
                console.print(f"[cyan]Episode URL: {result['episode_url']}[/cyan]")
        else:
            console.print(f"[red]Failed to publish episode: {result['error']}[/red]")
            raise click.Exit(1)

    finally:
        if pipeline:
            pipeline.cleanup()


@cli.command()
@click.pass_context
def shows(ctx):
    """List available podcast shows."""
    pipeline = None
    try:
        pipeline = HackerCastPipeline(ctx.obj["config"])
        pipeline._initialize_publisher()

        shows = pipeline.podcast_publisher.get_shows()
        if shows:
            console.print("[bold cyan]Available Podcast Shows:[/bold cyan]")
            for show in shows:
                attrs = show['attributes']
                console.print(f"[green]ID:[/green] {show['id']}")
                console.print(f"[blue]Title:[/blue] {attrs['title']}")
                console.print(f"[yellow]Description:[/yellow] {attrs.get('description', 'N/A')[:100]}...")
                console.print(f"[cyan]Website:[/cyan] {attrs.get('website', 'N/A')}")
                console.print("---")
        else:
            console.print("[yellow]No shows found[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing shows: {e}[/red]")
        raise click.Exit(1)
    finally:
        if pipeline:
            pipeline.cleanup()


@cli.command()
@click.option("--limit", "-l", default=10, type=int, help="Number of stories to fetch")
@click.pass_context
def select(ctx, limit):
    """Interactively select stories to process."""
    if limit <= 0:
        console.print("[red]Error: Limit must be a positive integer[/red]")
        raise click.Exit(1)

    pipeline = None
    try:
        pipeline = HackerCastPipeline(ctx.obj["config"])
        if ctx.obj["debug"]:
            pipeline.config.debug = True

        # Fetch stories
        stories = pipeline.fetch_top_stories(limit)
        if not stories:
            console.print("[red]No stories fetched![/red]")
            raise click.Exit(1)

        # Interactive selection
        selected_stories = pipeline.select_stories_interactively(stories)
        if selected_stories:
            console.print(f"[green]Selected {len(selected_stories)} stories[/green]")

            # Ask if user wants to continue with processing
            if click.confirm("Continue with scraping and processing selected stories?"):
                # Update pipeline with selected stories
                pipeline.stories = selected_stories

                # Run the rest of the pipeline
                scraped_content = pipeline.scrape_articles(selected_stories)
                if scraped_content:
                    script_content = pipeline.create_script(scraped_content)
                    if script_content:
                        audio_file = pipeline.convert_to_audio(script_content)
                        if audio_file:
                            console.print(f"[bold green]Pipeline completed! Audio saved to: {audio_file}[/bold green]")
                        else:
                            console.print("[red]Failed to generate audio[/red]")
                            sys.exit(1)
                    else:
                        console.print("[red]Failed to create script[/red]")
                        sys.exit(1)
                else:
                    console.print("[red]Failed to scrape articles[/red]")
                    sys.exit(1)
            else:
                console.print("[yellow]Selection completed. Exiting without processing.[/yellow]")
        else:
            console.print("[yellow]No stories selected[/yellow]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        sys.exit(1)
    finally:
        if pipeline:
            pipeline.cleanup()


if __name__ == "__main__":
    cli()
