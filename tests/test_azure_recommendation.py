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
"""Tests for audioanalyser.modules.azure_recommendation.

NOTE: generate_recommendation() calls ``openai.Completion.create``, which was
removed in openai>=1.0 and raises APIRemovedInV1 against the pinned 1.11.1.
These tests patch that call, so they cover this module's own logic - prompt
construction, response unwrapping, persistence - and deliberately do not claim
the OpenAI request itself works. See test_rejects_the_removed_openai_api below,
which pins the actual breakage.
"""

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import openai
import pytest

from audioanalyser.modules import azure_recommendation as rec


def _completion(text="A summary."):
    return SimpleNamespace(choices=[SimpleNamespace(text=text)])


class TestConfig:
    def test_reads_settings_and_applies_defaults(self, full_env):
        config = rec.Config()

        assert config.GPT3_API_KEY == "test-openai-key"
        assert config.PROMPT_STRATEGY == "default"
        assert config.PROMPT_LENGTH_RATIO == pytest.approx(0.1)
        assert config.MAX_OUTPUT_LENGTH == 2048
        assert config.OUTPUT_TONE == "neutral"
        assert config.OUTPUT_VOICE == "neutral"

    def test_reads_overrides_from_the_environment(self, full_env, clean_env):
        clean_env.setenv("PROMPT_STRATEGY", "fixed")
        clean_env.setenv("PROMPT_LENGTH_RATIO", "0.5")
        clean_env.setenv("MAX_OUTPUT_LENGTH", "128")
        clean_env.setenv("OUTPUT_TONE", "formal")
        clean_env.setenv("OUTPUT_VOICE", "friendly")

        config = rec.Config()

        assert config.PROMPT_STRATEGY == "fixed"
        assert config.PROMPT_LENGTH_RATIO == pytest.approx(0.5)
        assert config.MAX_OUTPUT_LENGTH == 128

    def test_rejects_a_transcripts_folder_that_is_not_a_directory(
        self, full_env, clean_env, tmp_path
    ):
        clean_env.setenv("TRANSCRIPTS_FOLDER", str(tmp_path / "absent"))

        with pytest.raises(EnvironmentError, match="TRANSCRIPTS_FOLDER"):
            rec.Config()

    def test_rejects_a_recommendations_folder_that_is_not_a_directory(
        self, full_env, clean_env, tmp_path
    ):
        clean_env.setenv("RECOMMENDATIONS_FOLDER", str(tmp_path / "absent"))

        with pytest.raises(EnvironmentError, match="RECOMMENDATIONS_FOLDER"):
            rec.Config()

    @pytest.mark.parametrize("ratio", ["0", "-0.5", "1.5"])
    def test_rejects_a_prompt_length_ratio_outside_zero_to_one(
        self, full_env, clean_env, ratio
    ):
        clean_env.setenv("PROMPT_LENGTH_RATIO", ratio)

        with pytest.raises(ValueError, match="PROMPT_LENGTH_RATIO"):
            rec.Config()

    @pytest.mark.parametrize("length", ["0", "-10"])
    def test_rejects_a_non_positive_max_output_length(
        self, full_env, clean_env, length
    ):
        clean_env.setenv("MAX_OUTPUT_LENGTH", length)

        with pytest.raises(ValueError, match="MAX_OUTPUT_LENGTH"):
            rec.Config()


class TestTranscript:
    def test_loads_the_file_contents(self, tmp_path):
        path = tmp_path / "a.txt"
        path.write_text("hello world")

        assert rec.Transcript(path).text == "hello world"

    def test_iterates_only_over_txt_files(self, tmp_path):
        (tmp_path / "one.txt").write_text("1")
        (tmp_path / "skip.md").write_text("no")

        found = [
            t.path.name for t in rec.Transcript.iter_transcripts(tmp_path)
        ]

        assert found == ["one.txt"]


class TestPromptConstruction:
    def test_default_strategy_scales_with_the_input_length(self, full_env):
        generator = rec.RecommendationsGenerator(rec.Config())

        # 100 words at ratio 0.1
        assert generator.calculate_prompt_length(" ".join(["w"] * 100)) == 10

    def test_default_strategy_never_returns_less_than_one(self, full_env):
        generator = rec.RecommendationsGenerator(rec.Config())

        assert generator.calculate_prompt_length("one") == 1

    def test_fixed_strategy_is_capped_by_max_output_length(
        self, full_env, clean_env
    ):
        clean_env.setenv("PROMPT_STRATEGY", "fixed")
        clean_env.setenv("MAX_OUTPUT_LENGTH", "5")
        generator = rec.RecommendationsGenerator(rec.Config())

        assert generator.calculate_prompt_length(" ".join(["w"] * 100)) == 5
        assert generator.calculate_prompt_length("one two") == 2

    def test_rejects_an_unknown_strategy(self, full_env, clean_env):
        clean_env.setenv("PROMPT_STRATEGY", "sideways")
        generator = rec.RecommendationsGenerator(rec.Config())

        with pytest.raises(ValueError, match="Invalid PROMPT_STRATEGY"):
            generator.calculate_prompt_length("hello")

    @pytest.mark.parametrize(
        ("tone", "voice", "expected_tone", "expected_voice"),
        [
            ("neutral", "neutral", "", ""),
            (
                "formal",
                "professional",
                "Formal tone:\n\n",
                "Professional voice:\n\n",
            ),
            ("casual", "friendly", "Casual tone:\n\n", "Friendly voice:\n\n"),
            ("unknown", "unknown", "", ""),
        ],
    )
    def test_tone_and_voice_prompts_map_from_configuration(
        self, full_env, clean_env, tone, voice, expected_tone, expected_voice
    ):
        clean_env.setenv("OUTPUT_TONE", tone)
        clean_env.setenv("OUTPUT_VOICE", voice)
        generator = rec.RecommendationsGenerator(rec.Config())

        assert generator.get_tone_and_voice_prompts() == (
            expected_tone,
            expected_voice,
        )

    def test_prompt_includes_the_tone_voice_and_source_text(
        self, full_env, clean_env
    ):
        clean_env.setenv("OUTPUT_TONE", "formal")
        generator = rec.RecommendationsGenerator(rec.Config())

        prompt = generator.create_prompt("the customer called about billing")

        assert prompt.startswith("Formal tone:\n\n")
        assert "the customer called about billing" in prompt
        assert "executive" in prompt


class TestGenerateRecommendation:
    def test_sends_the_prompt_and_returns_the_stripped_completion(
        self, full_env, tmp_path
    ):
        source = tmp_path / "call.txt"
        source.write_text("customer wants a refund")
        generator = rec.RecommendationsGenerator(rec.Config())

        with patch.object(openai, "Completion", MagicMock()) as completion:
            completion.create.return_value = _completion(
                "  Recommend a refund.  "
            )
            result = generator.generate_recommendation(rec.Transcript(source))

        assert result == "Recommend a refund."
        kwargs = completion.create.call_args.kwargs
        assert kwargs["engine"] == "gpt-3.5-turbo-instruct"
        assert kwargs["max_tokens"] == 2048
        assert "customer wants a refund" in kwargs["prompt"]

    def test_rejects_the_removed_openai_api(self, full_env, tmp_path):
        """openai>=1.0 removed the Completion resource this module calls.

        Pinned deliberately: while this raises, the -sum/--summary feature
        cannot work at runtime no matter how the module is configured.
        """
        source = tmp_path / "call.txt"
        source.write_text("hello")
        generator = rec.RecommendationsGenerator(rec.Config())

        with pytest.raises(openai.lib._old_api.APIRemovedInV1):
            generator.generate_recommendation(rec.Transcript(source))


class TestPersistence:
    def test_save_text_to_file_creates_parents(self, full_env, tmp_path):
        target = tmp_path / "nested" / "deep" / "out.txt"

        rec.RecommendationsGenerator(rec.Config()).save_text_to_file(
            target, "content"
        )

        assert target.read_text() == "content"

    def test_save_data_to_json_creates_parents(self, full_env, tmp_path):
        target = tmp_path / "nested" / "out.json"

        rec.RecommendationsGenerator(rec.Config()).save_data_to_json(
            target, {"recommendation": "text"}
        )

        assert json.loads(target.read_text()) == {"recommendation": "text"}

    def test_insert_data_to_sqlite_creates_the_table_and_rows(
        self, full_env, tmp_path
    ):
        db = tmp_path / "nested" / "out.db"

        rec.RecommendationsGenerator(rec.Config()).insert_data_to_sqlite(
            db, "recommendations", [("a.txt", "text")]
        )

        with sqlite3.connect(db) as conn:
            rows = conn.execute(
                "SELECT filename, transcription FROM recommendations"
            ).fetchall()
        assert rows == [("a.txt", "text")]


class TestGenerateRecommendations:
    def test_writes_txt_json_and_db_for_each_transcript(
        self, full_env, folders
    ):
        (folders["transcripts"] / "call.txt").write_text("customer text")
        generator = rec.RecommendationsGenerator(rec.Config())

        with patch.object(
            generator, "generate_recommendation", return_value="Do the thing."
        ):
            generator.generate_recommendations()

        out = folders["recommendations"]
        assert (
            out / "azure_recommendation-call.txt"
        ).read_text() == "Do the thing."
        assert json.loads(
            (out / "azure_recommendation-call.json").read_text()
        ) == {"recommendation": "Do the thing."}
        with sqlite3.connect(out / "recommendations.db") as conn:
            rows = conn.execute(
                "SELECT filename, transcription FROM recommendations"
            ).fetchall()
        assert rows == [("call.txt", "Do the thing.")]

    def test_does_nothing_when_there_are_no_transcripts(
        self, full_env, folders
    ):
        generator = rec.RecommendationsGenerator(rec.Config())

        generator.generate_recommendations()

        assert not list(Path(folders["recommendations"]).iterdir())


class TestEntryPoint:
    def test_generates_recommendations_for_the_configured_folder(
        self, full_env, folders
    ):
        (folders["transcripts"] / "call.txt").write_text("customer text")

        with patch.object(
            rec.RecommendationsGenerator,
            "generate_recommendation",
            return_value="Summary.",
        ):
            rec.azure_recommendation()

        assert (
            folders["recommendations"] / "azure_recommendation-call.txt"
        ).read_text() == "Summary."

    def test_logs_instead_of_raising_when_configuration_is_invalid(
        self, full_env, clean_env, tmp_path, caplog
    ):
        clean_env.setenv("TRANSCRIPTS_FOLDER", str(tmp_path / "absent"))

        rec.azure_recommendation()

        assert "Script execution failed" in caplog.text

    def test_swallows_the_removed_openai_api_error(
        self, full_env, folders, caplog
    ):
        """The removed-API failure is caught and logged, not surfaced.

        This is why the feature fails silently rather than crashing.
        """
        (folders["transcripts"] / "call.txt").write_text("customer text")

        rec.azure_recommendation()

        assert "Script execution failed" in caplog.text
        assert not list(Path(folders["recommendations"]).iterdir())
