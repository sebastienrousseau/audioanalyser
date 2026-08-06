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

import pytest

from audioanalyser.modules import azure_recommendation as rec
from audioanalyser.modules import llm_providers as lp


def _completion(text="A summary."):
    """A chat completion response: the reply lives on choices[].message."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
    )


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

        # 4000 words at ratio 0.1, comfortably above the floor
        assert generator.calculate_prompt_length(" ".join(["w"] * 4000)) == 400

    def test_short_transcripts_get_the_floor_not_a_token_or_two(
        self, full_env
    ):
        """A live run asked gemma3 for a "6 token" summary and got a refusal.

        The ratio alone scales a short call down to a handful of tokens,
        which cannot carry the section headings the prompt also demands.
        """
        generator = rec.RecommendationsGenerator(rec.Config())

        assert generator.calculate_prompt_length("one") == (
            rec.MIN_SUMMARY_TOKENS
        )

    def test_never_asks_for_more_than_the_hard_output_cap(
        self, full_env, clean_env
    ):
        clean_env.setenv("MAX_OUTPUT_LENGTH", "50")
        generator = rec.RecommendationsGenerator(rec.Config())

        assert generator.calculate_prompt_length(" ".join(["w"] * 9000)) == 50

    def test_instructions_say_where_the_transcript_is(self, full_env):
        """Without this a smaller model asks the user to paste it."""
        generator = rec.RecommendationsGenerator(rec.Config())

        assert "user message" in generator.create_prompt("hello")

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

    def test_instructions_carry_the_tone_and_voice(self, full_env, clean_env):
        clean_env.setenv("OUTPUT_TONE", "formal")
        generator = rec.RecommendationsGenerator(rec.Config())

        prompt = generator.create_prompt("the customer called about billing")

        assert prompt.startswith("Formal tone:\n\n")
        assert "executive" in prompt

    def test_instructions_exclude_the_transcript(self, full_env):
        """The transcript travels as the user message, not the system one.

        Keeping it out stops a long transcript from diluting the formatting
        rules the summary depends on.
        """
        generator = rec.RecommendationsGenerator(rec.Config())

        prompt = generator.create_prompt("the customer called about billing")

        assert "the customer called about billing" not in prompt


class TestProviderDelegation:
    def test_sends_the_instructions_and_transcript_separately(
        self, full_env, tmp_path
    ):
        """The provider receives the two parts, not a concatenated prompt."""
        source = tmp_path / "call.txt"
        source.write_text("customer wants a refund")
        generator = rec.RecommendationsGenerator(rec.Config())
        provider = MagicMock()
        provider.generate.return_value = "Summary."

        with patch.object(rec, "get_provider", return_value=provider):
            result = generator.generate_recommendation(rec.Transcript(source))

        assert result == "Summary."
        kwargs = provider.generate.call_args.kwargs
        assert "executive" in kwargs["system"]
        assert kwargs["user_text"] == "customer wants a refund"
        assert kwargs["max_tokens"] == 2048
        assert kwargs["temperature"] == 0.8

    def test_uses_whichever_provider_is_configured(self, full_env, tmp_path):
        """Selection is the provider layer's job, not this module's."""
        source = tmp_path / "call.txt"
        source.write_text("hello")
        generator = rec.RecommendationsGenerator(rec.Config())

        with patch.object(rec, "get_provider") as get_provider:
            get_provider.return_value.generate.return_value = "text"
            generator.generate_recommendation(rec.Transcript(source))

        get_provider.assert_called_once_with()


class TestOpenAiMigrationGuards:
    """Guards two migrations that both failed silently before.

    The OpenAI call now lives in llm_providers, so the assertions are split:
    this module must not reach for the SDK at all, and the provider must not
    use the resources removed in openai 1.0.
    """

    def test_this_module_does_not_touch_an_sdk_directly(self):
        source = Path(rec.__file__).read_text()

        assert "import openai" not in source
        assert "get_provider" in source

    def test_the_provider_avoids_the_resource_removed_in_openai_v1(self):
        """openai.Completion and the global api_key were removed in 1.0.

        Calling them raises APIRemovedInV1, which azure_recommendation()
        swallows - so the feature would fail silently rather than crash.
        """
        source = Path(lp.__file__).read_text()

        assert "openai.Completion" not in source
        assert "openai.api_key" not in source
        assert "client.chat.completions.create" in source
        # The legacy completions endpoint serves only gpt-3.5-turbo-instruct,
        # which OpenAI has been retiring. Matches the quoted literal so an
        # explanatory comment naming the old model does not trip this.
        assert '"gpt-3.5-turbo-instruct"' not in source


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

    def test_api_failures_are_logged_and_produce_no_output(
        self, full_env, folders, caplog
    ):
        """Errors from the OpenAI call are caught, not surfaced.

        Worth knowing when diagnosing: a failing request leaves the
        recommendations folder empty and only a log line behind.
        """
        (folders["transcripts"] / "call.txt").write_text("customer text")

        with patch.object(
            rec, "get_provider", side_effect=RuntimeError("api unavailable")
        ):
            rec.azure_recommendation()

        assert "Script execution failed" in caplog.text
        assert not list(Path(folders["recommendations"]).iterdir())
