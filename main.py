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

        self.logger = logging.getLogger(__name__)
        self.logger.info("HackerCast pipeline initialized")

        # Pipeline state
        self.stories: List[HackerNewsStory] = []
        self.scraped_content: List[ScrapedContent] = []
        self.audio_files: List[Path] = []

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

    def generate_podcast_script(self, content: List[ScrapedContent]) -> str:
        """
        Generate a podcast script from scraped content.

        Args:
            content: List of scraped content

        Returns:
            Generated podcast script
        """
        if not content:
            return ""

        console.print("[bold blue]Generating podcast script...[/bold blue]")

        script_parts = []

        # Introduction
        script_parts.append(
            f"Welcome to HackerCast, your daily digest of the top stories from Hacker News. "
            f"Today is {datetime.now().strftime('%B %d, %Y')}, and we have {len(content)} "
            f"fascinating stories to share with you."
        )

        # Story segments
        for i, article in enumerate(content, 1):
            script_parts.append(f"\n\nStory {i}: {article.title}")

            # Add article summary (first few sentences)
            sentences = article.content.split(".")[:3]  # First 3 sentences
            summary = ". ".join(sentences).strip()
            if summary:
                script_parts.append(f"\n{summary}.")

            # Add transition
            if i < len(content):
                script_parts.append("\n\nNext up...")

        # Conclusion
        script_parts.append(
            f"\n\nThat wraps up today's HackerCast. Thank you for listening, "
            f"and we'll see you tomorrow with more stories from the world of technology."
        )

        script = "".join(script_parts)

        # Save script to file
        script_file = self.config_manager.get_output_path(
            "data", f'script_{datetime.now().strftime("%Y%m%d")}.txt'
        )
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script)

        console.print(f"[green]Script generated and saved to: {script_file}[/green]")
        self.logger.info(f"Generated script with {len(script)} characters")

        return script

    def convert_to_audio(self, script: str) -> Optional[Path]:
        """
        Convert script to audio using TTS.

        Args:
            script: Podcast script text

        Returns:
            Path to generated audio file or None if failed
        """
        if not script.strip():
            console.print("[red]No script to convert![/red]")
            return None

        console.print("[bold blue]Converting script to audio...[/bold blue]")

        try:
            self._initialize_tts()

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_file = self.config_manager.get_output_path(
                "audio", f"hackercast_{timestamp}.mp3"
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Converting to speech...", total=None)

                success = self.tts_converter.convert_text_to_speech(
                    text=script,
                    output_file=str(audio_file),
                    language_code=self.config.tts.language_code,
                    voice_name=self.config.tts.voice_name,
                    speaking_rate=self.config.tts.speaking_rate,
                    pitch=self.config.tts.pitch,
                )

                if success:
                    progress.update(task, description=f"Audio saved: {audio_file.name}")
                    console.print(
                        f"[green]Audio generated successfully: {audio_file}[/green]"
                    )
                    self.logger.info(f"Generated audio file: {audio_file}")
                    self.audio_files.append(audio_file)
                    return audio_file
                else:
                    console.print("[red]Failed to generate audio![/red]")
                    return None

        except Exception as e:
            console.print(f"[red]Error generating audio: {e}[/red]")
            self.logger.error(f"Error generating audio: {e}")
            return None

    def save_pipeline_data(self) -> Path:
        """
        Save all pipeline data to JSON file.

        Returns:
            Path to saved data file
        """
        console.print("[bold blue]Saving pipeline data...[/bold blue]")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_file = self.config_manager.get_output_path(
            "data", f"pipeline_data_{timestamp}.json"
        )

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

    def run_full_pipeline(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Run the complete HackerCast pipeline.

        Args:
            limit: Number of stories to process

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

            # Step 2: Scrape articles
            content = self.scrape_articles(stories)
            if not content:
                raise ValueError("No articles scraped")

            # Step 3: Generate script
            script = self.generate_podcast_script(content)
            if not script:
                raise ValueError("No script generated")

            # Step 4: Convert to audio
            audio_file = self.convert_to_audio(script)

            # Step 5: Save pipeline data
            data_file = self.save_pipeline_data()

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
@click.pass_context
def run(ctx, limit):
    """Run the complete HackerCast pipeline."""
    pipeline = None
    try:
        pipeline = HackerCastPipeline(ctx.obj["config"])
        if ctx.obj["debug"]:
            pipeline.config.debug = True

        result = pipeline.run_full_pipeline(limit)

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
@click.pass_context
def tts(ctx, text, output_file):
    """Convert text to speech."""
    pipeline = None
    try:
        pipeline = HackerCastPipeline(ctx.obj["config"])
        pipeline._initialize_tts()
        success = pipeline.tts_converter.convert_text_to_speech(text, output_file)
        if success:
            console.print(f"[green]Audio saved to: {output_file}[/green]")
        else:
            console.print("[red]Failed to generate audio[/red]")
    finally:
        if pipeline:
            pipeline.cleanup()


if __name__ == "__main__":
    cli()
