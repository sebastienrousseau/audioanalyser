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
    level=logging.INFO, format='%(asctime)s %(levelname)s app - %(message)s'
)
logger = logging.getLogger('AzureTextAnalysis')


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
        self.az_lg_endpoint = os.getenv('AZURE_LANGUAGE_ENDPOINT')
        self.az_lg_key = os.getenv('AZURE_LANGUAGE_KEY')
        self.transcripts = os.getenv('TRANSCRIPTS_FOLDER')
        self.reports = os.getenv('REPORTS_FOLDER')
        self.db_name = os.getenv('ANALYSIS_DB_TABLE_NAME')
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
            missing = [var for var, value in locals().items() if value is None]
            logger.error(
                f"Missing environment variables: {', '.join(missing)}"
            )
            raise EnvironmentError("Missing required environment variables.")


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
    def convert_to_serializable(obj):
        """
        Converts Azure Text Analytics result objects into a serializable format

        Args:
            obj: The Azure Text Analytics result object.

        Returns:
            A serializable representation of the Azure Text Analytics result.
        """
        if isinstance(obj, list):
            return [TextAnalysis.convert_to_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            obj_dict = {
                key: TextAnalysis.convert_to_serializable(value)
                for key, value in obj.__dict__.items()
            }
            # Special handling for models with properties that
            # need custom handling
            if hasattr(obj, 'sentences'):
                obj_dict['sentences'] = [
                    TextAnalysis.convert_to_serializable(sentence)
                    for sentence in obj.sentences
                ]
            if hasattr(obj, 'entities'):
                obj_dict['entities'] = [
                    TextAnalysis.convert_to_serializable(entity)
                    for entity in obj.entities
                ]
            # Add more conditions as needed for other types
            return obj_dict
        elif isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        else:
            return str(obj)  # Fallback to string representation

    @staticmethod
    async def analyze_text(client, document):
        """
        Performs various text analytics tasks on a given document.

        Args:
            client (TextAnalyticsClient): The Azure Text Analytics client.
            document (str): The text document to analyze.

        Returns:
            A dictionary of analysis results such as sentiment, entities, etc.
        """
        async with client:
            sentiment_result = await client.analyze_sentiment([document])
            entity_result = await client.recognize_entities([document])
            key_phrases_result = await client.extract_key_phrases([document])
            language_result = await client.detect_language([document])
            pii_result = await client.recognize_pii_entities([document])

        return {
            "sentiment": sentiment_result if sentiment_result else None,
            "entities": entity_result if entity_result else None,
            "key_phrases": key_phrases_result if key_phrases_result else None,
            "language": language_result if language_result else None,
            "pii": pii_result if pii_result else None,
            # Add other results as needed
        }

    @staticmethod
    async def process_text_file(client, input_file):
        """
        Processes a text file for analysis.

        Args:
            client (TextAnalyticsClient): The Azure Text Analytics client.
            input_file (str): Path to the text file to be processed.
        """
        print(f"Processing file: {input_file}")
        with open(input_file, 'r') as file:
            text = file.read()
            analysis_results = await TextAnalysis.analyze_text(client, text)
            print(f"Analysis results for {input_file}: {analysis_results}")
            await TextAnalysis.save_results(input_file, analysis_results)

    @staticmethod
    async def save_results(input_file, results):
        """
        Saves analysis results in different formats.

        Args:
            input_file (str): Path to the input text file.
            results (dict): The analysis results to save.
        """
        # Create 'Analysis' folder if it doesn't exist
        config = Config()
        if not os.path.exists(config.reports):
            os.makedirs(config.reports)

        # Modify the path to save files inside the 'Analysis' folder
        base_filename = os.path.splitext(os.path.basename(input_file))[0]

        # Save to TXT with plain text format
        txt_filename = os.path.join(
            config.reports, f'{base_filename}_analysis.txt'
        )
        with open(txt_filename, 'w') as file:
            current_time = datetime.datetime.now().strftime(
                '%Y-%m-%d %H:%M:%S'
            )
            # Executive summary format
            file.write('Transcription analysis\n\n')
            file.write(f'File: {input_file}\n')
            file.write(f'Time: {current_time}\n\n')
            file.write('Summary:\n')

            # Sentiment Analysis Summary
            sentiment_result = results['sentiment'][0]
            file.write(
                f'• Overall Sentiment: {sentiment_result.sentiment}.\n'
            )

            # Enhanced Sentiment Analysis Summary
            sentiment_scores = sentiment_result.confidence_scores
            file.write(
                f'• Sentiment Scores - Positive:'
                f'{sentiment_scores.positive:.2f},'
                f'Neutral: {sentiment_scores.neutral:.2f},'
                f'Negative: {sentiment_scores.negative:.2f}\n'
            )

            # Key Entities Summary
            entities_result = results['entities'][0]
            if entities_result.entities:
                key_entities = [
                    entity.text for entity in entities_result.entities[:5]
                ]
                key_entities_text = ', '.join(key_entities)
                message = f'• Key Entities Identified: {key_entities_text}.\n'
                file.write(message)

            # Enhanced Key Phrases Summary
            key_phrases_result = results['key_phrases'][0]
            if key_phrases_result.key_phrases:
                file.write(
                    '   • Notable Topics: '
                    + ', '.join(key_phrases_result.key_phrases[:5])
                    + '.\n'
                )

            # Language Detection Summary
            language_result = results['language'][0]
            file.write(
                f'• Detected Language: {language_result.primary_language.name}'
                f'({language_result.primary_language.iso6391_name}).\n'
            )

            # PII Summary (if applicable)
            pii_result = results['pii'][0]
            if pii_result.entities:
                file.write('• Personally identifiable information (PII): Yes.')
            else:
                file.write('• Personally identifiable information (PII): No.')

        print(f'Saving results to {txt_filename}')

        # Save to JSON
        json_filename = os.path.join(
            config.reports, f'{base_filename}_analysis.json'
        )
        with open(json_filename, 'w') as json_file:
            json.dump(
                TextAnalysis.convert_to_serializable(results),
                json_file,
                indent=4
            )
        print(f'Saving results to {json_filename}')

        # Save to SQLite
        db_filename = os.path.join(config.reports, 'text_analysis.db')
        with sqlite3.connect(db_filename) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'''CREATE TABLE IF NOT EXISTS {config.db_name}
                            (filename TEXT, analysis TEXT)'''
            )
            cursor.execute(
                f"INSERT INTO {config.db_name} (filename, analysis)"
                f"VALUES (?, ?)",
                (input_file, json.dumps(
                    TextAnalysis.convert_to_serializable(results)
                )),
            )
            conn.commit()
        print(f'Saved analysis of {input_file} to database.')


async def azure_text_analysis():
    """
    Main function to initialize and run text analysis on all text files.
    """
    try:
        # Initialize configuration and process each text file
        config = Config()
        if not os.path.exists(config.reports):
            os.makedirs(config.reports)

        endpoint = config.az_lg_endpoint
        key = config.az_lg_key

        for filename in os.listdir(config.transcripts):
            if filename.endswith('.txt'):
                input_file = os.path.join(config.transcripts, filename)
                client = TextAnalyticsClient(
                    endpoint=endpoint,
                    credential=AzureKeyCredential(key)
                )
                await TextAnalysis.process_text_file(client, input_file)

        print('All files processed.')

    except Exception as e:
        logger.error(f"Script execution failed: {e}")


if __name__ == '__main__':
    # Run the main function in an asyncio event loop
    asyncio.run(azure_text_analysis())
