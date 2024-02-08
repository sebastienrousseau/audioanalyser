# Copyright (C) 2023-2024 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=invalid-name
"""
This script provides a command-line interface (CLI) for audio analysis tasks
such as speech to text conversion, text analysis, text to speech conversion,
audio recording, translation, and server operation.

It supports various functionalities including:
- Speech to text conversion using Azure Cognitive Services.
- Text analysis including sentiment analysis, entity recognition, key phrase
extraction, and language detection.
- Text to speech conversion using Azure Cognitive Services.
- Audio recording with optional settings specified in a JSON file.
- Translation between languages.
- Starting an Audio Analyser server with a web UI and REST API.

For more detailed information on each command, use the --help option with the
respective command.
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from audioanalyser.modules.analyze_text_files import analyze_text_files
from audioanalyser.modules.audio_recorder import audio_recorder
from audioanalyser.modules.azure_recommendation import azure_recommendation
from audioanalyser.modules.azure_translator import azure_translator
from audioanalyser.modules.speech_text_server import speech_text_server
from audioanalyser.modules.transcribe_audio_files import transcribe_audio_files
from audioanalyser.modules.text_to_speech import text_to_speech


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@staticmethod
def validate_args(args):
    """
    Validates the arguments passed to the function.

    Args:
        args (Namespace): The command line arguments.

    Returns:
        bool: True if all file paths exist, False otherwise.
    """
    for file_path in args.files:
        if not Path(file_path).is_file():
            logger.error(f"Specified file '{file_path}' does not exist.")
            return False
    return True


@staticmethod
def save_results(data, output_file):
    """
    Saves results to a JSON file.

    Args:
        data (dict): The data to save.
        output_file (str): The output file path.
    """
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=4)


@staticmethod
async def process_speech_to_text(args):
    """
    Processes speech to text.

    Args:
        args (Namespace): The command line arguments.
    """
    print("Args:", args)
    if args.text and validate_args(args):
        transcribe_audio_files(args.text)
    else:
        logger.error("No audio files specified.")


@staticmethod
async def process_text_analysis(args):
    """
    Processes text analysis.

    Args:
        args (Namespace): The command line arguments.
    """
    if validate_args(args):
        await analyze_text_files(args.files)


@staticmethod
async def process_text_to_speech(args):
    """
    Processes text to speech conversion.

    Args:
        args (Namespace): The command line arguments.
    """
    if validate_args(args):
        if args.text and args.name:
            text_to_speech(args.text, args.name)
        else:
            logger.error(
                "Text and name arguments are required for text-to-speech"
            )


@staticmethod
def process_audio_recording(args):
    """
    Processes audio recording.

    Args:
        args (Namespace): The command line arguments.
    """
    settings = None
    if args.record != "default":
        settings = load_audio_settings(args.record)
    audio_recorder(settings)


@staticmethod
def process_translation(args):
    """
    Processes translation.

    Args:
        args (Namespace): The command line arguments.
    """
    if validate_args(args):
        azure_translator(*args.translate)


@staticmethod
def start_server():
    """
    Starts the Audio Analyser server.
    """
    speech_text_server()


@staticmethod
def load_audio_settings(file_path):
    """
    Loads audio settings from a JSON file.

    Args:
        file_path (str): Path to the JSON settings file.

    Returns:
        dict: Loaded audio settings.
    """
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Error loading audio settings: {e}")
        return None


@staticmethod
async def main():
    """
    Main function to parse command line arguments and execute
    corresponding actions.
    """
    parser = argparse.ArgumentParser(
        prog="audioanalyser", description="Audio Analyser CLI"
    )

    parser.add_argument(
        "-stt",
        "--speech_to_text",
        action="store_true",
        help="""
This command processes audio files in the specified sample folder,
converting speech to text using Azure Cognitive Services.
It supports long audio recognition and handles various speech
recognition events. Results are saved as text and JSON files, and
transcriptions are also stored in a SQLite database.
Ideal for transcribing lectures, meetings, or interviews.
        """,
    )

    parser.add_argument(
        "-ta",
        "--text_analysis",
        action="store_true",
        help="""
This command processes text files in the specified transcript folder.
It performs sentiment analysis, entity recognition, key phrase
extraction, and language detection. Results are saved in text and JSON
formats, and a summary is stored in a SQLite database.
Suitable for analysing transcripts for insights and important data
points.
        """,
    )

    parser.add_argument(
        "-sum",
        "--summary",
        action="store_true",
        help="""
This command generates summaries based on the specified transcript folder. It
can be used to generate reports for insights and important data points from
transcripts. Results are saved in text and JSON formats, and also in a SQLite
database.
        """,
    )

    parser.add_argument(
        "-rec",
        "--record",
        nargs="?",
        const="default",
        help="Record audio. Optionally specify settings file (JSON)."
    )

    parser.add_argument(
        "-tts",
        "--text_to_speech",
        action="store_true",
        help="""
        This command converts text to speech using Azure Cognitive Services.
        It supports long audio recognition and handles various speech
        recognition events. Results are saved as audio files in the specified
        output folder.
        """
    )

    parser.add_argument(
        "text",
        nargs="?",
        default="",
        help="Text to convert to speech"
    )

    parser.add_argument(
        "name",
        nargs="?",
        default="",
        help="Name of the audio file"
    )

    parser.add_argument(
        "-s",
        "--server",
        action="store_true",
        help="""
This command starts the Audio Analyser server, which provides a web UI for
activating the audio files transcription, viewing transcripts, analysing them,
and generating reports. It also provides a REST API for interacting with the
server.
        """,
    )
    parser.add_argument(
        "-t",
        "--translate",
        nargs="*",
        default=None,
        help="Language codes for translation, e.g., -l en fr de"
    )
    parser.add_argument(
        "files", nargs="*", help="File paths to process"
    )

    args = parser.parse_args()

    try:
        if args.speech_to_text:
            await process_speech_to_text(args)
        elif args.text_analysis:
            await process_text_analysis(args)
        elif args.text_to_speech:
            await process_text_to_speech(args)
        elif args.summary:
            azure_recommendation()
        elif args.server:
            start_server()
        elif args.record:
            process_audio_recording(args)
        elif args.translate:
            process_translation(args)
        else:
            parser.print_help()
    except Exception as e:
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
