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
"""Tests for audioanalyser.modules.speech_text_server.

The endpoints are ordinary methods - cherrypy's decorators only attach
attributes - so they are called directly rather than over HTTP.
"""

import os
import signal
from unittest.mock import MagicMock, patch

import cherrypy
import pytest

from audioanalyser.modules import speech_text_server as sts


@pytest.fixture
def server():
    return sts.SpeechTextAnalysisServer()


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """A working directory laid out the way the endpoints expect."""
    for relative in (
        "dashboard",
        "resources/input",
        "resources/transcripts",
        "resources/reports",
        "resources/recommendations",
        "resources/translations",
    ):
        (tmp_path / relative).mkdir(parents=True)
    (tmp_path / "dashboard" / "index.html").write_text("<h1>dashboard</h1>")
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestIndex:
    def test_serves_the_dashboard_file(self, server, workspace):
        handle = server.index()

        try:
            assert handle.read() == "<h1>dashboard</h1>"
        finally:
            handle.close()


class TestSpeechToTextEndpoint:
    def test_reports_completion_and_restores_stdout(self, server, workspace):
        before = sts.sys.stdout

        with patch.object(sts, "transcribe_audio_files") as transcribe:
            result = server.process_all_speech_to_text()

        transcribe.assert_called_once_with()
        assert result["result"] == "Processing completed"
        assert sts.sys.stdout is before

    def test_captures_stdout_as_logs(self, server, workspace):
        with patch.object(
            sts, "transcribe_audio_files", side_effect=lambda: print("working")
        ):
            result = server.process_all_speech_to_text()

        assert "working" in result["logs"]

    def test_returns_500_on_failure(self, server, workspace):
        with patch.object(
            sts, "transcribe_audio_files", side_effect=RuntimeError("boom")
        ):
            result = server.process_all_speech_to_text()

        assert cherrypy.response.status == 500
        assert "error" in result


class TestTextToSpeechEndpoint:
    def test_forwards_every_argument(self, server, workspace):
        with patch.object(sts, "text_to_speech") as tts:
            result = server.text_to_speech(
                "hello", "greeting", "fr-FR", "voice"
            )

        tts.assert_called_once_with("hello", "greeting", "fr-FR", "voice")
        assert result["result"] == "Processing completed"

    def test_applies_the_default_language_and_voice(self, server, workspace):
        with patch.object(sts, "text_to_speech") as tts:
            server.text_to_speech("hello", "greeting")

        tts.assert_called_once_with(
            "hello", "greeting", "en-GB", "en-GB-RyanNeural"
        )

    def test_returns_500_on_failure(self, server, workspace):
        with patch.object(
            sts, "text_to_speech", side_effect=ValueError("bad")
        ):
            result = server.text_to_speech("hello", "greeting")

        assert cherrypy.response.status == 500
        assert "error" in result


class TestRecordAudioEndpoint:
    def test_returns_the_recorded_file_path(self, server, workspace):
        with patch.object(sts, "audio_recorder", return_value="/tmp/a.wav"):
            result = server.record_audio()

        assert result["recorded_file"] == "/tmp/a.wav"
        assert result["result"] == "Recording completed"

    def test_returns_500_when_recording_yields_nothing(
        self, server, workspace
    ):
        with patch.object(sts, "audio_recorder", return_value=None):
            result = server.record_audio()

        assert cherrypy.response.status == 500
        assert result["error"] == "Failed to record audio."

    def test_returns_500_when_the_recorder_raises(self, server, workspace):
        with patch.object(
            sts, "audio_recorder", side_effect=OSError("no device")
        ):
            result = server.record_audio()

        assert cherrypy.response.status == 500
        assert "no device" in result["error"]


class TestListAudioFiles:
    def test_lists_only_wav_files(self, server, workspace):
        inputs = workspace / "resources" / "input"
        (inputs / "one.wav").write_bytes(b"RIFF")
        (inputs / "two.wav").write_bytes(b"RIFF")
        (inputs / "notes.txt").write_text("skip")
        (inputs / "nested").mkdir()

        files = server.list_audio_files()

        assert sorted(f["name"] for f in files) == ["one.wav", "two.wav"]
        assert all(os.path.isabs(f["full_path"]) for f in files)

    def test_returns_500_when_the_folder_is_missing(
        self, server, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)

        result = server.list_audio_files()

        assert cherrypy.response.status == 500
        assert "error" in result


class TestServeAndDownload:
    def test_serve_audio_delegates_to_cherrypy_static(self, server, workspace):
        (workspace / "resources" / "input" / "a.wav").write_bytes(b"RIFF")

        with patch.object(
            cherrypy.lib.static, "serve_file", return_value="served"
        ) as serve:
            assert server.serve_audio("a.wav") == "served"

        assert serve.call_args.kwargs["content_type"] == "audio/wav"

    def test_serve_audio_returns_500_on_failure(self, server, workspace):
        with patch.object(
            cherrypy.lib.static, "serve_file", side_effect=OSError("gone")
        ):
            result = server.serve_audio("a.wav")

        assert cherrypy.response.status == 500
        assert "error" in result

    def test_download_audio_sets_the_attachment_header(
        self, server, workspace
    ):
        with patch.object(
            cherrypy.lib.static, "serve_file", return_value="served"
        ) as serve:
            assert server.download_audio("a.wav") == "served"

        header = cherrypy.response.headers["Content-Disposition"]
        assert header == 'attachment; filename="a.wav"'
        assert (
            serve.call_args.kwargs["content_type"]
            == "application/octet-stream"
        )

    def test_download_audio_returns_500_on_failure(self, server, workspace):
        with patch.object(
            cherrypy.lib.static, "serve_file", side_effect=OSError("gone")
        ):
            result = server.download_audio("a.wav")

        assert cherrypy.response.status == 500
        assert "error" in result


class TestTextAnalysisEndpoint:
    def test_starts_a_worker_thread(self, server, workspace):
        with patch.object(sts.threading, "Thread") as thread:
            result = server.process_text_analysis()

        thread.assert_called_once_with(target=server.run_analysis_thread)
        thread.return_value.start.assert_called_once()
        assert result["result"] == "Text analysis process started"

    def test_returns_500_when_the_thread_cannot_start(self, server, workspace):
        with patch.object(
            sts.threading, "Thread", side_effect=RuntimeError("no threads")
        ):
            result = server.process_text_analysis()

        assert cherrypy.response.status == 500
        assert "error" in result

    def test_worker_writes_completed_on_success(self, server, workspace):
        with patch.object(sts.asyncio, "run") as run:
            server.run_analysis_thread()

        run.assert_called_once()
        assert (workspace / "analysis_status.txt").read_text() == "Completed"

    def test_worker_writes_the_error_on_failure(self, server, workspace):
        with patch.object(
            sts.asyncio, "run", side_effect=RuntimeError("boom")
        ):
            server.run_analysis_thread()

        assert (workspace / "analysis_status.txt").read_text() == "Error: boom"

    def test_status_reports_processing_before_the_file_exists(
        self, server, workspace
    ):
        assert server.get_analysis_status() == {"status": "Processing"}

    def test_status_reports_the_file_contents_once_written(
        self, server, workspace
    ):
        (workspace / "analysis_status.txt").write_text("Completed")

        assert server.get_analysis_status() == {"status": "Completed"}


class TestListingEndpoints:
    @pytest.mark.parametrize(
        ("method", "folder"),
        [
            ("get_transcripts_list", "resources/transcripts"),
            ("get_reports_list", "resources/reports"),
            ("get_summaries_list", "resources/recommendations"),
            ("get_translations_list", "resources/translations"),
        ],
    )
    def test_returns_filename_and_content_for_each_txt_file(
        self, server, workspace, method, folder
    ):
        (workspace / folder / "one.txt").write_text("content one")
        (workspace / folder / "skip.md").write_text("ignored")

        items = getattr(server, method)()

        assert items == [{"filename": "one.txt", "content": "content one"}]

    @pytest.mark.parametrize(
        "method",
        [
            "get_transcripts_list",
            "get_reports_list",
            "get_summaries_list",
            "get_translations_list",
        ],
    )
    def test_returns_an_empty_list_when_the_folder_is_absent(
        self, server, tmp_path, monkeypatch, method
    ):
        monkeypatch.chdir(tmp_path)

        assert getattr(server, method)() == []

    @pytest.mark.parametrize(
        "method",
        [
            "get_transcripts_list",
            "get_reports_list",
            "get_summaries_list",
            "get_translations_list",
        ],
    )
    def test_returns_500_when_a_file_cannot_be_read(
        self, server, workspace, method
    ):
        folder = {
            "get_transcripts_list": "resources/transcripts",
            "get_reports_list": "resources/reports",
            "get_summaries_list": "resources/recommendations",
            "get_translations_list": "resources/translations",
        }[method]
        (workspace / folder / "one.txt").write_text("content")

        with patch("builtins.open", side_effect=IOError("unreadable")):
            result = getattr(server, method)()

        assert cherrypy.response.status == 500
        assert "error" in result


class TestRecommendationsEndpoint:
    def test_starts_a_worker_thread(self, server, workspace):
        with patch.object(sts.threading, "Thread") as thread:
            result = server.generate_recommendations()

        thread.assert_called_once_with(
            target=server.run_recommendations_thread
        )
        assert result["result"] == "Process started"

    def test_returns_500_when_the_thread_cannot_start(self, server, workspace):
        with patch.object(
            sts.threading, "Thread", side_effect=RuntimeError("no threads")
        ):
            result = server.generate_recommendations()

        assert cherrypy.response.status == 500
        assert "error" in result

    def test_worker_writes_completed_on_success(self, server, workspace):
        with patch.object(sts.asyncio, "run"):
            server.run_recommendations_thread()

        assert (
            workspace / "recommendations_status.txt"
        ).read_text() == "Completed"

    def test_worker_writes_the_error_on_failure(self, server, workspace):
        with patch.object(
            sts.asyncio, "run", side_effect=RuntimeError("boom")
        ):
            server.run_recommendations_thread()

        status = (workspace / "recommendations_status.txt").read_text()
        assert status == "Error: boom"


class TestTranslationEndpoint:
    def test_starts_a_worker_thread_with_the_country_code(
        self, server, workspace
    ):
        with patch.object(
            cherrypy, "request", MagicMock(json={"countryCode": "fr"})
        ):
            with patch.object(sts.threading, "Thread") as thread:
                result = server.process_all_translations()

        assert thread.call_args.kwargs["args"] == ("fr",)
        assert result["result"] == "Translation process started: fr"

    def test_returns_an_error_when_the_body_is_unusable(
        self, server, workspace
    ):
        broken = MagicMock()
        type(broken).json = property(
            lambda self: (_ for _ in ()).throw(ValueError("no body"))
        )

        with patch.object(cherrypy, "request", broken):
            result = server.process_all_translations()

        assert result[0]["error"]
        assert result[1] == 500

    def test_worker_calls_the_translator(self, server, workspace):
        with patch.object(sts, "azure_translator") as translator:
            server.run_translation_thread("fr")

        translator.assert_called_once_with("fr")

    def test_worker_logs_instead_of_raising(self, server, workspace):
        with patch.object(
            sts, "azure_translator", side_effect=RuntimeError("boom")
        ):
            server.run_translation_thread("fr")  # must not raise


class TestServerLifecycle:
    def test_graceful_shutdown_exits_the_engine(self, capsys):
        with patch.object(cherrypy.engine, "exit") as engine_exit:
            sts.graceful_shutdown(signal.SIGINT, None)

        engine_exit.assert_called_once()
        assert "Shutting down server" in capsys.readouterr().out

    def test_speech_text_server_configures_and_starts_cherrypy(self):
        with patch.object(cherrypy, "quickstart") as quickstart:
            with patch.object(cherrypy.config, "update") as config_update:
                with patch.object(sts.signal, "signal") as sig:
                    sts.speech_text_server()

        config_update.assert_called_once_with({"server.socket_port": 8080})
        sig.assert_called_once_with(signal.SIGINT, sts.graceful_shutdown)

        root, mount, config = quickstart.call_args.args
        assert isinstance(root, sts.SpeechTextAnalysisServer)
        assert mount == "/"
        assert config["/"]["tools.staticdir.index"] == "index.html"
        assert config["/"]["tools.staticdir.dir"].endswith("dashboard")
