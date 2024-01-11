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
This script uses the OpenAI API to generate recommendations for Azure based on
customer transcripts.

The script takes the following environment variables:

GPT3_API_KEY: Your OpenAI API key
TRANSCRIPTS_FOLDER: The folder containing the customer transcripts
RECOMMENDATIONS_FOLDER: The folder where the recommendations will be saved

The script does the following:

1. Reads the transcript files from the TRANSCRIPTS_FOLDER
2. Generates a recommendation for each transcript using the OpenAI API
3. Saves the recommendations to the RECOMMENDATIONS_FOLDER
"""

# Import the dependencies
import openai
import os
import logging
import uuid
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
    """
    Configuration class for the script. Reads the environment variables and
    validates their presence.
    """
    def __init__(self):
        self.GPT3_API_KEY = os.getenv('GPT3_API_KEY')
        self.TRANSCRIPTS_FOLDER = os.getenv('TRANSCRIPTS_FOLDER')
        self.RECOMMENDATIONS_FOLDER = os.getenv('RECOMMENDATIONS_FOLDER')
        self.validate()

    def validate(self):
        """
        Validates that the required environment variables are present.
        """
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
    """
    Class for generating recommendations. Reads the transcript files and
    generates recommendations for each one.
    """
    def __init__(self, config):
        self.config = config

    def generate_recommendations(self):
        """
        Generates recommendations for all the transcript files in the
        TRANSCRIPTS_FOLDER.
        """
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
        """
        Generates a recommendation for a given transcript.
        """
        # Replace with your GPT-3 API key
        api_key = self.config.GPT3_API_KEY

        # Initialize the OpenAI API client
        openai.api_key = api_key

        # Example prompt for generating a recommendation
        prompt = """
Summarize key insights from the provided transcripts in a concise executive
summary (10-15% of original length), suitable for senior banking and finance
leaders. The summary should be formatted for ease of comprehension, neutral,
objective, and fact-based. Avoid subjective language or tone.

- Briefly mention the source (e.g., customer calls, market research) and
objectives of the discussion/research.
- Organize the summary with clear section headings such as 'Key Findings',
'Trends', and 'Strategic Recommendations'.
- Include 3-5 bullet points for crucial findings, 2-3 sentences for trends,
etc.
- Prioritize the most crucial, actionable findings in short, focused bullet
points.
- Highlight important trends in 1-2 brief summary sentences.
- Provide forward-looking strategic recommendations focused on improving
customer satisfaction.
- Separate each main insight/finding/recommendation with line breaks.
- Use clear, industry-specific business language appropriate for senior
executives in banking and finance.
"""

        conversation_id = str(uuid.uuid4())
        logger.info(f"Conversation ID: {conversation_id}")
        # Generate text for the input transcript
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=f"{conversation_id}\n{prompt}{input_text}\n",
            temperature=0.8,
            max_tokens=1024,
            n=1,
            stop=None,
        )

        generated_text = response.choices[0].text.strip()
        return generated_text


def azure_recommendation():
    """
    Main function for the script. Reads the configuration and calls the
    recommendation generation function.
    """
    try:
        config = Config()

        recommendations_generator = RecommendationsGenerator(config)
        recommendations_generator.generate_recommendations()
    except Exception as e:
        logger.error(f"Script execution failed: {e}")


if __name__ == "__main__":
    azure_recommendation()
