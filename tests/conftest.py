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
#
"""Shared fixtures and import-time shims for the test suite.

Two things have to happen before ``audioanalyser`` is imported, so they run at
module scope rather than inside a fixture:

1. ``audio_recorder`` imports :mod:`pyaudio`, which needs the PortAudio system
   library and is not declared in any manifest. A stub keeps the suite runnable
   on machines and CI images that do not have it.
2. ``transcribe_audio_files`` reads ``AUDIO_EXTENSION`` at import time, so it
   has to be present in the environment before the first import.
"""

import os
import sys
import types
from unittest.mock import MagicMock

import pytest

# --------------------------------------------------------------------------
# Import-time shims (must precede any `audioanalyser` import)
# --------------------------------------------------------------------------

try:
    import pyaudio  # noqa: F401
except ImportError:
    # PyAudio ships wheels for Windows only; macOS and Linux build it from
    # source against PortAudio. The stub keeps the suite runnable where that
    # is absent. Where the real package is installed it is used instead, so
    # the format constants come from PortAudio rather than being asserted
    # against copies. No test opens a device: AudioRecorder tests patch
    # pyaudio.PyAudio regardless of which module is in play.
    _pyaudio = types.ModuleType("pyaudio")
    _pyaudio.paInt16 = 8
    _pyaudio.paInt24 = 4
    _pyaudio.paInt32 = 2
    _pyaudio.PyAudio = MagicMock(name="PyAudio")
    sys.modules["pyaudio"] = _pyaudio

# Read at import time by transcribe_audio_files.
os.environ.setdefault("AUDIO_EXTENSION", ".wav")


# --------------------------------------------------------------------------
# Environment fixtures
# --------------------------------------------------------------------------

# Every variable the package reads, so a test never picks up a developer's
# real credentials or a stray .env from the working tree.
ALL_ENV_VARS = (
    "ANALYSIS_DB_TABLE_NAME",
    "AUDIO_EXTENSION",
    "AZURE_AUDIO_TEXT_KEY",
    "AZURE_LANGUAGE_ENDPOINT",
    "AZURE_LANGUAGE_KEY",
    "AZURE_TRANSLATOR_ENDPOINT",
    "AZURE_TRANSLATOR_KEY",
    "CHANNELS",
    "CHUNK",
    "FORMAT",
    "GPT3_API_KEY",
    "INPUT_FOLDER",
    "MAX_OUTPUT_LENGTH",
    "OUTPUT_TONE",
    "OUTPUT_VOICE",
    "PROMPT_LENGTH_RATIO",
    "PROMPT_STRATEGY",
    "RATE",
    "RECOMMENDATIONS_FOLDER",
    "RECORD_SECONDS",
    "RECORDS_FOLDER",
    "REGION",
    "REPORTS_FOLDER",
    "TRANSCRIPTS_FOLDER",
    "TRANSLATIONS_FOLDER",
    "TRANSLATIONS_LANGUAGES",
)


@pytest.fixture
def clean_env(monkeypatch):
    """Remove every variable the package reads.

    Config classes are built from ``os.getenv`` at construction time, so this
    gives each test a known-empty starting point that monkeypatch restores.
    """
    for var in ALL_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


@pytest.fixture
def folders(tmp_path):
    """Create the folder layout the modules expect and return the paths."""
    names = (
        "input",
        "transcripts",
        "translations",
        "reports",
        "recommendations",
        "records",
    )
    paths = {}
    for name in names:
        path = tmp_path / name
        path.mkdir()
        paths[name] = path
    return paths


@pytest.fixture
def full_env(clean_env, folders):
    """Populate every variable with valid values pointing at tmp folders."""
    values = {
        "ANALYSIS_DB_TABLE_NAME": "analysis",
        "AUDIO_EXTENSION": ".wav",
        "AZURE_AUDIO_TEXT_KEY": "test-speech-key",
        "AZURE_LANGUAGE_ENDPOINT": "https://language.example.invalid",
        "AZURE_LANGUAGE_KEY": "test-language-key",
        "AZURE_TRANSLATOR_ENDPOINT": "https://translator.example.invalid",
        "AZURE_TRANSLATOR_KEY": "test-translator-key",
        "GPT3_API_KEY": "test-openai-key",
        "INPUT_FOLDER": str(folders["input"]),
        "RECOMMENDATIONS_FOLDER": str(folders["recommendations"]),
        "RECORDS_FOLDER": str(folders["records"]),
        "REGION": "westeurope",
        "REPORTS_FOLDER": str(folders["reports"]),
        "TRANSCRIPTS_DB_TABLE_NAME": "transcripts",
        "TRANSCRIPTS_FOLDER": str(folders["transcripts"]),
        "TRANSLATIONS_FOLDER": str(folders["translations"]),
        "TRANSLATIONS_LANGUAGES": "fr,es,de",
    }
    for key, value in values.items():
        clean_env.setenv(key, value)
    return values
