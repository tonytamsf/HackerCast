#!/usr/bin/env python

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class PodcastPublisher:
    """
    Publisher for podcast episodes to hosting platforms with dynamic ad insertion support.
    Primary integration with Transistor.fm due to their superior dynamic ad insertion capabilities.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.transistor.fm/v1"):
        """
        Initialize the podcast publisher.

        Args:
            api_key: API key for the podcast hosting platform
            base_url: Base URL for the API (defaults to Transistor.fm)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.logger = logging.getLogger(__name__)

        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update({
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'HackerCast/1.0'
        })

        self.logger.info("Podcast publisher initialized")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an API request with proper error handling and rate limiting.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests

        Returns:
            JSON response data

        Raises:
            Exception: If the request fails or returns an error
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(method, url, **kwargs)

            # Handle rate limiting
            if response.status_code == 429:
                self.logger.warning("Rate limit exceeded, waiting 10 seconds...")
                time.sleep(10)
                response = self.session.request(method, url, **kwargs)

            response.raise_for_status()

            if response.content:
                return response.json()
            else:
                return {}

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    self.logger.error(f"Error details: {error_detail}")
                except:
                    self.logger.error(f"Error response: {e.response.text}")
            raise

    def get_shows(self) -> List[Dict[str, Any]]:
        """
        Get all shows/podcasts for the authenticated user.

        Returns:
            List of show objects
        """
        self.logger.info("Fetching shows...")
        response = self._make_request('GET', 'shows')
        shows = response.get('data', [])
        self.logger.info(f"Found {len(shows)} shows")
        return shows

    def get_show_by_id(self, show_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific show by ID.

        Args:
            show_id: The show ID

        Returns:
            Show object or None if not found
        """
        try:
            response = self._make_request('GET', f'shows/{show_id}')
            return response.get('data')
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def authorize_audio_upload(self, filename: str, content_type: str = "audio/mpeg") -> Dict[str, str]:
        """
        Authorize an audio file upload and get presigned URL.

        Args:
            filename: Name of the audio file
            content_type: MIME type of the audio file

        Returns:
            Dictionary with upload_url and audio_url
        """
        self.logger.info(f"Authorizing upload for {filename}")

        data = {
            "filename": filename,
            "content_type": content_type
        }

        response = self._make_request('POST', 'uploads/authorize', json=data)

        upload_info = {
            'upload_url': response['data']['attributes']['upload_url'],
            'audio_url': response['data']['attributes']['audio_url']
        }

        self.logger.info("Upload authorization successful")
        return upload_info

    def upload_audio_file(self, file_path: Path, upload_url: str) -> bool:
        """
        Upload an audio file to the presigned URL.

        Args:
            file_path: Path to the audio file
            upload_url: Presigned URL from authorize_audio_upload

        Returns:
            True if upload successful, False otherwise
        """
        self.logger.info(f"Uploading audio file: {file_path}")

        try:
            with open(file_path, 'rb') as audio_file:
                # Use a separate session for file upload to avoid auth headers
                upload_response = requests.put(
                    upload_url,
                    data=audio_file,
                    headers={'Content-Type': 'audio/mpeg'}
                )
                upload_response.raise_for_status()

            self.logger.info("Audio file uploaded successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to upload audio file: {e}")
            return False

    def create_episode(
        self,
        show_id: str,
        title: str,
        summary: str,
        audio_url: str,
        season: Optional[int] = None,
        number: Optional[int] = None,
        published_at: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new podcast episode.

        Args:
            show_id: ID of the podcast show
            title: Episode title
            summary: Episode summary/description
            audio_url: URL to the audio file (from upload_audio_file)
            season: Season number (optional)
            number: Episode number (optional)
            published_at: Publication date in ISO format (optional, defaults to now)
            description: Detailed episode description (optional)

        Returns:
            Created episode data
        """
        self.logger.info(f"Creating episode: {title}")

        if published_at is None:
            published_at = datetime.now().isoformat()

        episode_data = {
            "show_id": show_id,
            "title": title,
            "summary": summary,
            "description": description or summary,
            "audio_url": audio_url,
            "published_at": published_at,
            "status": "draft"  # Create as draft first
        }

        # Add optional fields
        if season is not None:
            episode_data["season"] = season
        if number is not None:
            episode_data["number"] = number

        data = {"episode": episode_data}
        response = self._make_request('POST', 'episodes', json=data)

        episode = response.get('data')
        self.logger.info(f"Episode created with ID: {episode['id']}")
        return episode

    def publish_episode(self, episode_id: str) -> Dict[str, Any]:
        """
        Publish a draft episode.

        Args:
            episode_id: ID of the episode to publish

        Returns:
            Updated episode data
        """
        self.logger.info(f"Publishing episode: {episode_id}")

        data = {
            "episode": {
                "status": "published"
            }
        }

        response = self._make_request('PATCH', f'episodes/{episode_id}', json=data)
        episode = response.get('data')

        self.logger.info(f"Episode {episode_id} published successfully")
        return episode

    def publish_podcast_episode(
        self,
        audio_file_path: Path,
        show_id: str,
        title: str,
        summary: str,
        season: Optional[int] = None,
        episode_number: Optional[int] = None,
        description: Optional[str] = None,
        auto_publish: bool = True
    ) -> Dict[str, Any]:
        """
        Complete workflow to upload and publish a podcast episode.

        Args:
            audio_file_path: Path to the MP3 audio file
            show_id: ID of the podcast show
            title: Episode title
            summary: Episode summary
            season: Season number (optional)
            episode_number: Episode number (optional)
            description: Detailed description (optional)
            auto_publish: Whether to automatically publish the episode

        Returns:
            Dictionary with episode information and upload results
        """
        if not audio_file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        if not audio_file_path.suffix.lower() in ['.mp3', '.m4a', '.wav']:
            raise ValueError(f"Unsupported audio format: {audio_file_path.suffix}")

        try:
            # Step 1: Authorize upload
            filename = audio_file_path.name
            upload_info = self.authorize_audio_upload(filename)

            # Step 2: Upload audio file
            if not self.upload_audio_file(audio_file_path, upload_info['upload_url']):
                raise Exception("Failed to upload audio file")

            # Step 3: Create episode
            episode = self.create_episode(
                show_id=show_id,
                title=title,
                summary=summary,
                audio_url=upload_info['audio_url'],
                season=season,
                number=episode_number,
                description=description
            )

            # Step 4: Publish episode (if requested)
            if auto_publish:
                episode = self.publish_episode(episode['id'])

            return {
                'success': True,
                'episode_id': episode['id'],
                'episode_url': episode['attributes'].get('share_url'),
                'status': episode['attributes']['status'],
                'published_at': episode['attributes'].get('published_at'),
                'audio_url': upload_info['audio_url']
            }

        except Exception as e:
            self.logger.error(f"Failed to publish episode: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_episode_analytics(self, episode_id: str) -> Dict[str, Any]:
        """
        Get analytics for a specific episode.

        Args:
            episode_id: Episode ID

        Returns:
            Analytics data
        """
        response = self._make_request('GET', f'analytics/episodes/{episode_id}')
        return response.get('data', {})

    def create_dynamic_ad_campaign(
        self,
        show_id: str,
        name: str,
        ad_audio_url: str,
        position: str = "pre_roll",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a dynamic ad insertion campaign.

        Args:
            show_id: ID of the podcast show
            name: Campaign name
            ad_audio_url: URL to the ad audio file
            position: Ad position ("pre_roll", "mid_roll", "post_roll")
            start_date: Campaign start date (ISO format)
            end_date: Campaign end date (ISO format)

        Returns:
            Created campaign data
        """
        self.logger.info(f"Creating dynamic ad campaign: {name}")

        campaign_data = {
            "show_id": show_id,
            "name": name,
            "ad_audio_url": ad_audio_url,
            "position": position,
            "active": True
        }

        if start_date:
            campaign_data["start_date"] = start_date
        if end_date:
            campaign_data["end_date"] = end_date

        # Note: This is a hypothetical endpoint as Transistor's exact DAI API isn't fully documented
        # In practice, you might need to use their dashboard for DAI setup initially
        try:
            data = {"campaign": campaign_data}
            response = self._make_request('POST', 'advertising/campaigns', json=data)
            return response.get('data')
        except Exception as e:
            self.logger.warning(f"Dynamic ad campaign creation may require dashboard setup: {e}")
            raise


class PodcastPublisherConfig:
    """Configuration for podcast publishing."""

    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize from configuration dictionary.

        Args:
            config_dict: Configuration dictionary
        """
        self.api_key = config_dict.get('api_key') or os.getenv('TRANSISTOR_API_KEY')
        self.default_show_id = config_dict.get('default_show_id') or os.getenv('TRANSISTOR_SHOW_ID')
        self.base_url = config_dict.get('base_url', 'https://api.transistor.fm/v1')
        self.auto_publish = config_dict.get('auto_publish', True)
        self.default_season = config_dict.get('default_season')

        if not self.api_key:
            raise ValueError("Transistor API key is required. Set TRANSISTOR_API_KEY environment variable or provide in config.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'api_key': self.api_key,
            'default_show_id': self.default_show_id,
            'base_url': self.base_url,
            'auto_publish': self.auto_publish,
            'default_season': self.default_season
        }