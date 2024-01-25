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

"""Audio Recorder Module

This module provides functionality to record audio from an input device and
save as a WAV file.

Usage:
    - Configure audio parameters in .env environment file
    - Call audio_recorder() to start recording
    - Recording is saved to timestamped WAV file
    - Custom audio settings can optionally be specified

Features:
    - Reads audio from microphone/line-in input
    - Saves recording to configured output folder
    - Outputs 24-bit WAV files by default
    - Handles PyAudio stream exceptions
    - Validation of configuration parameters
    - Progress bar with status, count, and timing

The audio_recorder() function initializes the configuration, recorder,
and starts the recording process.

The Config class loads settings, checks output folder presence,
and validates parameters.

The AudioRecorder class manages the PyAudio stream and WAV file handling.
It also sets up signal handling for graceful shutdown.

Author:
    Sebastien Rousseau.

Version:
    0.0.5

Notes:
    - Requires PyAudio and PyDotEnv libraries
    - Requires .env file with AUDIO_SETTINGS
    environment variables
"""

# Import required libraries
from datetime import datetime
from dataclasses import dataclass, field
import logging
from dotenv import load_dotenv
import os
import pyaudio
import signal
import threading
import wave
from typing import Optional, Union
from tqdm import tqdm


# Load environment variables
load_dotenv()


# Define the AudioSettings dataclass for structured configuration
@dataclass
class AudioSettings:
    channels: int = field(default=1)
    chunk: int = field(default=1024)
    format: int = field(default=pyaudio.paInt16)
    input_folder: str = field(default="recordings")
    rate: int = field(default=44100)
    record_seconds: int = field(default=10)

    def __str__(self) -> str:
        return (
            f"AudioSettings(channels={self.channels}, chunk={self.chunk}, "
            f"format={self.format}, input_folder='{self.input_folder}', "
            f"rate={self.rate}, record_seconds={self.record_seconds})"
        )

    def __repr__(self) -> str:
        return self.__str__()


# Initialize logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("AudioRecorder")


class Config:
    """
    Handles configuration and environment validation.
    Ensures audio recording environment is set up correctly.
    """

    def __init__(self, settings: AudioSettings):
        self.settings = settings
        self.validate_directory(self.settings.input_folder)
        self.validate_audio_settings()

    @staticmethod
    def validate_directory(directory: str):
        # Ensures the specified directory exists; creates it if not found
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory {directory}")

    def validate_audio_settings(self):
        # Validates audio settings against predefined acceptable values
        if self.settings.format not in [
            pyaudio.paInt16,
            pyaudio.paInt24,
            pyaudio.paInt32
        ]:
            raise ValueError("Invalid audio format.")
        if not (1 <= self.settings.channels <= 2):
            raise ValueError("Channels must be 1 (mono) or 2 (stereo).")
        if not 8000 <= self.settings.rate <= 48000:
            raise ValueError("Sample rate must be between 8000 and 48000 Hz.")


class AudioRecorder:
    """
    Manages the audio recording process, including stream handling and file
    output.
    """

    def __init__(self, config: Config):
        self.config = config
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.output_file_path = None

    def record_audio(self):
        """
        Starts the audio recording process.
        Sets up signal handling for graceful exit.
        """
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        else:
            logger.warning(
                "Signal handling can only be set up in the main thread."
            )

        self.is_recording = True
        self.output_file_path = self.generate_output_file()

        try:
            stream = self.audio.open(
                format=self.config.settings.format,
                channels=self.config.settings.channels,
                rate=self.config.settings.rate,
                input=True,
                frames_per_buffer=self.config.settings.chunk
            )
        except Exception:
            logger.exception("Failed to open stream.")
            return

        try:
            # Calculate total number of chunks to read
            total_chunks = int(
                self.config.settings.rate /
                self.config.settings.chunk *
                self.config.settings.record_seconds
            )

            with wave.open(self.output_file_path, "wb") as wf:
                wf.setnchannels(self.config.settings.channels)
                wf.setsampwidth(self.audio.get_sample_size(
                    self.config.settings.format
                ))
                wf.setframerate(self.config.settings.rate)

                # Corrected usage of tqdm
                with tqdm(
                    total=total_chunks, desc="Recording", unit="chunk"
                ) as pbar:
                    for _ in range(total_chunks):
                        if not self.is_recording:
                            break
                        data = stream.read(self.config.settings.chunk)
                        wf.writeframes(data)
                        pbar.update(1)

        except Exception:
            logger.exception(
                "Error occurred during recording or file writing."
            )
        finally:
            stream.stop_stream()
            stream.close()
            self.audio.terminate()
            self.is_recording = False
            logger.info(f"File saved as: {self.output_file_path}")

        self.validate_output_file()

    def generate_output_file(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(
            self.config.settings.input_folder,
            f"recording_{timestamp}.wav"
        )

    def validate_output_file(self):
        """
        Validates the output WAV file, checking for specific properties
        like file size.
        """
        if os.path.exists(self.output_file_path):
            file_size = os.path.getsize(self.output_file_path)
            if file_size < 100:  # Arbitrary minimum file size
                logger.warning(
                    f"Output file {self.output_file_path} is"
                    f"unusually small. Possible recording issue.")
        else:
            logger.error(
                f"Output file {self.output_file_path} does not exist."
            )

    def signal_handler(self, signal_received, frame):
        logger.info("Signal received, stopping recording...")
        self.is_recording = False


def audio_recorder(
    custom_settings: Union[AudioSettings, dict] = None
) -> Optional[str]:
    try:
        if isinstance(custom_settings, dict):
            settings = AudioSettings(**custom_settings)
        elif isinstance(custom_settings, AudioSettings):
            settings = custom_settings
        else:
            settings = AudioSettings(
                channels=int(os.getenv("CHANNELS", 1)),
                chunk=int(os.getenv("CHUNK", 1024)),
                format=int(os.getenv("FORMAT", pyaudio.paInt16)),
                input_folder=os.getenv("INPUT_FOLDER", "recordings"),
                rate=int(os.getenv("RATE", 44100)),
                record_seconds=int(os.getenv("RECORD_SECONDS", 10)),
            )
        config = Config(settings)
        recorder = AudioRecorder(config)
        recorder.record_audio()
        return recorder.output_file_path
    except Exception:
        logger.exception("Error in audio recorder.")
        return None


if __name__ == "__main__":
    recorded_file = audio_recorder()
    if recorded_file:
        logger.info(f"Recording completed: {recorded_file}")
