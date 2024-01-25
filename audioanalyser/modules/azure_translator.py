from typing import Iterator
import requests
import uuid
import sqlite3
import json
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s app - %(message)s"
)
logger = logging.getLogger("Azure Translator")


class Config:
    def __init__(self):
        # Retrieve configuration from environment variables
        self.key = os.getenv('AZURE_TRANSLATOR_KEY')
        self.endpoint = os.getenv('AZURE_TRANSLATOR_ENDPOINT')
        self.location = os.getenv('REGION')
        self.TRANSCRIPTS_FOLDER = Path(os.getenv("TRANSCRIPTS_FOLDER", "."))
        self.TRANSLATIONS_FOLDER = Path(os.getenv("TRANSLATIONS_FOLDER", "."))
        self.translations_db_table_name = "translations"
        self.target_languages = ['fr', 'es', 'de']
        languages = os.getenv("TRANSLATIONS_LANGUAGES")
        self.target_languages = languages.split(",") if languages else []
        self.validate_config()

    def validate_config(self):
        # Check if all required Azure configurations are present
        if not all([self.key, self.endpoint, self.location]):
            raise ValueError('Missing required Azure configuration.')

        # Validate the transcript and translation folders
        if not self.TRANSCRIPTS_FOLDER.is_dir():
            raise EnvironmentError(
                f"Invalid TRANSCRIPTS_FOLDER path: {self.TRANSCRIPTS_FOLDER}"
            )
        if not self.TRANSLATIONS_FOLDER.is_dir():
            raise EnvironmentError(
                f"Invalid TRANSLATIONS_FOLDER path: {self.TRANSLATIONS_FOLDER}"
            )

        # Validate target languages
        if not all(isinstance(
            lang,
            str
        ) and lang.isalpha() for lang in self.target_languages):
            raise ValueError("Invalid language codes in target languages.")


class Transcript:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.text = self.load_transcript()

    def load_transcript(self) -> str:
        try:
            with open(self.path, "r") as file:
                return file.read()
        except IOError as e:
            logger.error(f"Error reading file {self.path}: {e}")
            return ""

    @staticmethod
    def iter_transcripts(folder_path: Path) -> Iterator["Transcript"]:
        # Iterate over .txt files in the given folder
        for path in folder_path.glob("*.txt"):
            yield Transcript(path)


class Translator:
    def __init__(self, config):
        self.config = config

    def translate(self, text: str, target_languages: list) -> dict:
        # Prepare the request for Azure Translator API
        path = '/translate'
        constructed_url = self.config.endpoint + path
        params = {'api-version': '3.0', 'from': 'en', 'to': target_languages}
        headers = {
            'Ocp-Apim-Subscription-Key': self.config.key,
            'Ocp-Apim-Subscription-Region': self.config.location,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }
        body = [{'text': text}]

        try:
            response = requests.post(
                constructed_url, params=params, headers=headers, json=body
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Translation request failed: {e}")
            return {}


def save_translation(file_path: Path, translated_text, config):
    # Process and save the translated text in various formats
    base_file_name = file_path.stem
    translations = {}

    for item in translated_text:
        for translation in item['translations']:
            lang = translation['to']
            text = translation['text']
            translations.setdefault(lang, []).append(text)

    for lang, texts in translations.items():
        # Step 1: Generate the JSON file name
        json_file_name = f"{base_file_name}-{lang}.json"

        # Step 2: Construct the full path
        json_filename = config.TRANSLATIONS_FOLDER / json_file_name

        # Step 3: Write the JSON file
        write_to_json(json_filename, texts)

        # Step 4: Define the SQLite database
        db_file_path = f"{base_file_name}-{lang}.db"
        db_filename = config.TRANSLATIONS_FOLDER / db_file_path

        # Step 5: Write the SQLite database
        write_to_sqlite(
            config.translations_db_table_name,
            file_path.name, lang, texts, db_filename
        )

        # Step 6: Write the text file
        txt_filename = f"{base_file_name}-{lang}.txt"
        txt_file = config.TRANSLATIONS_FOLDER / txt_filename
        write_to_file(txt_file, texts)


def write_to_file(output_filename: Path, translations: list) -> None:
    # Write the translations to a text file
    try:
        with open(output_filename, "w") as file:
            for text in translations:
                file.write(text + "\n")
    except IOError as e:
        logger.error(f"Error writing to file {output_filename}: {e}")


def write_to_json(json_filename, translations):
    # Write the translations to a JSON file
    with open(json_filename, "w") as json_file:
        json.dump(translations, json_file, indent=4)


def write_to_sqlite(
    db_table_name,
    file_name,
    language,
    translations,
    db_file_path
):
    # Write the translations to a SQLite database
    with sqlite3.connect(db_file_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""CREATE TABLE IF NOT EXISTS {db_table_name}
            (filename TEXT, language TEXT, translation TEXT)"""
        )
        for text in translations:
            cursor.execute(
                f"""INSERT INTO {db_table_name} (
                    filename,
                    language,
                    translation
                )
                VALUES (?, ?, ?)""", (file_name, language, text)
            )


def azure_translator(*args: str) -> None:
    config = Config()
    translator = Translator(config)

    # Determine the target languages
    target_languages = list(args) if args else config.target_languages

    # Iterate over transcripts and translate them
    for transcript in Transcript.iter_transcripts(config.TRANSCRIPTS_FOLDER):
        translated_text = translator.translate(
            transcript.text,
            target_languages
        )
        if translated_text:
            save_translation(transcript.path, translated_text, config)


if __name__ == '__main__':
    azure_translator()
