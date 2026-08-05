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
"""Tests for audioanalyser.modules.text_to_speech."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from audioanalyser.modules import text_to_speech as tts


class TestConfig:
    def test_reads_every_setting_from_the_environment(self, full_env):
        config = tts.Config()

        assert config.api_key == "test-speech-key"
        assert config.region == "westeurope"
        assert config.OUTPUT_FOLDER == full_env["RECORDS_FOLDER"]
        assert config.audio_extension == ".wav"

    def test_audio_extension_defaults_to_wav(self, full_env, clean_env):
        clean_env.delenv("AUDIO_EXTENSION")

        assert tts.Config().audio_extension == "wav"

    @pytest.mark.parametrize(
        "missing",
        ["AZURE_AUDIO_TEXT_KEY", "REGION", "RECORDS_FOLDER"],
    )
    def test_raises_when_a_required_variable_is_absent(
        self, full_env, clean_env, missing
    ):
        clean_env.delenv(missing)

        with pytest.raises(EnvironmentError, match="Missing required"):
            tts.Config()

    def test_names_the_missing_variables_in_the_log(
        self, full_env, clean_env, caplog
    ):
        clean_env.delenv("REGION")

        with pytest.raises(EnvironmentError):
            tts.Config()

        assert "region" in caplog.text


class TestTextToSpeech:
    def _synthesizer(self, reason, audio=b"", error_details=None):
        result = MagicMock()
        result.reason = reason
        result.audio_data = audio
        result.error_details = error_details
        synth = MagicMock()
        synth.speak_text_async.return_value.get.return_value = result
        return synth

    def test_returns_audio_data_when_synthesis_completes(self, full_env):
        completed = tts.speechsdk.ResultReason.SynthesizingAudioCompleted
        synth = self._synthesizer(completed, audio=b"RIFFDATA")

        with patch.object(
            tts.speechsdk, "SpeechSynthesizer", return_value=synth
        ):
            with patch.object(tts.speechsdk, "SpeechConfig"):
                result = tts.TextToSpeech(tts.Config()).synthesize_text(
                    "hello"
                )

        assert result == b"RIFFDATA"
        synth.speak_text_async.assert_called_once_with("hello")

    def test_passes_language_and_voice_to_the_speech_config(self, full_env):
        completed = tts.speechsdk.ResultReason.SynthesizingAudioCompleted
        synth = self._synthesizer(completed, audio=b"x")
        speech_config = MagicMock()

        with patch.object(
            tts.speechsdk, "SpeechSynthesizer", return_value=synth
        ):
            with patch.object(
                tts.speechsdk, "SpeechConfig", return_value=speech_config
            ):
                tts.TextToSpeech(tts.Config()).synthesize_text(
                    "hi", language="fr-FR", voice_name="fr-FR-DeniseNeural"
                )

        assert speech_config.speech_synthesis_language == "fr-FR"
        assert (
            speech_config.speech_synthesis_voice_name == "fr-FR-DeniseNeural"
        )

    def test_returns_none_and_logs_the_reason_on_failure(
        self, full_env, caplog
    ):
        synth = self._synthesizer(
            tts.speechsdk.ResultReason.Canceled, error_details="quota exceeded"
        )

        with patch.object(
            tts.speechsdk, "SpeechSynthesizer", return_value=synth
        ):
            with patch.object(tts.speechsdk, "SpeechConfig"):
                result = tts.TextToSpeech(tts.Config()).synthesize_text(
                    "hello"
                )

        assert result is None
        assert "quota exceeded" in caplog.text

    def test_reports_unknown_error_when_no_details_are_supplied(
        self, full_env, caplog
    ):
        synth = self._synthesizer(
            tts.speechsdk.ResultReason.Canceled, error_details=None
        )

        with patch.object(
            tts.speechsdk, "SpeechSynthesizer", return_value=synth
        ):
            with patch.object(tts.speechsdk, "SpeechConfig"):
                result = tts.TextToSpeech(tts.Config()).synthesize_text(
                    "hello"
                )

        assert result is None
        assert "Unknown error." in caplog.text

    def test_reraises_when_the_sdk_itself_fails(self, full_env, caplog):
        with patch.object(
            tts.speechsdk, "SpeechConfig", side_effect=RuntimeError("boom")
        ):
            with pytest.raises(RuntimeError, match="boom"):
                tts.TextToSpeech(tts.Config()).synthesize_text("hello")

        assert "An error occurred during speech synthesis" in caplog.text


class TestTextToSpeechEntryPoint:
    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"text": "", "name": "n"}, "Text must be"),
            ({"text": None, "name": "n"}, "Text must be"),
            ({"text": 42, "name": "n"}, "Text must be"),
            ({"text": "t", "name": ""}, "Name must be"),
            ({"text": "t", "name": 7}, "Name must be"),
            ({"text": "t", "name": "n", "language": ""}, "Language must be"),
            ({"text": "t", "name": "n", "language": 1}, "Language must be"),
            (
                {"text": "t", "name": "n", "voice_name": ""},
                "Voice name must be",
            ),
            (
                {"text": "t", "name": "n", "voice_name": 1},
                "Voice name must be",
            ),
        ],
    )
    def test_rejects_invalid_arguments(self, kwargs, message):
        with pytest.raises(ValueError, match=message):
            tts.text_to_speech(**kwargs)

    def test_writes_the_audio_file_to_the_output_folder(self, full_env):
        with patch.object(
            tts.TextToSpeech, "synthesize_text", return_value=b"AUDIO"
        ):
            tts.text_to_speech("hello", "greeting")

        written = Path(full_env["RECORDS_FOLDER"]) / "greeting.wav"
        assert written.read_bytes() == b"AUDIO"

    def test_creates_the_output_folder_when_it_is_missing(
        self, full_env, clean_env, tmp_path
    ):
        target = tmp_path / "not-yet-created"
        clean_env.setenv("RECORDS_FOLDER", str(target))

        with patch.object(
            tts.TextToSpeech, "synthesize_text", return_value=b"AUDIO"
        ):
            tts.text_to_speech("hello", "greeting")

        assert (target / "greeting.wav").read_bytes() == b"AUDIO"

    def test_writes_nothing_when_synthesis_returns_no_audio(
        self, full_env, caplog
    ):
        with patch.object(
            tts.TextToSpeech, "synthesize_text", return_value=None
        ):
            tts.text_to_speech("hello", "greeting")

        assert not list(Path(full_env["RECORDS_FOLDER"]).iterdir())
        assert "No audio data received" in caplog.text

    def test_reraises_and_logs_when_configuration_is_invalid(
        self, full_env, clean_env, caplog
    ):
        clean_env.delenv("REGION")

        with pytest.raises(EnvironmentError):
            tts.text_to_speech("hello", "greeting")

        assert "Script execution failed" in caplog.text
