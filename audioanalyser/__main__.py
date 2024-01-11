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
from audioanalyser.modules.azure_speech_to_text import azure_speech_to_text
from audioanalyser.modules.azure_text_analysis import azure_text_analysis
from audioanalyser.modules.server import audio_analyser_server
from audioanalyser.modules.azure_recommendation import azure_recommendation
from audioanalyser.modules.audio_recorder import audio_recorder


def main():
    parser = argparse.ArgumentParser(
        prog='audioanalyser',
        description='Audio Analyser CLI'
    )
    parser.add_argument(
        '-stt',
        '--speech_to_text',
        action='store_true',
        help='''
This command processes audio files in the specified sample folder,
converting speech to text using Azure Cognitive Services.
It supports long audio recognition and handles various speech
recognition events. Results are saved as text and JSON files, and
transcriptions are also stored in a SQLite database.
Ideal for transcribing lectures, meetings, or interviews.
        '''
    )
    parser.add_argument(
        '-ta',
        '--text_analysis',
        action='store_true',
        help='''
This command processes text files in the specified transcript folder.
It performs sentiment analysis, entity recognition, key phrase
extraction, and language detection. Results are saved in text and JSON
formats, and a summary is stored in a SQLite database.
Suitable for analysing transcripts for insights and important data
points.
        '''
    )
    parser.add_argument(
        '-sum',
        '--summary',
        action='store_true',
        help='''
This command generates summaries based on the specified transcript.
        '''
    )
    parser.add_argument(
        '-rec',
        '--record',
        action='store_true',
        help='''
This command records audio from the microphone and saves it as a WAV file.
        '''
    )
    parser.add_argument(
        '-s',
        '--server',
        action='store_true',
        help='''
This command starts the Audio Analyser server, which provides a web UI for
activating the audio files transcription, viewing transcripts, analysing them,
and generating reports. It also provides a REST API for interacting with the
server.
        '''
    )

    args = parser.parse_args()
    if args.speech_to_text:
        azure_speech_to_text()
    elif args.text_analysis:
        azure_text_analysis()
    elif args.summary:
        azure_recommendation()
    elif args.server:
        audio_analyser_server()
    elif args.record:
        audio_recorder()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
