#!/usr/bin/env python

import os
import sys
import logging
from typing import Optional
from google.cloud import texttospeech
from google.api_core import exceptions as gcloud_exceptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TTSConverter:
    """Text-to-Speech converter using Google Cloud Text-to-Speech API."""

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize the TTS converter.

        Args:
            credentials_path: Path to Google Cloud service account key file.
                            If None, uses GOOGLE_APPLICATION_CREDENTIALS env var.
        """
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

        try:
            self.client = texttospeech.TextToSpeechClient()
            logger.info("TTS client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TTS client: {e}")
            raise

    def convert_text_to_speech(
        self,
        text: str,
        output_file: str,
        language_code: str = 'en-US',
        voice_name: str = 'en-US-Neural2-D',
        speaking_rate: float = 1.0,
        pitch: float = 0.0
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

            if len(text) > 5000:
                logger.warning(f"Text length ({len(text)}) exceeds recommended limit (5000 chars)")

            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )

            # Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
                pitch=pitch
            )

            # Perform the text-to-speech request
            logger.info(f"Converting text to speech: {len(text)} characters")
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # Write the response to the output file
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'wb') as out:
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

    def get_available_voices(self, language_code: str = 'en-US') -> list:
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

def main():
    """Command-line interface for TTS conversion."""
    if len(sys.argv) != 3:
        print("Usage: python tts_converter.py '<text>' <output_file.mp3>", file=sys.stderr)
        sys.exit(1)

    text = sys.argv[1]
    output_file = sys.argv[2]

    # Validate output file extension
    if not output_file.lower().endswith('.mp3'):
        print("Error: Output file must have .mp3 extension", file=sys.stderr)
        sys.exit(1)

    # Check for Google Cloud credentials
    if not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        print("Warning: GOOGLE_APPLICATION_CREDENTIALS environment variable not set", file=sys.stderr)

    try:
        converter = TTSConverter()
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