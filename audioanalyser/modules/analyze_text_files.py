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

# Import necessary libraries
import asyncio
import datetime
import os
import json
import logging
import sqlite3
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics.aio import TextAnalyticsClient
from dotenv import load_dotenv

# Load environment variables from .env file for configuration
load_dotenv()

# Set up logging for the application
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s app - %(message)s",
)
logger = logging.getLogger("AzureTextAnalysis")


class Config:
    """
    Configuration class for setting up environment variables and validation.

    Attributes:
        az_lg_endpoint (str): Azure Language endpoint URL.
        az_lg_key (str): Azure Language subscription key.
        transcripts (str): Folder path for input transcripts.
        reports (str): Folder path for output reports.
        db_name (str): Table name for storing analysis results.
    """

    def __init__(self):
        # Initialize configuration with environment variables
        self.az_lg_endpoint = os.getenv("AZURE_LANGUAGE_ENDPOINT")
        self.az_lg_key = os.getenv("AZURE_LANGUAGE_KEY")
        self.transcripts = os.getenv("TRANSCRIPTS_FOLDER")
        self.reports = os.getenv("REPORTS_FOLDER")
        self.db_name = os.getenv("ANALYSIS_DB_TABLE_NAME")
        self.validate()

    def validate(self):
        """
        Validates the presence of required environment variables.

        Raises:
            EnvironmentError: If any required environment variable is missing.
        """
        required_vars = [
            self.az_lg_endpoint,
            self.az_lg_key,
            self.transcripts,
            self.reports,
            self.db_name,
        ]
        # Check for missing environment variables and log error if any
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


class TextAnalysis:
    """
    Provides methods for analysing text using Azure Text Analytics and handling
    results.

    Attributes:
        config (Config): Configuration object with necessary settings.
    """

    def __init__(self, config):
        self.config = config

    @staticmethod
    async def analyze_text(client, text):
        """
        Performs various text analytics tasks on the given text.

        Args:
            client (TextAnalyticsClient): The Azure Text Analytics client.
            text (str): The text to analyze.

        Returns:
            A dictionary of analysis results such as sentiment, entities, etc.
        """
        async with client:
            sentiment_result = await client.analyze_sentiment([text])
            entity_result = await client.recognize_entities([text])
            key_phrases_result = await client.extract_key_phrases(
                [text]
            )
            language_result = await client.detect_language([text])
            pii_result = await client.recognize_pii_entities([text])

        return {
            "sentiment": sentiment_result[0]
            if sentiment_result
            else None,
            "entities": entity_result[0] if entity_result else None,
            "key_phrases": key_phrases_result[0]
            if key_phrases_result
            else None,
            "language": language_result[0] if language_result else None,
            "pii": pii_result[0] if pii_result else None,
            # Add other results as needed
        }

    @staticmethod
    async def process_text(client, text, filename=None):
        """
        Processes text for analysis.

        Args:
            client (TextAnalyticsClient): The Azure Text Analytics client.
            text (str): The text to be processed.
            filename (str, optional): The filename associated with the text.

        Returns:
            A dictionary of analysis results.
        """
        if filename:
            print(f"Processing file: {filename}")

        analysis_results = await TextAnalysis.analyze_text(client, text)

        if filename:
            print(
                f"Analysis results for {filename}: {analysis_results}"
            )
            await TextAnalysis.save_results(filename, analysis_results)

        return analysis_results

    @staticmethod
    async def save_results(filename, results):
        """
        Saves analysis results in different formats.

        Args:
            filename (str): The filename associated with the text.
            results (dict): The analysis results to save.
        """
        # Create 'Analysis' folder if it doesn't exist
        config = Config()
        if not os.path.exists(config.reports):
            os.makedirs(config.reports)

        # Modify the path to save files inside the 'Analysis' folder
        base_filename = os.path.splitext(os.path.basename(filename))[0]

        # Save to TXT with plain text format
        txt_filename = os.path.join(
            config.reports, f"{base_filename}_analysis.txt"
        )
        with open(txt_filename, "w") as file:
            current_time = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            # Executive summary format
            file.write("Transcription analysis\n\n")
            file.write(f"File: {filename}\n")
            file.write(f"Time: {current_time}\n\n")
            file.write("Summary:\n")

            # Sentiment Analysis Summary
            sentiment_result = results["sentiment"]
            if sentiment_result:
                file.write(
                    f"• Overall Sentiment: {sentiment_result.sentiment}.\n"
                )

                # Enhanced Sentiment Analysis Summary
                sentiment_scores = sentiment_result.confidence_scores
                file.write(
                    f"• Sentiment Scores - Positive:"
                    f"{sentiment_scores.positive:.2f},"
                    f"Neutral: {sentiment_scores.neutral:.2f},"
                    f"Negative: {sentiment_scores.negative:.2f}\n"
                )

            # Key Entities Summary
            entities_result = results["entities"]
            if entities_result:
                key_entities = entities_result.entities[:5]
                if key_entities:
                    key_entities_text = ", ".join(
                        [entity.text for entity in key_entities]
                    )
                    message = f"""
                    • Key Entities Identified: {key_entities_text}.\n
                    """
                    file.write(message)

            # Enhanced Key Phrases Summary
            key_phrases_result = results["key_phrases"]
            if key_phrases_result:
                key_phrases = key_phrases_result.key_phrases[:5]
                if key_phrases:
                    file.write(
                        "   • Notable Topics: "
                        + ", ".join(key_phrases)
                        + ".\n"
                    )

            # Language Detection Summary
            language_result = results["language"]
            if language_result:
                primary_language = language_result.primary_language
                file.write(
                    f"• Detected Language: {primary_language.name}"
                    f"({primary_language.iso6391_name}).\n"
                )

            # PII Summary (if applicable)
            pii_result = results["pii"]
            if pii_result:
                pii_entities = pii_result.entities
                if pii_entities:
                    file.write(
                        "• Personally identifiable information (PII): Yes."
                    )
                else:
                    file.write(
                        "• Personally identifiable information (PII): No."
                    )

        print(f"Saving results to {txt_filename}")

        # Save to JSON
        json_filename = os.path.join(
            config.reports, f"{base_filename}_analysis.json"
        )
        with open(json_filename, "w") as json_file:
            json.dump(
                results,
                json_file,
                default=lambda x: x.__dict__,
                indent=4,
            )
        print(f"Saving results to {json_filename}")

        # Save to SQLite
        db_filename = os.path.join(config.reports, "text_analysis.db")
        with sqlite3.connect(db_filename) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""CREATE TABLE IF NOT EXISTS {config.db_name}
                            (filename TEXT, analysis TEXT)"""
            )
            cursor.execute(
                f"INSERT INTO {config.db_name} (filename, analysis)"
                f"VALUES (?, ?)",
                (
                    filename,
                    json.dumps(results, default=lambda x: x.__dict__),
                ),
            )
            conn.commit()
        print(f"Saved analysis of {filename} to database.")


async def analyze_text_files(file_path):
    """
    Main function to initialize and run text analysis on all text files.

    Args:
        file_path (str): Path to the folder with text files to be processed.
    """
    try:
        # Initialize configuration and process each text file
        config = Config()
        if not os.path.exists(config.reports):
            os.makedirs(config.reports)

        endpoint = config.az_lg_endpoint
        key = config.az_lg_key

        for filename in os.listdir(config.transcripts):
            if filename.endswith(".txt"):
                input_file = os.path.join(config.transcripts, filename)
                client = TextAnalyticsClient(
                    endpoint=endpoint,
                    credential=AzureKeyCredential(key),
                )
                with open(input_file, "r") as file:
                    text = file.read()
                await TextAnalysis.process_text(
                    client, text, input_file
                )

        print("All files processed.")

    except Exception as e:
        logger.error(f"Script execution failed: {e}")


if __name__ == "__main__":
    # Run the main function in an asyncio event loop
    asyncio.run(analyze_text_files(os.getcwd()))
