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
import azure.cognitiveservices.speech as speechsdk
import logging
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s app - %(message)s",
)
logger = logging.getLogger("AzureTextToSpeech")


class Config:
    """
    Configuration parameters for the Azure Text-to-Speech API.
    """

    def __init__(self):
        self.api_key = os.getenv("AZURE_AUDIO_TEXT_KEY")
        self.region = os.getenv("REGION")
        self.OUTPUT_FOLDER = os.getenv("RECORDS_FOLDER")
        self.audio_extension = os.getenv("AUDIO_EXTENSION", "wav")
        self.validate()

    def validate(self):
        """
        Validate the configuration parameters.
        """
        required_vars = [
            self.api_key,
            self.region,
            self.OUTPUT_FOLDER,
            self.audio_extension
        ]
        if any(var is None for var in required_vars):
            missing = ', '.join(
                [
                    name for name,
                    var in zip(
                        [
                            "api_key",
                            "region",
                            "OUTPUT_FOLDER",
                            "audio_extension"
                        ], required_vars
                    ) if var is None]
            )
            logger.error(f"Missing environment variables: {missing}")
            raise EnvironmentError("Missing required environment variables.")


class TextToSpeech:
    """
    Synthesizes speech from text using the Azure Text-to-Speech API.
    """

    def __init__(self, config):
        self.config = config

    def synthesize_text(
        self,
        text: str,
        language: str = "en-GB",
        voice_name: str = "en-GB-RyanNeural"
    ):
        """
        Synthesize speech from text using specified settings.
        """
        try:
            speech_config = speechsdk.SpeechConfig(
                subscription=self.config.api_key, region=self.config.region
            )
            speech_config.speech_synthesis_language = language
            speech_config.speech_synthesis_voice_name = voice_name

            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config
            )
            result = synthesizer.speak_text_async(text).get()

            if (result.reason ==
                    speechsdk.ResultReason.SynthesizingAudioCompleted):
                logger.info("Successfully synthesized speech from text.")
                return result.audio_data

            else:
                if result.error_details:
                    reason_for_failure = result.error_details
                else:
                    reason_for_failure = "Unknown error."

                error_message = (
                    f"Failed to synthesize speech from text. "
                    f"Reason: {reason_for_failure}"
                )
                logger.error(error_message)

                return None
        except Exception as e:
            logger.error(f"An error occurred during speech synthesis: {e}")
            raise


def text_to_speech(
    text=None,
    name=None,
    language="en-GB",
    voice_name="en-GB-RyanNeural"
):
    """
    Convert text to speech using the Azure Text-to-Speech API.
    """
    # Validate arguments
    if not text or not isinstance(text, str):
        raise ValueError("Text must be a non-empty string.")
    if not name or not isinstance(name, str):
        raise ValueError("Name must be a non-empty string.")
    if not isinstance(language, str) or not language:
        raise ValueError("Language must be a non-empty string.")
    if not isinstance(voice_name, str) or not voice_name:
        raise ValueError("Voice name must be a non-empty string.")

    try:
        config = Config()
        tts_processor = TextToSpeech(config)
        audio_data = tts_processor.synthesize_text(text, language, voice_name)

        if audio_data:
            output_path = Path(
                config.OUTPUT_FOLDER
            ) / f"{name}{config.audio_extension}"
            if not os.path.exists(config.OUTPUT_FOLDER):
                os.makedirs(config.OUTPUT_FOLDER)
            with open(output_path, "wb") as audio_file:
                audio_file.write(audio_data)
            logger.info(f"Audio file saved to {output_path}")
        else:
            logger.error("No audio data received from synthesis.")
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    text_to_speech()
