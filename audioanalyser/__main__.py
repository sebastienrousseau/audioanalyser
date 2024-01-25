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
Enables use of Python Audio Analyser as a "main" function (i.e.
"python -m audioanalyser").

This allows using Audio Analyser with third-party libraries without modifying
their code.
"""


import argparse
import asyncio
import json
import logging
from pathlib import Path
from audioanalyser.modules.analyze_text_files import analyze_text_files
from audioanalyser.modules.audio_recorder import audio_recorder
from audioanalyser.modules.azure_recommendation import (
    azure_recommendation,
)
from audioanalyser.modules.azure_translator import azure_translator
from audioanalyser.modules.speech_text_server import speech_text_server
from audioanalyser.modules.transcribe_audio_files import (
    transcribe_audio_files,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
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
This command generates summaries based on the specified transcript.
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
            if Path(args.files[0]).is_file():
                transcribe_audio_files(args.files[0])
            else:
                logger.error("Specified audio file does not exist.")
        elif args.text_analysis:
            await analyze_text_files(args.files)
        elif args.summary:
            azure_recommendation()
        elif args.server:
            speech_text_server()
        elif args.record:
            settings = None
            if args.record != "default":
                settings = load_audio_settings(args.record)
            await audio_recorder(settings)
        elif args.translate:
            azure_translator(*args.translate)
        else:
            parser.print_help()
    except Exception as e:
        logger.error(f"An error occurred: {e}")


def load_audio_settings(file_path):
    """Loads audio settings from a JSON file.

    Args:
        file_path (str): Path to the JSON file containing the audio settings.

    Returns:
        Optional[Dict]: The audio settings, or None if an error occurred.

    Raises:
        ValueError: If the file does not exist or is not a valid JSON file.

    """
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Error loading audio settings: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(main())
