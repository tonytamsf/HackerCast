#!/usr/bin/env python

import os
import sys
import logging
from typing import Optional
from google.cloud import texttospeech
from google.cloud import storage
from google.api_core import exceptions as gcloud_exceptions
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TTSConverter:
    """Text-to-Speech converter using Google Cloud Text-to-Speech API."""

    def __init__(self, credentials_path: Optional[str] = None, gcs_bucket: Optional[str] = None):
        """
        Initialize the TTS converter.

        Args:
            credentials_path: Path to Google Cloud service account key file.
                            If None, uses GOOGLE_APPLICATION_CREDENTIALS env var.
            gcs_bucket: Google Cloud Storage bucket name for long audio synthesis.
        """
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        try:
            self.client = texttospeech.TextToSpeechClient()
            self.long_audio_client = texttospeech.TextToSpeechLongAudioSynthesizeClient()
            self.storage_client = storage.Client()
            self.gcs_bucket = gcs_bucket
            logger.info("TTS clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TTS clients: {e}")
            raise

    def convert_text_to_speech(
        self,
        text: str,
        output_file: str,
        language_code: str = "en-US",
        voice_name: str = "en-US-Neural2-D",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bool:
        """
        Convert text to speech and save as MP3.

        Args:
            text: Text to convert to speech
            output_file: Path to save the MP3 file
            language_code: Language code (e.g., 'en-US')
            voice_name: Voice name to use
            speaking_rate: Speaking rate (0.25 to 4.0)
            pitch: Voice pitch (-20.0 to 20.0)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate input
            if not text.strip():
                logger.error("Text input is empty")
                return False

            # Check if we need to use Long Audio API
            text_bytes = len(text.encode('utf-8'))
            if text_bytes > 5000:
                logger.info(f"Text length ({text_bytes} bytes) exceeds standard limit. Using Long Audio API.")
                return self._convert_long_audio(text, output_file, language_code, voice_name, speaking_rate, pitch)

            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code, name=voice_name
            )

            # Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
                pitch=pitch,
            )

            # Perform the text-to-speech request
            logger.info(f"Converting text to speech: {len(text)} characters")
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # Write the response to the output file
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "wb") as out:
                out.write(response.audio_content)

            logger.info(f"Audio content written to file: {output_file}")
            return True

        except gcloud_exceptions.GoogleAPIError as e:
            logger.error(f"Google Cloud API error: {e}")
            return False
        except PermissionError as e:
            logger.error(f"Permission error writing to {output_file}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during TTS conversion: {e}")
            return False

    def get_available_voices(self, language_code: str = "en-US") -> list:
        """
        Get list of available voices for a language.

        Args:
            language_code: Language code to filter voices

        Returns:
            List of available voice names
        """
        try:
            voices = self.client.list_voices(language_code=language_code)
            return [voice.name for voice in voices.voices]
        except Exception as e:
            logger.error(f"Error fetching available voices: {e}")
            return []

    def _convert_long_audio(
        self,
        text: str,
        output_file: str,
        language_code: str = "en-US",
        voice_name: str = "en-US-Neural2-D",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bool:
        """
        Convert long text to speech using the Long Audio API.

        Args:
            text: Text to convert to speech
            output_file: Path to save the MP3 file
            language_code: Language code (e.g., 'en-US')
            voice_name: Voice name to use
            speaking_rate: Speaking rate (0.25 to 4.0)
            pitch: Voice pitch (-20.0 to 20.0)

        Returns:
            True if successful, False otherwise
        """
        if not self.gcs_bucket:
            logger.error("GCS bucket not configured. Required for Long Audio API.")
            return False

        try:
            # Get project ID from the client
            project_id = self.storage_client.project

            # Create unique filename for GCS
            import uuid
            gcs_filename = f"tts_output_{uuid.uuid4().hex}.mp3"
            gcs_uri = f"gs://{self.gcs_bucket}/{gcs_filename}"

            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code, name=voice_name
            )

            # Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                speaking_rate=speaking_rate,
                pitch=pitch,
            )

            # Create the request
            request = texttospeech.SynthesizeLongAudioRequest(
                parent=f"projects/{project_id}/locations/us-central1",
                input=synthesis_input,
                audio_config=audio_config,
                voice=voice,
                output_gcs_uri=gcs_uri,
            )

            logger.info(f"Starting long audio synthesis: {len(text)} characters")
            operation = self.long_audio_client.synthesize_long_audio(request=request)

            logger.info("Waiting for long audio synthesis to complete...")
            result = operation.result(timeout=300)  # 5 minute timeout

            # Download the file from GCS
            bucket = self.storage_client.bucket(self.gcs_bucket)
            blob = bucket.blob(gcs_filename)

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # Download the file
            blob.download_to_filename(output_file)
            logger.info(f"Audio content downloaded to: {output_file}")

            # Clean up the GCS file
            blob.delete()
            logger.info(f"Cleaned up temporary file: gs://{self.gcs_bucket}/{gcs_filename}")

            return True

        except Exception as e:
            logger.error(f"Error during long audio synthesis: {e}")
            return False


def main():
    """Command-line interface for TTS conversion."""
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print(
            "Usage: python tts_converter.py '<text>' <output_file.mp3> [gcs_bucket]", file=sys.stderr
        )
        print("  gcs_bucket: Optional Google Cloud Storage bucket name for long audio synthesis", file=sys.stderr)
        sys.exit(1)

    text = sys.argv[1]
    output_file = sys.argv[2]
    gcs_bucket = sys.argv[3] if len(sys.argv) == 4 else os.environ.get("GCS_BUCKET")

    # Validate output file extension
    if not output_file.lower().endswith(".mp3"):
        print("Error: Output file must have .mp3 extension", file=sys.stderr)
        sys.exit(1)

    # Check for Google Cloud credentials
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print(
            "Warning: GOOGLE_APPLICATION_CREDENTIALS environment variable not set",
            file=sys.stderr,
        )

    # Check if we might need GCS bucket for long audio
    text_bytes = len(text.encode('utf-8'))
    if text_bytes > 5000 and not gcs_bucket:
        print(
            f"Warning: Text is {text_bytes} bytes (>5000). Long Audio API requires a GCS bucket.",
            file=sys.stderr,
        )
        print("Provide bucket name as 3rd argument or set GCS_BUCKET environment variable.", file=sys.stderr)

    try:
        converter = TTSConverter(gcs_bucket=gcs_bucket)
        success = converter.convert_text_to_speech(text, output_file)

        if success:
            print(f"Successfully converted text to speech: {output_file}")
        else:
            print("Failed to convert text to speech", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
