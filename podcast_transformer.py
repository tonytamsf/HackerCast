#!/usr/bin/env python

import os
import logging
from typing import Optional
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PodcastTransformer:
    """Transforms text content into podcast format using Gemini 2.5 Flash."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the podcast transformer.

        Args:
            api_key: Gemini API key. If None, uses GEMINI_API_KEY env var.
        """
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY environment variable or pass api_key parameter.")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        logger.info("Podcast transformer initialized with Gemini 2.5 Flash")

    def load_podcast_prompt(self, prompt_file: str = "prompts/podcast-prompt-1.md") -> str:
        """
        Load the podcast transformation prompt from file.

        Args:
            prompt_file: Path to the prompt file

        Returns:
            The prompt content as string

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt = f.read()
            logger.info(f"Loaded podcast prompt from {prompt_file}")
            return prompt
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_file}")
            raise

    def transform_to_podcast(self, content: str, topic: str = "") -> str:
        """
        Transform content into podcast format using the loaded prompt.

        Args:
            content: The content to transform
            topic: Optional topic description for the episode

        Returns:
            Transformed podcast script

        Raises:
            Exception: If transformation fails
        """
        try:
            # Load the podcast prompt
            prompt_template = self.load_podcast_prompt()

            # Prepare the full prompt with content
            if topic:
                full_prompt = prompt_template.replace(
                    "[Briefly describe the topic, e.g., \"The Science of Black Holes,\" \"The History of the Silk Road,\" \"An Introduction to Quantum Computing\"]",
                    topic
                )
            else:
                full_prompt = prompt_template

            # Add the content to transform at the end
            full_prompt += f"\n\n{content}"

            logger.info("=" * 60)
            logger.info("🤖 STARTING GEMINI TRANSFORMATION")
            logger.info("=" * 60)
            logger.info(f"📝 Content length: {len(content)} characters")
            logger.info(f"🎯 Topic: {topic if topic else 'Auto-generated from content'}")
            logger.info(f"📄 Full prompt length: {len(full_prompt)} characters")
            logger.info("🚀 Sending request to Gemini 2.0 Flash...")

            # Generate the podcast script
            response = self.model.generate_content(full_prompt)

            if not response.text:
                raise Exception("Empty response from Gemini API")

            logger.info("✅ GEMINI TRANSFORMATION COMPLETED SUCCESSFULLY")
            logger.info(f"📊 Generated script length: {len(response.text)} characters")
            logger.info("=" * 60)

            return response.text.strip()

        except Exception as e:
            logger.error("❌ GEMINI TRANSFORMATION FAILED")
            logger.error(f"🚨 Error: {e}")
            logger.error("=" * 60)
            raise


def main():
    """Command-line interface for podcast transformation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python podcast_transformer.py '<content>' [topic]", file=sys.stderr)
        sys.exit(1)

    content = sys.argv[1]
    topic = sys.argv[2] if len(sys.argv) > 2 else ""

    try:
        transformer = PodcastTransformer()
        podcast_script = transformer.transform_to_podcast(content, topic)
        print(podcast_script)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()