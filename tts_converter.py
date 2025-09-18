#!/usr/bin/env python

import os
import sys
import logging
import tempfile
import re
import subprocess
from typing import Optional, List, Tuple, Dict, NamedTuple
from datetime import datetime
from pathlib import Path
from google.cloud import texttospeech
from google.api_core import exceptions as gcloud_exceptions
from podcast_transformer import PodcastTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DialogueSegment(NamedTuple):
    """Represents a dialogue segment with speaker and text."""
    speaker: str
    text: str
    voice_config: dict


class VoiceConfig(NamedTuple):
    """Voice configuration for a speaker."""
    language_code: str = "en-US"
    voice_name: str = "en-US-Neural2-D"
    speaking_rate: float = 1.0
    pitch: float = 0.0


class TTSConverter:
    """Text-to-Speech converter using Google Cloud Text-to-Speech API."""

    # Maximum bytes per request (leave some buffer below the 5000 limit)
    MAX_BYTES_PER_CHUNK = 4500

    def __init__(self, credentials_path: Optional[str] = None, enable_podcast_transformation: bool = True):
        """
        Initialize the TTS converter.

        Args:
            credentials_path: Path to Google Cloud service account key file.
                            If None, uses GOOGLE_APPLICATION_CREDENTIALS env var.
            enable_podcast_transformation: Whether to transform text to podcast format before TTS
        """
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        try:
            self.client = texttospeech.TextToSpeechClient()
            logger.info("TTS client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TTS client: {e}")
            raise

        # Initialize podcast transformer if enabled
        self.enable_podcast_transformation = enable_podcast_transformation
        self.podcast_transformer = None
        if enable_podcast_transformation:
            try:
                self.podcast_transformer = PodcastTransformer()
                logger.info("Podcast transformer initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize podcast transformer: {e}. Continuing without podcast transformation.")
                self.enable_podcast_transformation = False

        # Define voice configurations for different speakers
        self.voice_configs = {
            "chloe": VoiceConfig(
                language_code="en-US",
                voice_name="en-US-Studio-O",  # Female Studio voice with pitch support
                speaking_rate=1.0,
                pitch=2.0  # Slightly higher pitch for female voice
            ),
            "david": VoiceConfig(
                language_code="en-US",
                voice_name="en-US-Studio-Q",  # Male Studio voice with pitch support
                speaking_rate=1.0,
                pitch=-2.0  # Slightly lower pitch for male voice
            ),
            "default": VoiceConfig(
                language_code="en-US",
                voice_name="en-US-Neural2-D",
                speaking_rate=1.0,
                pitch=0.0
            )
        }

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

    def _parse_dialogue(self, text: str) -> List[DialogueSegment]:
        """
        Parse text into dialogue segments, detecting speaker prefixes.

        Args:
            text: Text containing dialogue with speaker prefixes (e.g., "Chloe: Hello")

        Returns:
            List of DialogueSegment objects
        """
        segments = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for speaker prefix (e.g., "Chloe:", "David:")
            speaker_match = re.match(r'^(Chloe|David):\s*(.+)$', line, re.IGNORECASE)

            if speaker_match:
                speaker_name = speaker_match.group(1).lower()
                dialogue_text = speaker_match.group(2).strip()

                # Get voice config for this speaker
                voice_config = self.voice_configs.get(speaker_name, self.voice_configs["default"])

                segments.append(DialogueSegment(
                    speaker=speaker_name,
                    text=dialogue_text,
                    voice_config=voice_config._asdict()
                ))
            else:
                # No speaker prefix detected, use default voice
                voice_config = self.voice_configs["default"]
                segments.append(DialogueSegment(
                    speaker="narrator",
                    text=line,
                    voice_config=voice_config._asdict()
                ))

        return segments

    def _has_dialogue_format(self, text: str) -> bool:
        """
        Check if text contains dialogue format with speaker prefixes.

        Args:
            text: Text to check

        Returns:
            True if dialogue format is detected
        """
        # Look for lines starting with "Chloe:" or "David:"
        dialogue_pattern = r'^(Chloe|David):\s*'
        lines = text.split('\n')

        dialogue_lines = 0
        total_meaningful_lines = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            total_meaningful_lines += 1
            if re.match(dialogue_pattern, line, re.IGNORECASE):
                dialogue_lines += 1

        # Consider it dialogue format if more than 30% of lines have speaker prefixes
        if total_meaningful_lines == 0:
            return False

        dialogue_ratio = dialogue_lines / total_meaningful_lines
        return dialogue_ratio > 0.3

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

    def _convert_dialogue_to_speech(
        self,
        text: str,
        output_file: str,
    ) -> bool:
        """
        Convert dialogue-formatted text to speech with multiple voices.

        Args:
            text: Text containing dialogue with speaker prefixes
            output_file: Path to save the MP3 file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse dialogue into segments
            segments = self._parse_dialogue(text)
            if not segments:
                logger.warning("No dialogue segments found")
                return False

            logger.info(f"Processing {len(segments)} dialogue segments with multiple voices")

            # Process each segment and collect audio files
            temp_files = []

            for i, segment in enumerate(segments):
                logger.info(f"Processing segment {i+1}/{len(segments)} - {segment.speaker}: {segment.text[:50]}...")

                # Synthesize this segment with the appropriate voice
                voice_config = segment.voice_config
                audio_content = self._synthesize_chunk(
                    segment.text,
                    voice_config["language_code"],
                    voice_config["voice_name"],
                    voice_config["speaking_rate"],
                    voice_config["pitch"],
                )

                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                    temp_file.write(audio_content)
                    temp_files.append(temp_file.name)

            # Concatenate using ffmpeg if available, otherwise simple binary concatenation
            logger.info("Concatenating dialogue audio segments...")
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

            logger.info(f"🎭 Multi-voice dialogue audio written to file: {output_file}")
            return True

        except Exception as e:
            logger.error(f"Error processing dialogue: {e}")
            # Clean up temporary files on error
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass
            return False

    def _save_intermediate_script(self, script: str, topic: str = "") -> str:
        """
        Save the transformed podcast script to an intermediate file.

        Args:
            script: The podcast script to save
            topic: Optional topic for filename

        Returns:
            Path to the saved script file
        """
        # Create output/data directory if it doesn't exist
        output_dir = Path("output/data")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Clean topic for filename (remove special characters)
        clean_topic = ""
        if topic:
            clean_topic = re.sub(r'[^\w\s-]', '', topic)
            clean_topic = re.sub(r'[-\s]+', '_', clean_topic).strip('_')
            clean_topic = f"_{clean_topic}" if clean_topic else ""

        filename = f"script_{timestamp}{clean_topic}.txt"
        script_path = output_dir / filename

        # Save the script
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)

        logger.info(f"💾 Podcast script saved to: {script_path}")
        return str(script_path)

    def _transform_to_podcast(self, text: str, topic: str = "") -> Tuple[str, str]:
        """
        Transform text to podcast format using Gemini and save intermediate output.

        Args:
            text: Text to transform
            topic: Optional topic description

        Returns:
            Tuple of (transformed podcast script, path to saved script file)
        """
        if not self.enable_podcast_transformation or not self.podcast_transformer:
            # Save original text as well for consistency
            script_path = self._save_intermediate_script(text, f"original_{topic}")
            return text, script_path

        try:
            transformed_script = self.podcast_transformer.transform_to_podcast(text, topic)
            script_path = self._save_intermediate_script(transformed_script, topic)
            return transformed_script, script_path
        except Exception as e:
            logger.warning(f"Podcast transformation failed: {e}. Using original text.")
            script_path = self._save_intermediate_script(text, f"fallback_{topic}")
            return text, script_path

    def convert_text_to_speech(
        self,
        text: str,
        output_file: str,
        language_code: str = "en-US",
        voice_name: str = "en-US-Neural2-D",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        topic: str = "",
    ) -> Tuple[bool, Optional[str]]:
        """
        Convert text to speech and save as MP3. Automatically handles large texts
        by chunking and concatenating audio segments. Optionally transforms text
        to podcast format before conversion.

        Args:
            text: Text to convert to speech
            output_file: Path to save the MP3 file
            language_code: Language code (e.g., 'en-US')
            voice_name: Voice name to use
            speaking_rate: Speaking rate (0.25 to 4.0)
            pitch: Voice pitch (-20.0 to 20.0)
            topic: Topic description for podcast transformation

        Returns:
            Tuple of (success boolean, path to intermediate script file if created)
        """
        try:
            # Validate input
            if not text.strip():
                logger.error("Text input is empty")
                return False, None

            # Transform to podcast format if enabled and save intermediate output
            script_path = None
            if self.enable_podcast_transformation:
                logger.info("🎭 Transforming text to podcast format...")
                text, script_path = self._transform_to_podcast(text, topic)
                logger.info(f"📄 Using transformed script from: {script_path}")
            else:
                logger.info("⚠️  Podcast transformation disabled, using original text")

            # Check if text contains dialogue format
            if self._has_dialogue_format(text):
                logger.info("🎭 Dialogue format detected, using multi-voice conversion")
                success = self._convert_dialogue_to_speech(text, output_file)
                return success, script_path

            # Check if we need to chunk the text
            text_bytes = len(text.encode('utf-8'))
            if text_bytes > self.MAX_BYTES_PER_CHUNK:
                logger.info(f"Text size ({text_bytes} bytes) exceeds limit. Chunking text...")
                success = self._convert_large_text_to_speech(
                    text, output_file, language_code, voice_name, speaking_rate, pitch
                )
                return success, script_path

            # Single chunk processing
            logger.info(f"Converting text to speech: {len(text)} characters")
            audio_content = self._synthesize_chunk(
                text, language_code, voice_name, speaking_rate, pitch
            )

            # Write the response to the output file
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "wb") as out:
                out.write(audio_content)

            logger.info(f"🎵 Audio content written to file: {output_file}")
            if script_path:
                logger.info(f"📄 Intermediate script available at: {script_path}")
            return True, script_path

        except gcloud_exceptions.GoogleAPIError as e:
            logger.error(f"Google Cloud API error: {e}")
            return False, script_path
        except PermissionError as e:
            logger.error(f"Permission error writing to {output_file}: {e}")
            return False, script_path
        except Exception as e:
            logger.error(f"Unexpected error during TTS conversion: {e}")
            return False, script_path

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
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print(
            "Usage: python tts_converter.py '<text>' <output_file.mp3> [topic]", file=sys.stderr
        )
        sys.exit(1)

    text = sys.argv[1]
    output_file = sys.argv[2]
    topic = sys.argv[3] if len(sys.argv) == 4 else ""

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
        success, script_path = converter.convert_text_to_speech(text, output_file, topic=topic)

        if success:
            print(f"Successfully converted text to speech: {output_file}")
            if script_path:
                print(f"Intermediate script saved to: {script_path}")
        else:
            print("Failed to convert text to speech", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
