#!/usr/bin/env python

# NOTE: This script requires authentication with Google Cloud.
# See: https://cloud.google.com/docs/authentication/getting-started
# You will need to set the GOOGLE_APPLICATION_CREDENTIALS environment variable.

import sys
from google.cloud import texttospeech

def text_to_mp3(text, output_file):
    """Converts a text string to an MP3 file using Google Cloud Text-to-Speech."""
    try:
        # Instantiates a client
        client = texttospeech.TextToSpeechClient()

        # Set the text input to be synthesized
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Build the voice request, select a language code ("en-US") and the ssml
        # voice gender ("neutral")
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )

        # Select the type of audio file you want returned
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        # Perform the text-to-speech request on the text input with the selected
        # voice parameters and audio file type
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # The response's audio_content is binary.
        with open(output_file, "wb") as out:
            # Write the response to the output file.
            out.write(response.audio_content)
            print(f'Audio content written to file "{output_file}"')

    except Exception as e:
        print(f"Error converting text to speech: {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python tts_converter.py <text_to_speak> <output_file.mp3>", file=sys.stderr)
        sys.exit(1)

    text_to_speak = sys.argv[1]
    output_file = sys.argv[2]

    text_to_mp3(text_to_speak, output_file)