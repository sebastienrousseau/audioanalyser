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

"""
This module contains the code for the audio recording application.

The main function, audio_recorder, is used to start the audio recording
process. It uses the Config class to load the audio recording settings from the
.env file, and the AudioRecorder class to manage the audio recording process.

The Config class ensures that the input and output directories exist, and that
the audio settings are valid. It also generates the output file path for the
recorded audio.

The AudioRecorder class sets up signal handling for the application, and
manages the audio stream and file output. It generates the output file path,
and starts the recording process.

If an error occurs during the recording process, the error is logged and None
is returned. Otherwise, the output file path is returned.

Note: This code assumes that the .env file contains the required environment
variables for the audio recording settings.
"""

# Import required libraries
import logging
import os
import pyaudio
import signal
import threading
import wave
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()

# Constants for audio recording settings, loaded from environment variables
AUDIO_SETTINGS = {
    'CHANNELS': int(os.getenv('CHANNELS', 1)),
    'CHUNK': int(os.getenv('CHUNK', 1024)),
    'FORMAT': int(os.getenv('FORMAT', pyaudio.paInt16)),
    'RATE': int(os.getenv('RATE', 44100)),
    'RECORD_SECONDS': int(os.getenv('RECORD_SECONDS', 10)),
    'INPUT_FOLDER': os.getenv('INPUT_FOLDER', 'recordings')
}

# Setting up logging for the application, helpful for debugging and monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s - %(message)s'
)
logger = logging.getLogger('AudioRecorder')


class Config:
    """
    Handles configuration and environment validation.
    Ensures audio recording environment is set up correctly.
    """
    def __init__(self, settings):
        self.settings = settings
        self.validate_directory(self.settings['INPUT_FOLDER'])
        self.validate_audio_settings()

    @staticmethod
    def validate_directory(directory):
        # Ensures the specified directory exists; creates it if not found
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory {directory}")

    def validate_audio_settings(self):
        # Validates audio settings against predefined acceptable values
        if self.settings['FORMAT'] not in [
            pyaudio.paInt16,
            pyaudio.paInt24,
            pyaudio.paInt32
        ]:
            raise ValueError("Invalid audio format.")
        if not (1 <= self.settings['CHANNELS'] <= 2):
            raise ValueError("Channels must be 1 (mono) or 2 (stereo).")
        if not 8000 <= self.settings['RATE'] <= 48000:
            raise ValueError("Sample rate must be between 8000 and 48000 Hz.")


class AudioRecorder:
    """
    Manages the audio recording process, including stream handling and file
    output.
    """
    def __init__(self, config):
        """
        Args:
            config (Config): The application configuration settings.
        """
        self.config = config
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.output_file_path = None
        self.setup_signal_handling()

    def record_audio(self):
        """
        Starts the audio recording process.
        """
        self.is_recording = True
        self.output_file_path = self.generate_output_file()

        stream = self.audio.open(
            format=self.config.settings['FORMAT'],
            channels=self.config.settings['CHANNELS'],
            rate=self.config.settings['RATE'],
            input=True,
            frames_per_buffer=self.config.settings['CHUNK']
        )

        with wave.open(self.output_file_path, 'wb') as wf:
            wf.setnchannels(self.config.settings['CHANNELS'])
            wf.setsampwidth(self.audio.get_sample_size(
                self.config.settings['FORMAT'])
            )
            wf.setframerate(self.config.settings['RATE'])

            try:
                with tqdm(
                    total=self.config.settings['RECORD_SECONDS'],
                    desc="Recording",
                    unit="sec"
                ) as pbar:
                    for _ in range(
                        int(
                            self.config.settings['RATE'] /
                            self.config.settings['CHUNK'] *
                            self.config.settings['RECORD_SECONDS']
                        )
                    ):
                        if not self.is_recording:
                            break
                        data = stream.read(self.config.settings['CHUNK'])
                        wf.writeframes(data)
                        pbar.update(1)
            finally:
                stream.stop_stream()
                stream.close()
                self.audio.terminate()
                self.is_recording = False
                logger.info(f"File saved as: {self.output_file_path}")

    def generate_output_file(self):
        """
        Generates the output file path for the recorded audio.

        Returns:
            str: The output file path.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(
            self.config.settings['INPUT_FOLDER'], f"recording_{timestamp}.wav"
        )

    def setup_signal_handling(self):
        """
        Sets up signal handling for the application.
        """
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        else:
            logger.warning(
                "Signal handling can only be set up in the main thread."
            )

    def signal_handler(self, signal_received, frame):
        """
        Handles signals received by the application.

        Args:
            signal_received (int): The signal received.
            frame (object): The frame object.
        """
        logger.info("Signal received, stopping recording...")
        self.is_recording = False


def audio_recorder():
    try:
        config = Config(AUDIO_SETTINGS)
        recorder = AudioRecorder(config)
        recorder.record_audio()
        return recorder.output_file_path
    except Exception as e:
        logger.error(f"Error in audio recorder: {e}")
        return None


if __name__ == "__main__":
    recorded_file = audio_recorder()
    if recorded_file:
        logger.info(f"Recording completed: {recorded_file}")
