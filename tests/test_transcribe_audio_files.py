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
"""Tests for audioanalyser.modules.transcribe_audio_files."""

import json
import logging
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from audioanalyser.modules import transcribe_audio_files as taf


@pytest.fixture
def env(full_env, clean_env):
    """full_env plus the table name this module needs."""
    clean_env.setenv("TRANSCRIPTS_DB_TABLE_NAME", "transcripts")
    return full_env


def _recognizer(results=("hello world",), *, stop=True):
    """Build a recognizer whose callbacks fire when recognition starts."""
    recognizer = MagicMock()
    handlers = {}

    for name in ("recognized", "canceled", "session_stopped"):
        getattr(recognizer, name).connect.side_effect = (
            lambda fn, key=name: handlers.__setitem__(key, fn)
        )

    def start():
        for text in results:
            event = MagicMock()
            event.result.text = text
            handlers["recognized"](event)
        if stop:
            handlers["session_stopped"](MagicMock())

    recognizer.start_continuous_recognition.side_effect = start
    recognizer._handlers = handlers
    return recognizer


class TestConfig:
    def test_reads_every_setting_from_the_environment(self, env):
        config = taf.Config()

        assert config.api_key == "test-speech-key"
        assert config.region == "westeurope"
        assert config.transcripts_db_table_name == "transcripts"

    @pytest.mark.parametrize(
        "missing",
        [
            "AZURE_AUDIO_TEXT_KEY",
            "REGION",
            "INPUT_FOLDER",
            "TRANSCRIPTS_FOLDER",
            "TRANSCRIPTS_DB_TABLE_NAME",
        ],
    )
    def test_raises_when_a_required_variable_is_absent(
        self, env, clean_env, missing
    ):
        clean_env.delenv(missing)

        with pytest.raises(EnvironmentError, match="Missing required"):
            taf.Config()


class TestSpeechToTextRecognition:
    def test_collects_every_recognised_phrase(self, env):
        recognizer = _recognizer(("first", "second"))

        with patch.object(
            taf.speechsdk, "SpeechRecognizer", return_value=recognizer
        ):
            with patch.object(taf.speechsdk, "SpeechConfig"):
                with patch.object(taf.speechsdk.audio, "AudioConfig"):
                    results = taf.SpeechToText(
                        taf.Config()
                    ).speech_to_text_long("a.wav")

        assert results == ["first", "second"]

    def test_warns_when_nothing_is_recognised(self, env, caplog):
        recognizer = _recognizer(())

        with patch.object(
            taf.speechsdk, "SpeechRecognizer", return_value=recognizer
        ):
            with patch.object(taf.speechsdk, "SpeechConfig"):
                with patch.object(taf.speechsdk.audio, "AudioConfig"):
                    results = taf.SpeechToText(
                        taf.Config()
                    ).speech_to_text_long("a.wav")

        assert results == []
        assert "No results for a.wav" in caplog.text

    @pytest.mark.parametrize(
        ("reason", "expected"),
        [
            ("EndOfStream", "End of audio stream reached"),
            ("Error", "Recognition canceled due to an error"),
            ("other", "Recognition canceled: Reason="),
        ],
    )
    def test_cancellation_paths_are_logged(
        self, env, caplog, reason, expected
    ):
        # The EndOfStream branch logs at INFO, below caplog's
        # default threshold.
        caplog.set_level(logging.INFO)
        recognizer = _recognizer((), stop=False)

        def start():
            event = MagicMock()
            event.result.reason = taf.speechsdk.ResultReason.Canceled
            details = event.result.cancellation_details
            details.error_details = "boom"
            if reason == "EndOfStream":
                details.reason = taf.speechsdk.CancellationReason.EndOfStream
            elif reason == "Error":
                details.reason = taf.speechsdk.CancellationReason.Error
            else:
                details.reason = "SomethingElse"
            recognizer._handlers["canceled"](event)

        recognizer.start_continuous_recognition.side_effect = start

        with patch.object(
            taf.speechsdk, "SpeechRecognizer", return_value=recognizer
        ):
            with patch.object(taf.speechsdk, "SpeechConfig"):
                with patch.object(taf.speechsdk.audio, "AudioConfig"):
                    taf.SpeechToText(taf.Config()).speech_to_text_long("a.wav")

        assert expected in caplog.text

    def test_non_cancellation_errors_are_logged(self, env, caplog):
        recognizer = _recognizer((), stop=False)

        def start():
            event = MagicMock()
            event.result.reason = "NoMatch"
            recognizer._handlers["canceled"](event)

        recognizer.start_continuous_recognition.side_effect = start

        with patch.object(
            taf.speechsdk, "SpeechRecognizer", return_value=recognizer
        ):
            with patch.object(taf.speechsdk, "SpeechConfig"):
                with patch.object(taf.speechsdk.audio, "AudioConfig"):
                    taf.SpeechToText(taf.Config()).speech_to_text_long("a.wav")

        assert "Recognition error" in caplog.text


class TestWriters:
    def test_write_to_file_writes_one_line_per_result(self, env, tmp_path):
        out = tmp_path / "a.txt"

        taf.SpeechToText(taf.Config()).write_to_file(out, ["one", "two"])

        assert out.read_text() == "one\ntwo\n"

    def test_write_to_json_serialises_the_results(self, env, tmp_path):
        out = tmp_path / "a.json"

        taf.SpeechToText(taf.Config()).write_to_json(out, ["one"])

        assert json.loads(out.read_text()) == ["one"]

    def test_write_to_sqlite_creates_the_table_and_rows(self, env, tmp_path):
        db = tmp_path / "a.db"

        taf.SpeechToText(taf.Config()).write_to_sqlite(db, "a.wav", ["one"])

        with sqlite3.connect(db) as conn:
            rows = conn.execute(
                "SELECT filename, transcription FROM transcripts"
            ).fetchall()
        assert rows == [("a.wav", "one")]


class TestProcessing:
    def test_process_file_writes_all_three_outputs(self, env, folders):
        audio = folders["input"] / "call.wav"
        audio.write_bytes(b"RIFF")
        processor = taf.SpeechToText(taf.Config())

        with patch.object(
            processor, "speech_to_text_long", return_value=["hello"]
        ):
            processor.process_file(str(audio))

        assert (folders["transcripts"] / "call.txt").read_text() == "hello\n"
        assert json.loads(
            (folders["transcripts"] / "call.json").read_text()
        ) == ["hello"]
        assert (folders["transcripts"] / "transcriptions.db").exists()

    def test_process_file_writes_nothing_when_there_are_no_results(
        self, env, folders
    ):
        audio = folders["input"] / "call.wav"
        audio.write_bytes(b"RIFF")
        processor = taf.SpeechToText(taf.Config())

        with patch.object(processor, "speech_to_text_long", return_value=[]):
            processor.process_file(str(audio))

        assert not list(folders["transcripts"].iterdir())

    def test_processes_a_single_named_file(self, env, folders):
        audio = folders["input"] / "one.wav"
        audio.write_bytes(b"RIFF")
        processor = taf.SpeechToText(taf.Config())

        with patch.object(processor, "process_file") as process_file:
            processor.process_audio_files(str(audio))

        process_file.assert_called_once_with(str(audio))

    def test_logs_when_the_named_file_is_missing(self, env, folders, caplog):
        processor = taf.SpeechToText(taf.Config())

        processor.process_audio_files(str(folders["input"] / "absent.wav"))

        assert "File not found" in caplog.text

    def test_processes_every_matching_file_in_the_input_folder(
        self, env, folders
    ):
        (folders["input"] / "a.wav").write_bytes(b"RIFF")
        (folders["input"] / "b.wav").write_bytes(b"RIFF")
        (folders["input"] / "notes.txt").write_text("skip me")
        processor = taf.SpeechToText(taf.Config())

        with patch.object(processor, "process_file") as process_file:
            processor.process_audio_files()

        processed = sorted(
            c.args[0].rsplit("/", 1)[-1] for c in process_file.call_args_list
        )
        assert processed == ["a.wav", "b.wav"]

    def test_logs_when_a_listed_file_vanishes_before_processing(
        self, env, folders, caplog
    ):
        # os.listdir sees the file but it is gone by the time it is opened.
        (folders["input"] / "ghost.wav").write_bytes(b"RIFF")
        processor = taf.SpeechToText(taf.Config())

        with patch.object(taf.os.path, "exists", return_value=False):
            with patch.object(processor, "process_file") as process_file:
                processor.process_audio_files()

        process_file.assert_not_called()
        assert "File not found" in caplog.text


class TestEntryPoint:
    def test_transcribes_the_requested_file(self, env, folders):
        audio = folders["input"] / "call.wav"
        audio.write_bytes(b"RIFF")

        with patch.object(
            taf.SpeechToText, "speech_to_text_long", return_value=["hi"]
        ):
            taf.transcribe_audio_files(str(audio))

        assert (folders["transcripts"] / "call.txt").read_text() == "hi\n"

    def test_logs_instead_of_raising_when_configuration_is_invalid(
        self, env, clean_env, caplog
    ):
        clean_env.delenv("REGION")

        taf.transcribe_audio_files()

        assert "Script execution failed" in caplog.text
