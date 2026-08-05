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
"""Tests for audioanalyser.modules.azure_translator."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from audioanalyser.modules import azure_translator as tr


def _payload(*pairs):
    """Build an Azure Translator style response body."""
    return [
        {"translations": [{"to": lang, "text": text} for lang, text in pairs]}
    ]


class TestConfig:
    def test_reads_settings_and_splits_target_languages(self, full_env):
        config = tr.Config()

        assert config.key == "test-translator-key"
        assert config.location == "westeurope"
        assert config.target_languages == ["fr", "es", "de"]
        assert config.translations_db_table_name == "translations"

    def test_target_languages_is_empty_when_unset(self, full_env, clean_env):
        clean_env.delenv("TRANSLATIONS_LANGUAGES")

        assert tr.Config().target_languages == []

    @pytest.mark.parametrize(
        "missing",
        ["AZURE_TRANSLATOR_KEY", "AZURE_TRANSLATOR_ENDPOINT", "REGION"],
    )
    def test_rejects_missing_azure_settings(
        self, full_env, clean_env, missing
    ):
        clean_env.delenv(missing)

        with pytest.raises(ValueError, match="Missing required Azure"):
            tr.Config()

    def test_rejects_a_transcripts_folder_that_is_not_a_directory(
        self, full_env, clean_env, tmp_path
    ):
        clean_env.setenv("TRANSCRIPTS_FOLDER", str(tmp_path / "absent"))

        with pytest.raises(
            EnvironmentError, match="Invalid TRANSCRIPTS_FOLDER"
        ):
            tr.Config()

    def test_rejects_a_translations_folder_that_is_not_a_directory(
        self, full_env, clean_env, tmp_path
    ):
        clean_env.setenv("TRANSLATIONS_FOLDER", str(tmp_path / "absent"))

        with pytest.raises(
            EnvironmentError, match="Invalid TRANSLATIONS_FOLDER"
        ):
            tr.Config()

    def test_rejects_non_alphabetic_language_codes(self, full_env, clean_env):
        clean_env.setenv("TRANSLATIONS_LANGUAGES", "fr,es1")

        with pytest.raises(ValueError, match="Invalid language codes"):
            tr.Config()


class TestTranscript:
    def test_loads_the_file_contents(self, tmp_path):
        path = tmp_path / "a.txt"
        path.write_text("hello world")

        assert tr.Transcript(path).text == "hello world"

    def test_returns_empty_string_and_logs_when_unreadable(
        self, tmp_path, caplog
    ):
        missing = tmp_path / "gone.txt"

        assert tr.Transcript(missing).text == ""
        assert "Error reading file" in caplog.text

    def test_iterates_only_over_txt_files(self, tmp_path):
        (tmp_path / "one.txt").write_text("1")
        (tmp_path / "two.txt").write_text("2")
        (tmp_path / "skip.md").write_text("no")

        found = sorted(
            t.path.name for t in tr.Transcript.iter_transcripts(tmp_path)
        )

        assert found == ["one.txt", "two.txt"]


class TestTranslator:
    def test_posts_to_the_translate_endpoint_and_returns_json(self, full_env):
        response = MagicMock()
        response.json.return_value = _payload(("fr", "bonjour"))

        with patch.object(requests, "post", return_value=response) as post:
            result = tr.Translator(tr.Config()).translate("hello", ["fr"])

        assert result == _payload(("fr", "bonjour"))
        (url,) = post.call_args.args
        assert url.endswith("/translate")
        assert post.call_args.kwargs["params"]["to"] == ["fr"]
        assert post.call_args.kwargs["json"] == [{"text": "hello"}]

    def test_sends_the_subscription_headers(self, full_env):
        response = MagicMock()
        response.json.return_value = []

        with patch.object(requests, "post", return_value=response) as post:
            tr.Translator(tr.Config()).translate("hello", ["fr"])

        headers = post.call_args.kwargs["headers"]
        assert headers["Ocp-Apim-Subscription-Key"] == "test-translator-key"
        assert headers["Ocp-Apim-Subscription-Region"] == "westeurope"
        assert headers["X-ClientTraceId"]

    def test_returns_empty_dict_and_logs_on_request_failure(
        self, full_env, caplog
    ):
        with patch.object(
            requests, "post", side_effect=requests.RequestException("no route")
        ):
            result = tr.Translator(tr.Config()).translate("hello", ["fr"])

        assert result == {}
        assert "Translation request failed" in caplog.text

    def test_returns_empty_dict_when_the_response_is_an_error_status(
        self, full_env, caplog
    ):
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError("401")

        with patch.object(requests, "post", return_value=response):
            assert tr.Translator(tr.Config()).translate("hello", ["fr"]) == {}


class TestWriters:
    def test_write_to_file_writes_one_line_per_translation(self, tmp_path):
        out = tmp_path / "out.txt"

        tr.write_to_file(out, ["one", "two"])

        assert out.read_text() == "one\ntwo\n"

    def test_write_to_file_logs_instead_of_raising_when_path_is_bad(
        self, tmp_path, caplog
    ):
        tr.write_to_file(tmp_path / "absent-dir" / "out.txt", ["one"])

        assert "Error writing to file" in caplog.text

    def test_write_to_json_serialises_the_list(self, tmp_path):
        out = tmp_path / "out.json"

        tr.write_to_json(out, ["one", "two"])

        assert json.loads(out.read_text()) == ["one", "two"]

    def test_write_to_sqlite_creates_the_table_and_rows(self, tmp_path):
        db = tmp_path / "out.db"

        tr.write_to_sqlite("translations", "a.txt", "fr", ["un", "deux"], db)

        with sqlite3.connect(db) as conn:
            rows = conn.execute(
                "SELECT filename, language, translation FROM translations"
            ).fetchall()
        assert rows == [("a.txt", "fr", "un"), ("a.txt", "fr", "deux")]


class TestSaveTranslation:
    def test_writes_txt_json_and_db_per_language(self, full_env, folders):
        source = folders["transcripts"] / "call.txt"
        source.write_text("hello")

        tr.save_translation(
            source, _payload(("fr", "bonjour"), ("es", "hola")), tr.Config()
        )

        out = folders["translations"]
        assert (out / "call-fr.txt").read_text() == "bonjour\n"
        assert json.loads((out / "call-es.json").read_text()) == ["hola"]
        with sqlite3.connect(out / "call-fr.db") as conn:
            rows = conn.execute(
                "SELECT translation FROM translations"
            ).fetchall()
        assert rows == [("bonjour",)]


class TestAzureTranslatorEntryPoint:
    def test_translates_each_transcript_and_saves_the_result(
        self, full_env, folders
    ):
        (folders["transcripts"] / "one.txt").write_text("hello")
        response = MagicMock()
        response.json.return_value = _payload(("fr", "bonjour"))

        with patch.object(requests, "post", return_value=response):
            tr.azure_translator()

        assert (
            folders["translations"] / "one-fr.txt"
        ).read_text() == "bonjour\n"

    def test_explicit_arguments_override_the_configured_languages(
        self, full_env, folders
    ):
        (folders["transcripts"] / "one.txt").write_text("hello")
        response = MagicMock()
        response.json.return_value = _payload(("de", "hallo"))

        with patch.object(requests, "post", return_value=response) as post:
            tr.azure_translator("de")

        assert post.call_args.kwargs["params"]["to"] == ["de"]

    def test_writes_nothing_when_translation_yields_no_result(
        self, full_env, folders
    ):
        (folders["transcripts"] / "one.txt").write_text("hello")

        with patch.object(
            requests, "post", side_effect=requests.RequestException("down")
        ):
            tr.azure_translator()

        assert not list(Path(folders["translations"]).iterdir())
