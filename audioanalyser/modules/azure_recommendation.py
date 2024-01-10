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

import openai  # Import the OpenAI library
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s app - %(message)s'
)
logger = logging.getLogger('AzureRecommendations')


class Config:
    def __init__(self):
        self.GPT3_API_KEY = os.getenv('GPT3_API_KEY')
        self.TRANSCRIPTS_FOLDER = os.getenv('TRANSCRIPTS_FOLDER')
        self.RECOMMENDATIONS_FOLDER = os.getenv('RECOMMENDATIONS_FOLDER')
        self.validate()

    def validate(self):
        required_vars = [
            self.GPT3_API_KEY,
            self.TRANSCRIPTS_FOLDER,
            self.RECOMMENDATIONS_FOLDER,
        ]
        if any(var is None for var in required_vars):
            missing = [
                var for var,
                value in locals().items() if value is None
            ]
            logger.error(
                f"Missing environment variables: {', '.join(missing)}"
            )
            raise EnvironmentError("Missing required environment variables.")


class RecommendationsGenerator:
    def __init__(self, config):
        self.config = config

    def generate_recommendations(self):
        # Create the output recommendations folder if it doesn't exist
        os.makedirs(self.config.RECOMMENDATIONS_FOLDER, exist_ok=True)

        # Iterate through .txt files in the transcripts folder
        for filename in os.listdir(self.config.TRANSCRIPTS_FOLDER):
            if filename.endswith(".txt"):
                # Read the transcript file
                with open(os.path.join(
                    self.config.TRANSCRIPTS_FOLDER, filename
                ), "r") as file:
                    transcript_text = file.read()

                # Generate a recommendation for the transcript
                recommendation_text = self.generate_recommendation(
                    transcript_text
                )

                # Create a filename for the recommendation with the
                # "azure_recommendation-" prefix
                recommendation_filename = f"azure_recommendation-{filename}"

                # Save the recommendation to the output folder
                with open(os.path.join(
                    self.config.RECOMMENDATIONS_FOLDER, recommendation_filename
                ), "w") as recommendation_file:
                    recommendation_file.write(recommendation_text)
                # Add a print statement to show the generated recommendation
                print(f"Generated recommendation for {filename}:")
                print(recommendation_text)

    def generate_recommendation(self, input_text):

        # Replace with your GPT-3 API key
        api_key = self.config.GPT3_API_KEY

        # Initialize the OpenAI API client
        openai.api_key = api_key

        # Example prompt for generating a recommendation
        prompt = """
    Provide a recommendation based on the following transcripts:\n"""

        # Generate text for the input transcript
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=f"{prompt}{input_text}\n",
            max_tokens=1000
        )

        generated_text = response.choices[0].text.strip()
        return generated_text


def azure_recommendation():
    try:
        config = Config()

        recommendations_generator = RecommendationsGenerator(config)
        recommendations_generator.generate_recommendations()
    except Exception as e:
        logger.error(f"Script execution failed: {e}")


if __name__ == "__main__":
    azure_recommendation()
