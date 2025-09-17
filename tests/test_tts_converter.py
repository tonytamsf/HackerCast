"""Tests for TTS converter module."""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from tts_converter import TTSConverter


class TestTTSConverter:
    """Test TTSConverter class."""

    @patch("tts_converter.texttospeech.TextToSpeechClient")
    def test_tts_initialization_default(self, mock_client_class):
        """Test TTS converter initialization with default credentials."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        converter = TTSConverter()

        assert converter.client == mock_client
        mock_client_class.assert_called_once()

    @patch("tts_converter.texttospeech.TextToSpeechClient")
    @patch("os.environ")
    def test_tts_initialization_with_credentials_path(
        self, mock_environ, mock_client_class
    ):
        """Test TTS converter initialization with custom credentials path."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        converter = TTSConverter(credentials_path="/path/to/credentials.json")

        assert converter.client == mock_client
        assert mock_environ.__setitem__.called

    @patch("tts_converter.texttospeech.TextToSpeechClient")
    def test_tts_initialization_failure(self, mock_client_class):
        """Test TTS converter initialization failure."""
        mock_client_class.side_effect = Exception("Failed to initialize")

        with pytest.raises(Exception, match="Failed to initialize"):
            TTSConverter()

    @patch("tts_converter.texttospeech.TextToSpeechClient")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_convert_text_to_speech_success(
        self, mock_makedirs, mock_file, mock_client_class
    ):
        """Test successful text-to-speech conversion."""
        # Setup mock client and response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.audio_content = b"fake_audio_data"
        mock_client.synthesize_speech.return_value = mock_response
        mock_client_class.return_value = mock_client

        converter = TTSConverter()
        result = converter.convert_text_to_speech(
            text="Hello world", output_file="/tmp/test.mp3"
        )

        assert result is True
        mock_client.synthesize_speech.assert_called_once()
        mock_file.assert_called_once_with("/tmp/test.mp3", "wb")
        mock_file().write.assert_called_once_with(b"fake_audio_data")

    @patch("tts_converter.texttospeech.TextToSpeechClient")
    def test_convert_text_to_speech_empty_text(self, mock_client_class):
        """Test TTS conversion with empty text."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        converter = TTSConverter()
        result = converter.convert_text_to_speech(text="", output_file="/tmp/test.mp3")

        assert result is False
        mock_client.synthesize_speech.assert_not_called()

    @patch("tts_converter.texttospeech.TextToSpeechClient")
    def test_convert_text_to_speech_long_text_warning(self, mock_client_class):
        """Test TTS conversion with very long text (should warn but proceed)."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.audio_content = b"fake_audio_data"
        mock_client.synthesize_speech.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Create text longer than 5000 characters
        long_text = "a" * 6000

        with patch("builtins.open", mock_open()):
            with patch("os.makedirs"):
                converter = TTSConverter()
                result = converter.convert_text_to_speech(
                    text=long_text, output_file="/tmp/test.mp3"
                )

                assert result is True
                mock_client.synthesize_speech.assert_called_once()

    @patch("tts_converter.texttospeech.TextToSpeechClient")
    def test_convert_text_to_speech_api_error(self, mock_client_class):
        """Test TTS conversion with Google API error."""
        from google.api_core import exceptions as gcloud_exceptions

        mock_client = Mock()
        mock_client.synthesize_speech.side_effect = gcloud_exceptions.GoogleAPIError(
            "API Error"
        )
        mock_client_class.return_value = mock_client

        converter = TTSConverter()
        result = converter.convert_text_to_speech(
            text="Hello world", output_file="/tmp/test.mp3"
        )

        assert result is False

    @patch("tts_converter.texttospeech.TextToSpeechClient")
    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_convert_text_to_speech_permission_error(
        self, mock_file, mock_client_class
    ):
        """Test TTS conversion with file permission error."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.audio_content = b"fake_audio_data"
        mock_client.synthesize_speech.return_value = mock_response
        mock_client_class.return_value = mock_client

        with patch("os.makedirs"):
            converter = TTSConverter()
            result = converter.convert_text_to_speech(
                text="Hello world", output_file="/tmp/test.mp3"
            )

            assert result is False

    @patch("tts_converter.texttospeech.TextToSpeechClient")
    def test_convert_text_to_speech_custom_parameters(self, mock_client_class):
        """Test TTS conversion with custom voice parameters."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.audio_content = b"fake_audio_data"
        mock_client.synthesize_speech.return_value = mock_response
        mock_client_class.return_value = mock_client

        with patch("builtins.open", mock_open()):
            with patch("os.makedirs"):
                converter = TTSConverter()
                result = converter.convert_text_to_speech(
                    text="Hello world",
                    output_file="/tmp/test.mp3",
                    language_code="en-GB",
                    voice_name="en-GB-Neural2-A",
                    speaking_rate=1.2,
                    pitch=2.0,
                )

                assert result is True

                # Verify the call was made with custom parameters
                call_args = mock_client.synthesize_speech.call_args
                voice_params = call_args[1]["voice"]
                audio_config = call_args[1]["audio_config"]

                assert voice_params.language_code == "en-GB"
                assert voice_params.name == "en-GB-Neural2-A"
                assert audio_config.speaking_rate == 1.2
                assert audio_config.pitch == 2.0

    @patch("tts_converter.texttospeech.TextToSpeechClient")
    def test_get_available_voices_success(self, mock_client_class):
        """Test getting available voices successfully."""
        mock_client = Mock()
        mock_voice1 = Mock()
        mock_voice1.name = "en-US-Neural2-A"
        mock_voice2 = Mock()
        mock_voice2.name = "en-US-Neural2-B"

        mock_voices_response = Mock()
        mock_voices_response.voices = [mock_voice1, mock_voice2]
        mock_client.list_voices.return_value = mock_voices_response
        mock_client_class.return_value = mock_client

        converter = TTSConverter()
        voices = converter.get_available_voices("en-US")

        assert voices == ["en-US-Neural2-A", "en-US-Neural2-B"]
        mock_client.list_voices.assert_called_once_with(language_code="en-US")

    @patch("tts_converter.texttospeech.TextToSpeechClient")
    def test_get_available_voices_error(self, mock_client_class):
        """Test getting available voices with error."""
        mock_client = Mock()
        mock_client.list_voices.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        converter = TTSConverter()
        voices = converter.get_available_voices("en-US")

        assert voices == []


class TestTTSMain:
    """Test TTS converter main function and CLI."""

    @patch("tts_converter.TTSConverter")
    @patch("sys.argv", ["tts_converter.py", "Hello world", "output.mp3"])
    def test_main_success(self, mock_converter_class):
        """Test main function with successful conversion."""
        mock_converter = Mock()
        mock_converter.convert_text_to_speech.return_value = True
        mock_converter_class.return_value = mock_converter

        from tts_converter import main

        # Should not raise any exception
        try:
            main()
        except SystemExit as e:
            # Should exit with code 0 for success
            assert e.code != 1

    @patch("tts_converter.TTSConverter")
    @patch("sys.argv", ["tts_converter.py", "Hello world", "output.mp3"])
    def test_main_conversion_failure(self, mock_converter_class):
        """Test main function with conversion failure."""
        mock_converter = Mock()
        mock_converter.convert_text_to_speech.return_value = False
        mock_converter_class.return_value = mock_converter

        from tts_converter import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["tts_converter.py", "Hello world"])
    def test_main_wrong_arguments(self):
        """Test main function with wrong number of arguments."""
        from tts_converter import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["tts_converter.py", "Hello world", "output.txt"])
    def test_main_wrong_file_extension(self):
        """Test main function with wrong output file extension."""
        from tts_converter import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("tts_converter.TTSConverter")
    @patch("sys.argv", ["tts_converter.py", "Hello world", "output.mp3"])
    def test_main_initialization_error(self, mock_converter_class):
        """Test main function with TTS initialization error."""
        mock_converter_class.side_effect = Exception("Initialization failed")

        from tts_converter import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
