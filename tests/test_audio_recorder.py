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
"""Tests for audioanalyser.modules.audio_recorder."""

import os
import signal
import threading
from unittest.mock import MagicMock, patch

import pytest

from audioanalyser.modules import audio_recorder as ar


@pytest.fixture
def settings(tmp_path):
    return ar.AudioSettings(
        input_folder=str(tmp_path / "recordings"), record_seconds=1, chunk=1024
    )


@pytest.fixture
def fake_audio():
    """A stand-in for pyaudio.PyAudio() with a readable stream."""
    audio = MagicMock()
    stream = MagicMock()
    stream.read.return_value = b"\x00" * 2048
    audio.open.return_value = stream
    audio.get_sample_size.return_value = 2
    with patch.object(ar.pyaudio, "PyAudio", return_value=audio):
        yield audio, stream


class TestAudioSettings:
    def test_defaults_match_the_documented_values(self):
        s = ar.AudioSettings()

        assert (s.channels, s.chunk, s.rate, s.record_seconds) == (
            1,
            1024,
            44100,
            10,
        )
        assert s.input_folder == "recordings"
        assert s.format == ar.pyaudio.paInt16

    def test_str_and_repr_describe_every_field(self):
        s = ar.AudioSettings(channels=2)

        assert repr(s) == str(s)
        assert "channels=2" in str(s)
        assert "input_folder='recordings'" in str(s)


class TestConfig:
    def test_creates_the_input_folder_when_absent(self, settings):
        assert not os.path.exists(settings.input_folder)

        ar.Config(settings)

        assert os.path.isdir(settings.input_folder)

    def test_accepts_an_existing_folder(self, tmp_path):
        existing = tmp_path / "already-here"
        existing.mkdir()

        ar.Config(ar.AudioSettings(input_folder=str(existing)))

        assert existing.is_dir()

    def test_rejects_an_unsupported_sample_format(self, settings):
        settings.format = 999

        with pytest.raises(ValueError, match="Invalid audio format"):
            ar.Config(settings)

    @pytest.mark.parametrize("channels", [0, 3])
    def test_rejects_channel_counts_outside_mono_or_stereo(
        self, settings, channels
    ):
        settings.channels = channels

        with pytest.raises(ValueError, match="Channels must be"):
            ar.Config(settings)

    @pytest.mark.parametrize("rate", [7999, 48001])
    def test_rejects_sample_rates_outside_the_supported_range(
        self, settings, rate
    ):
        settings.rate = rate

        with pytest.raises(ValueError, match="Sample rate must be"):
            ar.Config(settings)


class TestAudioRecorder:
    def test_generates_a_timestamped_filename_in_the_input_folder(
        self, settings, fake_audio
    ):
        recorder = ar.AudioRecorder(ar.Config(settings))

        path = recorder.generate_output_file()

        assert path.startswith(settings.input_folder)
        assert path.endswith(".wav")
        assert "recording_" in os.path.basename(path)

    def test_records_and_writes_a_wav_file(self, settings, fake_audio):
        _, stream = fake_audio
        recorder = ar.AudioRecorder(ar.Config(settings))

        recorder.record_audio()

        assert os.path.exists(recorder.output_file_path)
        assert stream.read.call_count == int(
            settings.rate / settings.chunk * settings.record_seconds
        )
        assert recorder.is_recording is False

    def test_closes_the_stream_and_terminates_the_device(
        self, settings, fake_audio
    ):
        audio, stream = fake_audio
        recorder = ar.AudioRecorder(ar.Config(settings))

        recorder.record_audio()

        stream.stop_stream.assert_called_once()
        stream.close.assert_called_once()
        audio.terminate.assert_called_once()

    def test_returns_early_and_logs_when_the_stream_cannot_open(
        self, settings, fake_audio, caplog
    ):
        audio, _ = fake_audio
        audio.open.side_effect = OSError("no input device")
        recorder = ar.AudioRecorder(ar.Config(settings))

        recorder.record_audio()

        assert "Failed to open stream." in caplog.text

    def test_stops_early_once_the_recording_flag_is_cleared(
        self, settings, fake_audio
    ):
        _, stream = fake_audio
        recorder = ar.AudioRecorder(ar.Config(settings))

        def stop_after_first_chunk(_chunk):
            recorder.is_recording = False
            return b"\x00" * 2048

        stream.read.side_effect = stop_after_first_chunk
        recorder.record_audio()

        assert stream.read.call_count == 1

    def test_logs_when_reading_the_stream_fails(
        self, settings, fake_audio, caplog
    ):
        _, stream = fake_audio
        stream.read.side_effect = OSError("device disappeared")
        recorder = ar.AudioRecorder(ar.Config(settings))

        recorder.record_audio()

        assert "Error occurred during recording" in caplog.text

    def test_signal_handler_clears_the_recording_flag(
        self, settings, fake_audio
    ):
        recorder = ar.AudioRecorder(ar.Config(settings))
        recorder.is_recording = True

        recorder.signal_handler(signal.SIGINT, None)

        assert recorder.is_recording is False

    def test_installs_signal_handlers_on_the_main_thread(
        self, settings, fake_audio
    ):
        recorder = ar.AudioRecorder(ar.Config(settings))

        with patch.object(ar.signal, "signal") as sig:
            recorder.record_audio()

        assert {c.args[0] for c in sig.call_args_list} == {
            signal.SIGINT,
            signal.SIGTERM,
        }

    def test_warns_instead_of_installing_handlers_off_the_main_thread(
        self, settings, fake_audio, caplog
    ):
        recorder = ar.AudioRecorder(ar.Config(settings))
        thread = threading.Thread(target=recorder.record_audio)

        thread.start()
        thread.join()

        assert (
            "Signal handling can only be set up in the main thread"
            in caplog.text
        )

    def test_warns_when_the_recording_is_suspiciously_small(
        self, settings, fake_audio, caplog
    ):
        recorder = ar.AudioRecorder(ar.Config(settings))
        recorder.output_file_path = os.path.join(
            settings.input_folder, "tiny.wav"
        )
        with open(recorder.output_file_path, "wb") as handle:
            handle.write(b"short")

        recorder.validate_output_file()

        assert "unusually small" in caplog.text

    def test_logs_when_the_output_file_is_absent(
        self, settings, fake_audio, caplog
    ):
        recorder = ar.AudioRecorder(ar.Config(settings))
        recorder.output_file_path = os.path.join(
            settings.input_folder, "never-written.wav"
        )

        recorder.validate_output_file()

        assert "does not exist" in caplog.text


class TestAudioRecorderEntryPoint:
    def test_accepts_a_settings_instance(self, settings, fake_audio):
        result = ar.audio_recorder(settings)

        assert result is not None
        assert os.path.exists(result)

    def test_accepts_a_settings_dictionary(self, tmp_path, fake_audio):
        result = ar.audio_recorder(
            {"input_folder": str(tmp_path / "from-dict"), "record_seconds": 1}
        )

        assert result is not None
        assert "from-dict" in result

    def test_builds_settings_from_the_environment_by_default(
        self, clean_env, tmp_path, fake_audio
    ):
        clean_env.setenv("INPUT_FOLDER", str(tmp_path / "from-env"))
        clean_env.setenv("RECORD_SECONDS", "1")
        clean_env.setenv("CHANNELS", "2")
        clean_env.setenv("RATE", "16000")

        result = ar.audio_recorder()

        assert "from-env" in result

    def test_returns_none_and_logs_when_settings_are_invalid(
        self, tmp_path, fake_audio, caplog
    ):
        result = ar.audio_recorder(
            {"input_folder": str(tmp_path / "bad"), "channels": 9}
        )

        assert result is None
        assert "Error in audio recorder." in caplog.text
