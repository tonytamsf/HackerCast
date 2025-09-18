#!/usr/bin/env python

import os
import sys
import logging
import tempfile
import re
import subprocess
from typing import Optional, List
from google.cloud import texttospeech
from google.api_core import exceptions as gcloud_exceptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TTSConverter:
    """Text-to-Speech converter using Google Cloud Text-to-Speech API."""

    # Maximum bytes per request (leave some buffer below the 5000 limit)
    MAX_BYTES_PER_CHUNK = 4500

    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize the TTS converter.

        Args:
            credentials_path: Path to Google Cloud service account key file.
                            If None, uses GOOGLE_APPLICATION_CREDENTIALS env var.
        """
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        try:
            self.client = texttospeech.TextToSpeechClient()
            logger.info("TTS client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TTS client: {e}")
            raise

    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks that fit within the API byte limit.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        # If text is small enough, return as single chunk
        if len(text.encode('utf-8')) <= self.MAX_BYTES_PER_CHUNK:
            return [text]

        chunks = []
        current_chunk = ""

        # Split by sentences first for better audio flow
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if adding this sentence would exceed the limit
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            if len(test_chunk.encode('utf-8')) > self.MAX_BYTES_PER_CHUNK:
                # If current chunk has content, save it and start new chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Single sentence is too long, split by words
                    words = sentence.split()
                    for word in words:
                        test_chunk = current_chunk + " " + word if current_chunk else word
                        if len(test_chunk.encode('utf-8')) > self.MAX_BYTES_PER_CHUNK:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = word
                            else:
                                # Single word is too long, just add it (rare edge case)
                                chunks.append(word)
                                current_chunk = ""
                        else:
                            current_chunk = test_chunk
            else:
                current_chunk = test_chunk

        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _synthesize_chunk(
        self,
        text: str,
        language_code: str = "en-US",
        voice_name: str = "en-US-Neural2-D",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bytes:
        """
        Synthesize a single text chunk to audio.

        Args:
            text: Text to convert
            language_code: Language code
            voice_name: Voice name
            speaking_rate: Speaking rate
            pitch: Voice pitch

        Returns:
            Audio content as bytes

        Raises:
            Exception: If synthesis fails
        """
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code, name=voice_name
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch,
        )

        response = self.client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        return response.audio_content

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
        Convert text to speech and save as MP3. Automatically handles large texts
        by chunking and concatenating audio segments.

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

            # Check if we need to chunk the text
            text_bytes = len(text.encode('utf-8'))
            if text_bytes > self.MAX_BYTES_PER_CHUNK:
                logger.info(f"Text size ({text_bytes} bytes) exceeds limit. Chunking text...")
                return self._convert_large_text_to_speech(
                    text, output_file, language_code, voice_name, speaking_rate, pitch
                )

            # Single chunk processing
            logger.info(f"Converting text to speech: {len(text)} characters")
            audio_content = self._synthesize_chunk(
                text, language_code, voice_name, speaking_rate, pitch
            )

            # Write the response to the output file
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "wb") as out:
                out.write(audio_content)

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

    def _convert_large_text_to_speech(
        self,
        text: str,
        output_file: str,
        language_code: str = "en-US",
        voice_name: str = "en-US-Neural2-D",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
    ) -> bool:
        """
        Convert large text to speech by chunking and concatenating audio segments.

        Args:
            text: Text to convert to speech
            output_file: Path to save the MP3 file
            language_code: Language code
            voice_name: Voice name
            speaking_rate: Speaking rate
            pitch: Voice pitch

        Returns:
            True if successful, False otherwise
        """
        try:
            # Split text into chunks
            chunks = self._chunk_text(text)
            logger.info(f"Split text into {len(chunks)} chunks")

            # Process each chunk and collect audio files
            temp_files = []

            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")

                # Synthesize this chunk
                audio_content = self._synthesize_chunk(
                    chunk, language_code, voice_name, speaking_rate, pitch
                )

                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                    temp_file.write(audio_content)
                    temp_files.append(temp_file.name)

            # Concatenate using ffmpeg if available, otherwise simple binary concatenation
            logger.info("Concatenating audio segments...")
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            if self._has_ffmpeg() and len(temp_files) > 1:
                self._concatenate_with_ffmpeg(temp_files, output_file)
            else:
                # Simple binary concatenation (works for MP3)
                self._concatenate_binary(temp_files, output_file)

            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass

            logger.info(f"Combined audio content written to file: {output_file}")
            return True

        except Exception as e:
            logger.error(f"Error processing large text: {e}")
            # Clean up temporary files on error
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass
            return False

    def _has_ffmpeg(self) -> bool:
        """Check if ffmpeg is available on the system."""
        try:
            subprocess.run(['ffmpeg', '-version'],
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _concatenate_with_ffmpeg(self, temp_files: List[str], output_file: str) -> None:
        """Concatenate audio files using ffmpeg."""
        # Create a temporary file list for ffmpeg
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as list_file:
            for temp_file in temp_files:
                list_file.write(f"file '{temp_file}'\n")
            list_file_path = list_file.name

        try:
            # Use ffmpeg to concatenate
            subprocess.run([
                'ffmpeg', '-f', 'concat', '-safe', '0',
                '-i', list_file_path, '-c', 'copy', output_file, '-y'
            ], check=True, capture_output=True)
        finally:
            # Clean up the list file
            try:
                os.unlink(list_file_path)
            except OSError:
                pass

    def _concatenate_binary(self, temp_files: List[str], output_file: str) -> None:
        """Simple binary concatenation of MP3 files."""
        with open(output_file, 'wb') as outfile:
            for temp_file in temp_files:
                with open(temp_file, 'rb') as infile:
                    outfile.write(infile.read())

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


def main():
    """Command-line interface for TTS conversion."""
    if len(sys.argv) != 3:
        print(
            "Usage: python tts_converter.py '<text>' <output_file.mp3>", file=sys.stderr
        )
        sys.exit(1)

    text = sys.argv[1]
    output_file = sys.argv[2]

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
