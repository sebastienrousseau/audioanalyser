import azure.cognitiveservices.speech as speechsdk
import logging
import os
import json
import sqlite3
from dotenv import load_dotenv
import threading

load_dotenv()

AUDIO_EXTENSION = os.getenv("AUDIO_EXTENSION")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s app - %(message)s",
)
logger = logging.getLogger("AzureSpeechToText")


class Config:
    """
    Configuration parameters for the Azure Speech-to-Text API.

    Attributes:
        - api_key (str): The API key for the Azure Speech-to-Text API.
        - region (str): The Azure region where the Speech-to-Text API
        is located.
        - INPUT_FOLDER (str): The folder path where the input audio files are
        located.
        - TRANSCRIPTS_FOLDER (str): The folder path where the transcribed text
        files will be saved.
        - transcripts_db_table_name (str): The name of the SQLite database
        table where the transcribed text will be stored.
    """

    def __init__(self):
        self.api_key = os.getenv("AZURE_AUDIO_TEXT_KEY")
        self.region = os.getenv("REGION")
        self.INPUT_FOLDER = os.getenv("INPUT_FOLDER")
        self.TRANSCRIPTS_FOLDER = os.getenv("TRANSCRIPTS_FOLDER")
        self.transcripts_db_table_name = os.getenv(
            "TRANSCRIPTS_DB_TABLE_NAME"
        )
        self.validate()

    def validate(self):
        """
        Validate the configuration parameters.

        Raises:
            EnvironmentError: If any required environment variables are
            missing.
        """
        required_vars = [
            self.api_key,
            self.region,
            self.INPUT_FOLDER,
            self.TRANSCRIPTS_FOLDER,
            self.transcripts_db_table_name,
            AUDIO_EXTENSION,
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


class SpeechToText:
    """
    Transcribes audio files using the Azure Speech-to-Text API.

    Args:
        config (Config): The configuration parameters for the Azure
        Speech-to-Text API.

    Attributes:
        config (Config): The configuration parameters for the Azure
        Speech-to-Text API.
    """

    def __init__(self, config):
        """
        Initialize the SpeechToText class.

        Args:
            config (Config): The configuration parameters for the Azure
            Speech-to-Text API.
        """
        self.config = config

    def process_audio_files(self, file_path=None):
        """
        Process audio files based on the provided file path.
        If file_path is None, process all audio files in the input folder.

        Args:
            file_path (str, optional): The path to a specific file to process,
            or None to process all files in the input folder.
        """
        if file_path:
            if os.path.exists(file_path):
                self.process_file(file_path)
            else:
                logger.error(f"File not found: {file_path}")
        else:
            for filename in os.listdir(self.config.INPUT_FOLDER):
                if filename.endswith(AUDIO_EXTENSION):
                    full_path = os.path.join(
                        self.config.INPUT_FOLDER, filename
                    )
                    if os.path.exists(full_path):
                        self.process_file(full_path)
                    else:
                        logger.error(f"File not found: {full_path}")

    def process_file(self, file_path):
        """
        Process a single audio file.

        Args:
            file_path (str): The full path to the audio file to process.
        """
        input_path = file_path
        output_filename = os.path.splitext(os.path.basename(file_path))[
            0
        ]
        output_path = os.path.join(
            self.config.TRANSCRIPTS_FOLDER, f"{output_filename}.txt"
        )
        json_path = os.path.join(
            self.config.TRANSCRIPTS_FOLDER, f"{output_filename}.json"
        )
        db_filename = os.path.join(
            self.config.TRANSCRIPTS_FOLDER, "transcriptions.db"
        )

        logger.info(f"Processing {input_path}")
        results = self.speech_to_text_long(input_path)

        if results:
            self.write_to_file(output_path, results)
            self.write_to_json(json_path, results)
            self.write_to_sqlite(
                db_filename, os.path.basename(file_path), results
            )

    def speech_to_text_long(self, audio_filename):
        """
        Use the Azure Speech-to-Text API to transcribe an audio file.

        Args:
            audio_filename (str): The path to the audio file to transcribe.

        Returns:
            list: A list of the transcribed text for the audio file.
        """
        logger.info(
            f"Starting speech recognition for {audio_filename}. Please wait..."
        )
        speech_config = speechsdk.SpeechConfig(
            subscription=self.config.api_key, region=self.config.region
        )
        audio_input = speechsdk.audio.AudioConfig(
            filename=audio_filename
        )
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_input
        )

        all_results = []
        done = threading.Event()

        def handle_final_result(evt):
            logger.info(f"Recognized: {evt.result.text}")
            all_results.append(evt.result.text)

        def handle_recognition_error(evt):
            if evt.result.reason == speechsdk.ResultReason.Canceled:
                cancellation = evt.result.cancellation_details
                if (
                    cancellation.reason
                    == speechsdk.CancellationReason.EndOfStream
                ):
                    logger.info(
                        "Recognition completed: End of audio stream reached."
                    )
                elif (
                    cancellation.reason
                    == speechsdk.CancellationReason.Error
                ):
                    message = (
                        f"Recognition canceled due to an error: "
                        f"{cancellation.error_details}"
                    )
                    logger.error(message)
                else:
                    logger.error(
                        f"Recognition canceled: Reason={cancellation.reason}"
                    )
            else:
                logger.error(f"Recognition error: {evt}")
            done.set()

        speech_recognizer.recognized.connect(handle_final_result)
        speech_recognizer.canceled.connect(handle_recognition_error)
        speech_recognizer.session_stopped.connect(
            lambda evt: done.set()
        )

        speech_recognizer.start_continuous_recognition()
        done.wait()

        if not all_results:
            Warning(
                f"No results for {audio_filename}. "
                f"Check the audio file format and content."
            )
            logger.warning(
                f"No results for {audio_filename}. "
                f"Check the audio file format and content."
            )

        return all_results

    def write_to_file(self, output_filename, results):
        """
        Writes the transcribed text to a file.

        Args:
            output_filename (str): The path to the output file.
            results (List[str]): A list of the transcribed text.
        """
        with open(output_filename, "w") as file:
            for result in results:
                file.write(result + "\n")

    def write_to_json(self, json_filename, results):
        """
        Writes the transcribed text to a JSON file.

        Args:
            json_filename (str): The path to the output JSON file.
            results (List[str]): A list of the transcribed text.
        """
        with open(json_filename, "w") as json_file:
            json.dump(results, json_file, indent=4)

    def write_to_sqlite(self, db_filename, audio_filename, results):
        """
        Writes the transcribed text to a SQLite database.

        Args:
            db_filename (str): The path to the SQLite database file.
            audio_filename (str): The name of the audio file.
            results (List[str]): A list of the transcribed text.
        """
        config = Config()
        with sqlite3.connect(db_filename) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""CREATE TABLE IF NOT EXISTS {
                config.transcripts_db_table_name
            } (filename TEXT, transcription TEXT)"""
            )
            for result in results:
                sql_statement = (
                    f"""INSERT INTO {
                        config.transcripts_db_table_name
                    } (filename, transcription)"""
                    f"""VALUES (?, ?)"""
                )
                cursor.execute(sql_statement, (audio_filename, result))


def transcribe_audio_files(file_path=None):
    """
    Transcribe audio files using Azure Speech-to-Text API.

    Args:
        file_path (str, optional): The path to the audio file to transcribe.
        If None, use the default TRANSCRIPTS_FOLDER.

    Raises:
        Exception: If there is an error during the transcription process.
    """
    try:
        config = Config()
        speech_to_text_processor = SpeechToText(config)
        speech_to_text_processor.process_audio_files(file_path)

    except Exception as e:
        logger.error(f"Script execution failed: {e}")


if __name__ == "__main__":
    transcribe_audio_files()
