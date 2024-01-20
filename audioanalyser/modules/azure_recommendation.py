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
# implied. See the License for the specific language governing permissions and
# limitations under the License.

"""
This script uses the OpenAI API to generate recommendations for Azure based on
customer transcripts.

The script takes the following environment variables:

GPT3_API_KEY: Your OpenAI API key
TRANSCRIPTS_FOLDER: The folder containing the customer transcripts
RECOMMENDATIONS_FOLDER: The folder where the recommendations will be saved
PROMPT_STRATEGY: The strategy for generating prompts (default: 'default')
PROMPT_LENGTH_RATIO: The ratio of prompt length to total tokens (default: 0.1)
OUTPUT_TONE: The desired tone of the generated recommendations (default: 'neutral')
MAX_OUTPUT_LENGTH: The maximum desired length of the generated recommendations in tokens (default: 200)
OUTPUT_VOICE: The desired voice for the generated recommendations (default: 'neutral')

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
        self.PROMPT_STRATEGY = os.getenv('PROMPT_STRATEGY', 'default')
        self.PROMPT_LENGTH_RATIO = float(os.getenv('PROMPT_LENGTH_RATIO', 0.1))
        self.OUTPUT_TONE = os.getenv('OUTPUT_TONE', 'neutral')
        self.MAX_OUTPUT_LENGTH = int(os.getenv('MAX_OUTPUT_LENGTH', 2048))
        self.OUTPUT_VOICE = os.getenv('OUTPUT_VOICE', 'neutral')
        self.validate()

    def validate(self):
        """
        Validates that the required environment variables are present and within
        expected ranges.
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
        
        # Validate PROMPT_LENGTH_RATIO is within a reasonable range
        if not 0 < self.PROMPT_LENGTH_RATIO <= 1:
            raise ValueError("PROMPT_LENGTH_RATIO should be between 0 and 1.")

        # Validate MAX_OUTPUT_LENGTH is a positive integer
        if self.MAX_OUTPUT_LENGTH <= 0:
            raise ValueError("MAX_OUTPUT_LENGTH should be a positive integer.")


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

        # Calculate prompt length based on strategy
        total_tokens = len(input_text.split())
        if self.config.PROMPT_STRATEGY == 'default':
            prompt_length = max(1, int(total_tokens * self.config.PROMPT_LENGTH_RATIO))
        elif self.config.PROMPT_STRATEGY == 'fixed':
            prompt_length = min(self.config.MAX_OUTPUT_LENGTH, total_tokens)
        else:
            raise ValueError("Invalid PROMPT_STRATEGY value. Use 'default' or 'fixed'.")

        # Determine output tone
        if self.config.OUTPUT_TONE == 'neutral':
            tone_prompt = ''
        elif self.config.OUTPUT_TONE == 'formal':
            tone_prompt = 'Formal tone:\n\n'
        elif self.config.OUTPUT_TONE == 'casual':
            tone_prompt = 'Casual tone:\n\n'
        else:
            raise ValueError("Invalid OUTPUT_TONE value. Use 'neutral', 'formal', or 'casual'.")

        # Determine output voice
        if self.config.OUTPUT_VOICE == 'neutral':
            voice_prompt = ''
        elif self.config.OUTPUT_VOICE == 'professional':
            voice_prompt = 'Professional voice:\n\n'
        elif self.config.OUTPUT_VOICE == 'friendly':
            voice_prompt = 'Friendly voice:\n\n'
        else:
            raise ValueError("Invalid OUTPUT_VOICE value. Use 'neutral', 'professional', or 'friendly'.")

        # Example prompt for generating a recommendation
        prompt = f"""
{tone_prompt}{voice_prompt}Summarize key insights from the provided transcripts in a concise executive
summary ({prompt_length} tokens), suitable for senior banking and finance
leaders. The summary should be clear and comprehensible, neutral,
objective, and fact-based. Avoid subjective language or tone.

- Briefly mention the source (e.g., customer calls, market research) and
objectives of the discussion/research.
- Organize the summary with clear section headings such as 'Categories', 'Key Findings',
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
            max_tokens=self.config.MAX_OUTPUT_LENGTH,
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
