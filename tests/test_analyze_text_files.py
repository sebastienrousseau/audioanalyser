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
"""Tests for audioanalyser.modules.analyze_text_files.

The module is async, so each test drives it with ``asyncio.run`` rather than
taking a dependency on pytest-asyncio.
"""

import asyncio
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from audioanalyser.modules import analyze_text_files as atf


def _client(**overrides):
    """An async-context-manager client returning canned analytics results."""
    scores = SimpleNamespace(positive=0.8, neutral=0.15, negative=0.05)
    defaults = {
        "analyze_sentiment": [
            SimpleNamespace(sentiment="positive", confidence_scores=scores)
        ],
        "recognize_entities": [
            SimpleNamespace(
                entities=[
                    SimpleNamespace(text="Contoso"),
                    SimpleNamespace(text="Ada"),
                ]
            )
        ],
        "extract_key_phrases": [
            SimpleNamespace(key_phrases=["billing", "refund"])
        ],
        "detect_language": [
            SimpleNamespace(
                primary_language=SimpleNamespace(
                    name="English", iso6391_name="en"
                )
            )
        ],
        "recognize_pii_entities": [
            SimpleNamespace(entities=[SimpleNamespace(text="ada@example.com")])
        ],
    }
    defaults.update(overrides)

    client = MagicMock()
    for name, value in defaults.items():
        setattr(client, name, AsyncMock(return_value=value))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class TestConfig:
    def test_reads_every_setting_from_the_environment(self, full_env):
        config = atf.Config()

        assert config.az_lg_endpoint == "https://language.example.invalid"
        assert config.az_lg_key == "test-language-key"
        assert config.db_name == "analysis"

    @pytest.mark.parametrize(
        "missing",
        [
            "AZURE_LANGUAGE_ENDPOINT",
            "AZURE_LANGUAGE_KEY",
            "TRANSCRIPTS_FOLDER",
            "REPORTS_FOLDER",
            "ANALYSIS_DB_TABLE_NAME",
        ],
    )
    def test_raises_when_a_required_variable_is_absent(
        self, full_env, clean_env, missing
    ):
        clean_env.delenv(missing)

        with pytest.raises(EnvironmentError, match="Missing required"):
            atf.Config()


class TestTextAnalysisConstruction:
    def test_holds_the_configuration_it_is_given(self, full_env):
        config = atf.Config()

        assert atf.TextAnalysis(config).config is config


class TestAnalyzeText:
    def test_calls_every_analytics_endpoint_and_maps_the_results(self):
        client = _client()

        results = asyncio.run(atf.TextAnalysis.analyze_text(client, "hello"))

        client.analyze_sentiment.assert_awaited_once_with(["hello"])
        client.recognize_pii_entities.assert_awaited_once_with(["hello"])
        assert results["sentiment"].sentiment == "positive"
        assert results["language"].primary_language.iso6391_name == "en"

    def test_maps_empty_responses_to_none(self):
        client = _client(
            analyze_sentiment=[],
            recognize_entities=[],
            extract_key_phrases=[],
            detect_language=[],
            recognize_pii_entities=[],
        )

        results = asyncio.run(atf.TextAnalysis.analyze_text(client, "hello"))

        assert set(results.values()) == {None}


class TestSaveResults:
    def test_writes_the_summary_json_and_database(self, full_env, folders):
        client = _client()
        results = asyncio.run(atf.TextAnalysis.analyze_text(client, "hello"))

        asyncio.run(atf.TextAnalysis.save_results("call.txt", results))

        summary = (folders["reports"] / "call_analysis.txt").read_text()
        assert "Overall Sentiment: positive" in summary
        assert "Key Entities Identified: Contoso, Ada" in summary
        assert "Notable Topics: billing, refund" in summary
        assert "Detected Language: English(en)" in summary
        assert "(PII): Yes" in summary

        payload = json.loads(
            (folders["reports"] / "call_analysis.json").read_text()
        )
        assert payload["sentiment"]["sentiment"] == "positive"

        with sqlite3.connect(folders["reports"] / "text_analysis.db") as conn:
            rows = conn.execute("SELECT filename FROM analysis").fetchall()
        assert rows == [("call.txt",)]

    def test_reports_absence_of_pii(self, full_env, folders):
        client = _client(recognize_pii_entities=[SimpleNamespace(entities=[])])
        results = asyncio.run(atf.TextAnalysis.analyze_text(client, "hello"))

        asyncio.run(atf.TextAnalysis.save_results("call.txt", results))

        summary = (folders["reports"] / "call_analysis.txt").read_text()
        assert "(PII): No" in summary

    def test_omits_sections_whose_results_are_missing(self, full_env, folders):
        results = {
            "sentiment": None,
            "entities": None,
            "key_phrases": None,
            "language": None,
            "pii": None,
        }

        asyncio.run(atf.TextAnalysis.save_results("call.txt", results))

        summary = (folders["reports"] / "call_analysis.txt").read_text()
        assert "Overall Sentiment" not in summary
        assert "Transcription analysis" in summary

    def test_omits_sections_whose_collections_are_empty(
        self, full_env, folders
    ):
        results = {
            "sentiment": None,
            "entities": SimpleNamespace(entities=[]),
            "key_phrases": SimpleNamespace(key_phrases=[]),
            "language": None,
            "pii": None,
        }

        asyncio.run(atf.TextAnalysis.save_results("call.txt", results))

        summary = (folders["reports"] / "call_analysis.txt").read_text()
        assert "Key Entities Identified" not in summary
        assert "Notable Topics" not in summary

    def test_creates_the_reports_folder_when_missing(
        self, full_env, clean_env, tmp_path
    ):
        target = tmp_path / "reports-not-created"
        clean_env.setenv("REPORTS_FOLDER", str(target))
        results = {
            k: None
            for k in (
                "sentiment",
                "entities",
                "key_phrases",
                "language",
                "pii",
            )
        }

        asyncio.run(atf.TextAnalysis.save_results("call.txt", results))

        assert (target / "call_analysis.txt").exists()


class TestProcessText:
    def test_returns_results_without_saving_when_no_filename_is_given(self):
        client = _client()

        with patch.object(
            atf.TextAnalysis, "save_results", new=AsyncMock()
        ) as save:
            results = asyncio.run(
                atf.TextAnalysis.process_text(client, "hello")
            )

        save.assert_not_awaited()
        assert results["sentiment"].sentiment == "positive"

    def test_saves_the_results_when_a_filename_is_given(self):
        client = _client()

        with patch.object(
            atf.TextAnalysis, "save_results", new=AsyncMock()
        ) as save:
            asyncio.run(
                atf.TextAnalysis.process_text(client, "hello", "call.txt")
            )

        save.assert_awaited_once()
        assert save.await_args.args[0] == "call.txt"


class TestEntryPoint:
    def test_processes_each_transcript_in_the_folder(self, full_env, folders):
        (folders["transcripts"] / "one.txt").write_text("hello")
        (folders["transcripts"] / "two.txt").write_text("bonjour")
        (folders["transcripts"] / "skip.md").write_text("not a transcript")

        with patch.object(atf, "TextAnalyticsClient", return_value=_client()):
            with patch.object(
                atf.TextAnalysis, "process_text", new=AsyncMock()
            ) as process:
                asyncio.run(
                    atf.analyze_text_files(str(folders["transcripts"]))
                )

        processed = sorted(
            call.args[2].rsplit("/", 1)[-1] for call in process.await_args_list
        )
        assert processed == ["one.txt", "two.txt"]

    def test_creates_the_reports_folder_when_missing(
        self, full_env, clean_env, tmp_path
    ):
        target = tmp_path / "reports-absent"
        clean_env.setenv("REPORTS_FOLDER", str(target))

        asyncio.run(atf.analyze_text_files("ignored"))

        assert target.is_dir()

    def test_logs_instead_of_raising_when_configuration_is_invalid(
        self, full_env, clean_env, caplog
    ):
        clean_env.delenv("AZURE_LANGUAGE_KEY")

        asyncio.run(atf.analyze_text_files("ignored"))

        assert "Script execution failed" in caplog.text
