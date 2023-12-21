# Copyright (C) 2023 Sebastien Rousseau.
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

import asyncio
import datetime
import os
import json
import logging
import sqlite3
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics.aio import TextAnalyticsClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set environment variables
DB_TABLE_NAME = 'text_analysis'

# Set up logging format
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s %(levelname)s app - %(message)s'
)
logger = logging.getLogger('AzureTextAnalysis')


class Config:
    def __init__(self):
        self.az_lg_endpoint = os.getenv('AZURE_LANGUAGE_ENDPOINT')
        self.az_lg_key = os.getenv('AZURE_LANGUAGE_KEY')
        self.transcripts = os.getenv('TRANSCRIPTS_FOLDER')
        self.reports = os.getenv('REPORTS_FOLDER')
        self.validate()

    def validate(self):
        required_vars = [
            self.az_lg_endpoint,
            self.az_lg_key,
            self.transcripts,
            self.reports,
            DB_TABLE_NAME,
        ]
        if any(var is None for var in required_vars):
            missing = [var for var, value in locals().items() if value is None]
            logger.error(
                f"Missing environment variables: {', '.join(missing)}"
            )
            raise EnvironmentError("Missing required environment variables.")


class TextAnalysis:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def convert_to_serializable(obj):
        """
        Converts Azure Text Analytics result objects into
        a serializable format.
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
        # Perform various text analytics tasks
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
        print(f"Processing file: {input_file}")
        with open(input_file, 'r') as file:
            text = file.read()
            analysis_results = await TextAnalysis.analyze_text(client, text)
            print(f"Analysis results for {input_file}: {analysis_results}")
            await TextAnalysis.save_results(input_file, analysis_results)

    @staticmethod
    async def save_results(input_file, results):
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
                f'''CREATE TABLE IF NOT EXISTS {DB_TABLE_NAME}
                            (filename TEXT, analysis TEXT)'''
            )
            cursor.execute(
                f"INSERT INTO {DB_TABLE_NAME} (filename, analysis)"
                f"VALUES (?, ?)",
                (input_file, json.dumps(
                    TextAnalysis.convert_to_serializable(results)
                )),
            )
            conn.commit()
        print(f'Saved analysis of {input_file} to database.')


async def azure_text_analysis():
    try:
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
    asyncio.run(azure_text_analysis())
