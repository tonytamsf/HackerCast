#!/usr/bin/env python

import os
import json
import logging
import time
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime
import requests
from google.auth import default
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


class NotebookLMClient:
    """Client for Google Agentspace NotebookLM API for podcast generation."""

    def __init__(
        self,
        project_number: str,
        location: str = "global",
        endpoint_location: str = "us",
        credentials_path: Optional[str] = None,
    ):
        """
        Initialize the NotebookLM client.

        Args:
            project_number: Google Cloud project number
            location: Geographic location (e.g., 'global', 'us-central1')
            endpoint_location: Multi-region endpoint ('us' or 'eu')
            credentials_path: Path to service account key file
        """
        self.project_number = project_number
        self.location = location
        self.endpoint_location = endpoint_location

        # Set up authentication
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        try:
            self.credentials, self.project_id = default()
            self.credentials.refresh(Request())
            logger.info("NotebookLM client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize NotebookLM client: {e}")
            raise

        # API endpoints - Use project_number for Discovery Engine API
        # Note: Discovery Engine API uses project_number, not project_id
        self.base_url = f"https://discoveryengine.googleapis.com/v1/projects/{project_number}/locations/{location}"
        self.notebooks_url = f"{self.base_url}/notebooks"
        self.podcast_url = f"{self.base_url}/podcasts"

        logger.info(f"Using podcast API endpoint: {self.podcast_url}")

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        if not self.credentials.valid:
            self.credentials.refresh(Request())

        return {
            "Authorization": f"Bearer {self.credentials.token}",
            "Content-Type": "application/json",
        }

    def check_api_access(self) -> bool:
        """
        Check if the Podcast API is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            headers = self._get_auth_headers()
            # Try a simple GET request to check if the endpoint exists
            response = requests.get(self.podcast_url, headers=headers, timeout=30)

            if response.status_code == 405:  # Method Not Allowed - endpoint exists but GET not supported
                logger.info("Podcast API endpoint is accessible")
                return True
            elif response.status_code == 404:
                logger.warning("Podcast API endpoint not found - may not be enabled or available")
                return False
            elif response.status_code == 403:
                logger.warning("Permission denied - check IAM roles")
                return False
            else:
                logger.info(f"Podcast API check returned status: {response.status_code}")
                return True

        except Exception as e:
            logger.error(f"Error checking API access: {e}")
            return False

    def create_notebook(self, title: str, description: str = "") -> Optional[Dict[str, Any]]:
        """
        Create a new notebook.

        Args:
            title: Notebook title
            description: Notebook description

        Returns:
            Notebook data or None if failed
        """
        try:
            payload = {
                "title": title,
                "description": description,
            }

            headers = self._get_auth_headers()
            response = requests.post(
                self.notebooks_url, json=payload, headers=headers, timeout=30
            )

            if response.status_code == 200:
                notebook_data = response.json()
                logger.info(f"Created notebook: {notebook_data.get('name', title)}")
                return notebook_data
            else:
                logger.error(
                    f"Failed to create notebook: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error creating notebook: {e}")
            return None

    def add_sources_to_notebook(
        self, notebook_name: str, sources: List[Dict[str, Any]]
    ) -> bool:
        """
        Add sources to a notebook.

        Args:
            notebook_name: Full notebook resource name
            sources: List of source data dictionaries

        Returns:
            True if successful, False otherwise
        """
        try:
            sources_url = f"{self.notebooks_url}/{notebook_name}/sources:batchCreate"
            payload = {"sources": sources}

            headers = self._get_auth_headers()
            response = requests.post(
                sources_url, json=payload, headers=headers, timeout=30
            )

            if response.status_code == 200:
                logger.info(f"Added {len(sources)} sources to notebook")
                return True
            else:
                logger.error(
                    f"Failed to add sources: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error adding sources to notebook: {e}")
            return False

    def generate_podcast(
        self,
        contexts: List[Dict[str, str]],
        title: str,
        description: str = "",
        focus_prompt: str = "",
        length: str = "STANDARD",
        language_code: str = "en-US",
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a podcast using the standalone Podcast API.

        Args:
            contexts: List of context elements (text, images, etc.)
            title: Podcast title
            description: Podcast description
            focus_prompt: Focus for the podcast discussion
            length: Podcast length ('SHORT' for 4-5 min, 'STANDARD' for ~10 min)
            language_code: Language code (e.g., 'en-US')

        Returns:
            Podcast generation response or None if failed
        """
        try:
            # Validate input size (must be < 100,000 tokens)
            total_text_length = sum(
                len(context.get("text", "")) for context in contexts
            )
            if total_text_length > 400000:  # Rough estimate: 4 chars per token
                logger.warning(
                    f"Context size ({total_text_length} chars) may exceed token limit"
                )

            payload = {
                "podcastConfig": {
                    "length": length,
                    "languageCode": language_code,
                },
                "contexts": contexts,
                "title": title,
                "description": description,
            }

            # Add focus prompt if provided
            if focus_prompt:
                payload["podcastConfig"]["focus"] = focus_prompt

            headers = self._get_auth_headers()
            logger.info(f"Making request to: {self.podcast_url}")
            logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")

            response = requests.post(
                self.podcast_url, json=payload, headers=headers, timeout=300
            )

            if response.status_code == 200:
                podcast_data = response.json()
                logger.info(f"Podcast generation initiated: {title}")
                return podcast_data
            else:
                error_msg = f"Failed to generate podcast: {response.status_code} - {response.text}"
                logger.error(error_msg)

                # Add specific error guidance
                if response.status_code == 404:
                    logger.error("404 Error - This usually means:")
                    logger.error("1. The Podcast API is not enabled for your project")
                    logger.error("2. You don't have the 'Podcast API User' role (roles/discoveryengine.podcastApiUser)")
                    logger.error("3. The Podcast API is not available in your region or project")
                    logger.error("4. You may need to be allowlisted for this feature")
                elif response.status_code == 403:
                    logger.error("403 Error - Permission denied. Check that:")
                    logger.error("1. You have the 'Podcast API User' role")
                    logger.error("2. The Discovery Engine API is enabled")
                    logger.error("3. Your authentication credentials are valid")

                return None

        except Exception as e:
            logger.error(f"Error generating podcast: {e}")
            return None

    def download_audio(self, audio_url: str, output_file: str) -> bool:
        """
        Download generated audio file.

        Args:
            audio_url: URL to the generated audio
            output_file: Local path to save the audio

        Returns:
            True if successful, False otherwise
        """
        try:
            headers = self._get_auth_headers()
            response = requests.get(audio_url, headers=headers, stream=True, timeout=300)

            if response.status_code == 200:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)

                with open(output_file, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                logger.info(f"Audio downloaded successfully: {output_file}")
                return True
            else:
                logger.error(
                    f"Failed to download audio: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            return False


class NotebookLMPodcastGenerator:
    """High-level interface for generating podcasts from content."""

    def __init__(
        self,
        project_number: str,
        location: str = "global",
        endpoint_location: str = "us",
        credentials_path: Optional[str] = None,
    ):
        """
        Initialize the podcast generator.

        Args:
            project_number: Google Cloud project number
            location: Geographic location
            endpoint_location: Multi-region endpoint
            credentials_path: Path to service account key file
        """
        self.client = NotebookLMClient(
            project_number=project_number,
            location=location,
            endpoint_location=endpoint_location,
            credentials_path=credentials_path,
        )

    def create_podcast_from_articles(
        self,
        articles: List[Dict[str, str]],
        title: str,
        description: str = "",
        focus_prompt: str = "",
        length: str = "STANDARD",
        output_file: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a podcast from a list of articles.

        Args:
            articles: List of articles with 'title' and 'content' keys
            title: Podcast title
            description: Podcast description
            focus_prompt: Focus for the discussion
            length: Podcast length ('SHORT' or 'STANDARD')
            output_file: Path to save the audio file

        Returns:
            Path to the generated audio file or None if failed
        """
        try:
            # Prepare contexts from articles
            contexts = []
            for article in articles:
                article_text = f"Title: {article.get('title', 'Unknown')}\n\n"
                article_text += article.get('content', '')

                contexts.append({"text": article_text})

            # Add default focus prompt for tech news if none provided
            if not focus_prompt:
                focus_prompt = (
                    "Create an engaging technology podcast discussion about these Hacker News stories. "
                    "Focus on the technical implications, innovation aspects, and broader impact on the tech industry. "
                    "Make it conversational and accessible to a technical audience."
                )

            # Check API access first
            if not self.client.check_api_access():
                logger.error("Podcast API is not accessible. Please check your project configuration and permissions.")
                return None

            # Generate podcast
            logger.info(f"Generating podcast with {len(articles)} articles")
            response = self.client.generate_podcast(
                contexts=contexts,
                title=title,
                description=description,
                focus_prompt=focus_prompt,
                length=length,
            )

            if not response:
                logger.error("Failed to generate podcast")
                return None

            # Check for audio URL in response
            audio_url = response.get("audioUrl") or response.get("audio_url")
            if not audio_url:
                logger.error("No audio URL in podcast response")
                logger.debug(f"Response: {response}")
                return None

            # Generate output filename if not provided
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"output/audio/hackercast_notebooklm_{timestamp}.mp3"

            # Download the audio
            success = self.client.download_audio(audio_url, output_file)
            if success:
                logger.info(f"Podcast generated successfully: {output_file}")
                return output_file
            else:
                logger.error("Failed to download podcast audio")
                return None

        except Exception as e:
            logger.error(f"Error creating podcast from articles: {e}")
            return None

    def create_podcast_from_text(
        self,
        text: str,
        title: str,
        description: str = "",
        focus_prompt: str = "",
        length: str = "STANDARD",
        output_file: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a podcast from raw text.

        Args:
            text: Text content for the podcast
            title: Podcast title
            description: Podcast description
            focus_prompt: Focus for the discussion
            length: Podcast length ('SHORT' or 'STANDARD')
            output_file: Path to save the audio file

        Returns:
            Path to the generated audio file or None if failed
        """
        try:
            contexts = [{"text": text}]

            response = self.client.generate_podcast(
                contexts=contexts,
                title=title,
                description=description,
                focus_prompt=focus_prompt,
                length=length,
            )

            if not response:
                return None

            audio_url = response.get("audioUrl") or response.get("audio_url")
            if not audio_url:
                logger.error("No audio URL in podcast response")
                return None

            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"output/audio/hackercast_notebooklm_{timestamp}.mp3"

            success = self.client.download_audio(audio_url, output_file)
            return output_file if success else None

        except Exception as e:
            logger.error(f"Error creating podcast from text: {e}")
            return None