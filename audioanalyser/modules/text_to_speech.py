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

    Attributes:
        - api_key (str): The API key for the Azure Text-to-Speech API.
        - region (str): The Azure region where the Text-to-Speech API is
        located.
        - OUTPUT_FOLDER (str): The folder path where the synthesized audio
        files will be saved.
        - audio_extension (str): The audio file extension for the output files.
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

        Raises:
            EnvironmentError: If any required environment variables
            are missing.
        """
        required_vars = [
            self.api_key,
            self.region,
            self.OUTPUT_FOLDER,
            self.audio_extension
        ]
        if any(var is None for var in required_vars):
            missing = [
                var for var, value in locals().items() if value is None
            ]
            logger.error(
                f"Missing environment variables: {', '.join(missing)}"
            )
            raise EnvironmentError(
                "Missing required environment variables."
            )


class TextToSpeech:
    """
    Synthesizes speech from text using the Azure Text-to-Speech API.

    Args:
        config (Config): The configuration parameters for the Azure
        Text-to-Speech API.

    Attributes:
        config (Config): The configuration parameters for the Azure
        Text-to-Speech API.
    """

    def __init__(self, config):
        self.config = config

    def synthesize_text(self, text: str, filename: str):
        """
        Synthesize speech from text and save it to an audio file.

        Args:
            text (str): The text to synthesize.
            filename (str): The base name for the output audio file,
            without extension.
        """
        speech_config = speechsdk.SpeechConfig(
            subscription=self.config.api_key, region=self.config.region
        )

        # Set the language
        speech_config.speech_synthesis_language = "en-GB"  # Language setting

        # Optionally, specify a voice name
        # Configure speech synthesis
        speech_config.speech_synthesis_voice_name = "en-GB-RyanNeural"

        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:

            PROJECT_ROOT = Path(__file__).resolve().parents[2]
            OUTPUT_FOLDER = PROJECT_ROOT / os.getenv("RECORDS_FOLDER")
            self.config.OUTPUT_FOLDER = os.path.join(
                PROJECT_ROOT, OUTPUT_FOLDER
            )

            # Ensure the output directory exists
            if not os.path.exists(self.config.OUTPUT_FOLDER):
                os.makedirs(self.config.OUTPUT_FOLDER)

            # Construct the output file path correctly
            output_path = Path(
                self.config.OUTPUT_FOLDER
            ) / f"{filename}.{self.config.audio_extension}"

            with open(output_path, "wb") as audio_file:
                audio_file.write(result.audio_data)
            logger.info(f"Audio file saved to {output_path}")
        else:
            logger.error("Failed to synthesize speech from text.")


def text_to_speech():
    try:
        config = Config()
        tts = TextToSpeech(config)
        # Example usage, replace "Hello, World!" and "output_filename" with
        # your desired input and file name.
        tts.synthesize_text("Thank you for your time today!", "text_to_speech")
    except Exception as e:
        logger.error(f"Failed to synthesize text to speech: {e}")


if __name__ == "__main__":
    text_to_speech()
