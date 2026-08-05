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
"""Tests for the audioanalyser command line interface.

Note the module decorates its module-level functions with @staticmethod. That
only became callable in Python 3.10, so importing and invoking this CLI is
impossible on 3.9 - which the package declared support for until recently.
"""

import asyncio
import json
from argparse import Namespace
from unittest.mock import AsyncMock, patch

from audioanalyser import __main__ as cli


def _args(**overrides):
    defaults = {
        "speech_to_text": False,
        "text_analysis": False,
        "summary": False,
        "record": None,
        "text_to_speech": False,
        "text": "",
        "name": "",
        "server": False,
        "translate": None,
        "files": [],
    }
    defaults.update(overrides)
    return Namespace(**defaults)


def _run_main(argv):
    with patch.object(
        cli.sys if hasattr(cli, "sys") else cli, "argv", create=True
    ):
        pass
    return asyncio.run(cli.main())


class TestValidateArgs:
    def test_accepts_existing_files(self, tmp_path):
        one = tmp_path / "one.txt"
        one.write_text("x")

        assert cli.validate_args(_args(files=[str(one)])) is True

    def test_accepts_an_empty_file_list(self):
        assert cli.validate_args(_args(files=[])) is True

    def test_rejects_a_missing_file_and_logs_it(self, tmp_path, caplog):
        missing = str(tmp_path / "absent.txt")

        assert cli.validate_args(_args(files=[missing])) is False
        assert "does not exist" in caplog.text


class TestSaveResults:
    def test_writes_indented_json(self, tmp_path):
        target = tmp_path / "out.json"

        cli.save_results({"a": 1}, target)

        assert json.loads(target.read_text()) == {"a": 1}


class TestLoadAudioSettings:
    def test_reads_a_settings_file(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text('{"channels": 2}')

        assert cli.load_audio_settings(path) == {"channels": 2}

    def test_returns_none_and_logs_on_bad_input(self, tmp_path, caplog):
        assert cli.load_audio_settings(tmp_path / "absent.json") is None
        assert "Error loading audio settings" in caplog.text


class TestProcessSpeechToText:
    def test_transcribes_the_named_file(self, tmp_path):
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"RIFF")
        args = _args(text=str(audio), files=[str(audio)])

        with patch.object(cli, "transcribe_audio_files") as transcribe:
            asyncio.run(cli.process_speech_to_text(args))

        transcribe.assert_called_once_with(str(audio))

    def test_logs_when_no_audio_file_is_given(self, caplog):
        with patch.object(cli, "transcribe_audio_files") as transcribe:
            asyncio.run(cli.process_speech_to_text(_args(text="")))

        transcribe.assert_not_called()
        assert "No audio files specified." in caplog.text

    def test_logs_when_the_referenced_file_is_missing(self, tmp_path, caplog):
        args = _args(text="something", files=[str(tmp_path / "absent.wav")])

        with patch.object(cli, "transcribe_audio_files") as transcribe:
            asyncio.run(cli.process_speech_to_text(args))

        transcribe.assert_not_called()
        assert "No audio files specified." in caplog.text


class TestProcessTextAnalysis:
    def test_analyses_the_given_files(self, tmp_path):
        one = tmp_path / "one.txt"
        one.write_text("hello")

        with patch.object(
            cli, "analyze_text_files", new=AsyncMock()
        ) as analyse:
            asyncio.run(cli.process_text_analysis(_args(files=[str(one)])))

        analyse.assert_awaited_once_with([str(one)])

    def test_skips_analysis_when_a_file_is_missing(self, tmp_path):
        with patch.object(
            cli, "analyze_text_files", new=AsyncMock()
        ) as analyse:
            asyncio.run(
                cli.process_text_analysis(
                    _args(files=[str(tmp_path / "absent.txt")])
                )
            )

        analyse.assert_not_awaited()


class TestProcessTextToSpeech:
    def test_synthesises_when_text_and_name_are_present(self):
        args = _args(text="hello", name="greeting")

        with patch.object(cli, "text_to_speech") as tts:
            asyncio.run(cli.process_text_to_speech(args))

        tts.assert_called_once_with("hello", "greeting")

    def test_logs_when_text_or_name_is_missing(self, caplog):
        with patch.object(cli, "text_to_speech") as tts:
            asyncio.run(
                cli.process_text_to_speech(_args(text="hello", name=""))
            )

        tts.assert_not_called()
        assert "Text and name arguments are required" in caplog.text

    def test_skips_when_a_referenced_file_is_missing(self, tmp_path):
        args = _args(
            text="hello", name="greeting", files=[str(tmp_path / "absent.txt")]
        )

        with patch.object(cli, "text_to_speech") as tts:
            asyncio.run(cli.process_text_to_speech(args))

        tts.assert_not_called()


class TestProcessAudioRecording:
    def test_records_with_defaults(self):
        with patch.object(cli, "audio_recorder") as recorder:
            cli.process_audio_recording(_args(record="default"))

        recorder.assert_called_once_with(None)

    def test_records_with_settings_loaded_from_a_file(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text('{"channels": 2}')

        with patch.object(cli, "audio_recorder") as recorder:
            cli.process_audio_recording(_args(record=str(path)))

        recorder.assert_called_once_with({"channels": 2})


class TestProcessTranslation:
    def test_translates_with_the_requested_languages(self, tmp_path):
        one = tmp_path / "one.txt"
        one.write_text("hello")
        args = _args(translate=["fr", "de"], files=[str(one)])

        with patch.object(cli, "azure_translator") as translator:
            cli.process_translation(args)

        translator.assert_called_once_with("fr", "de")

    def test_skips_when_a_referenced_file_is_missing(self, tmp_path):
        args = _args(translate=["fr"], files=[str(tmp_path / "absent.txt")])

        with patch.object(cli, "azure_translator") as translator:
            cli.process_translation(args)

        translator.assert_not_called()


class TestStartServer:
    def test_delegates_to_the_server_module(self):
        with patch.object(cli, "speech_text_server") as server:
            cli.start_server()

        server.assert_called_once_with()


class TestMain:
    def _main_with(self, argv):
        with patch("sys.argv", ["audioanalyser", *argv]):
            asyncio.run(cli.main())

    def test_speech_to_text_flag_dispatches(self, tmp_path):
        audio = tmp_path / "a.wav"
        audio.write_bytes(b"RIFF")

        with patch.object(
            cli, "process_speech_to_text", new=AsyncMock()
        ) as handler:
            self._main_with(["-stt", str(audio)])

        handler.assert_awaited_once()

    def test_text_analysis_flag_dispatches(self):
        with patch.object(
            cli, "process_text_analysis", new=AsyncMock()
        ) as handler:
            self._main_with(["-ta"])

        handler.assert_awaited_once()

    def test_text_to_speech_flag_dispatches(self):
        with patch.object(
            cli, "process_text_to_speech", new=AsyncMock()
        ) as handler:
            self._main_with(["-tts", "hello", "greeting"])

        handler.assert_awaited_once()

    def test_summary_flag_dispatches(self):
        with patch.object(cli, "azure_recommendation") as handler:
            self._main_with(["-sum"])

        handler.assert_called_once_with()

    def test_server_flag_dispatches(self):
        with patch.object(cli, "start_server") as handler:
            self._main_with(["-s"])

        handler.assert_called_once_with()

    def test_record_flag_dispatches(self):
        with patch.object(cli, "process_audio_recording") as handler:
            self._main_with(["-rec"])

        handler.assert_called_once()

    def test_translate_flag_dispatches(self):
        with patch.object(cli, "process_translation") as handler:
            self._main_with(["-t", "fr"])

        handler.assert_called_once()

    def test_prints_help_when_no_flag_is_given(self, capsys):
        self._main_with([])

        assert "Audio Analyser CLI" in capsys.readouterr().out

    def test_logs_instead_of_raising_when_a_handler_fails(self, caplog):
        with patch.object(
            cli, "start_server", side_effect=RuntimeError("server down")
        ):
            self._main_with(["-s"])

        assert "An error occurred: server down" in caplog.text


class TestPackageMetadata:
    def test_exposes_a_version(self):
        import audioanalyser

        assert audioanalyser.__version__
