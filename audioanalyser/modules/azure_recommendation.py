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
This script is designed to automate the generation of recommendations for Azure
services based on customer transcripts. It utilizes the OpenAI API for
processing and analysing the transcripts. The script requires several
environment variables for configuration and outputs the recommendations in a
specified folder.

Environment Variables:
- GPT3_API_KEY: The API key for accessing OpenAI's GPT-3 service.
- TRANSCRIPTS_FOLDER: Directory path containing customer transcripts.
- RECOMMENDATIONS_FOLDER: Directory containing the generated recommendations.
- PROMPT_STRATEGY: Strategy for generating prompts (default: 'default').
- PROMPT_LENGTH_RATIO: Ratio of prompt length to total tokens (default: 0.1).
- OUTPUT_TONE: Desired tone for the recommendations (default: 'neutral').
- MAX_OUTPUT_LENGTH: Maximum length of generated recommendations in tokens.
- OUTPUT_VOICE: Desired voice for the recommendations (default: 'neutral').

Workflow:
1. Reads transcripts from the specified TRANSCRIPTS_FOLDER.
2. Utilizes OpenAI API to generate recommendations for each transcript.
3. Saves the recommendations in the RECOMMENDATIONS_FOLDER.
"""

# Importing necessary libraries and modules
import openai
from pathlib import Path
import logging
from dotenv import load_dotenv
from typing import Iterator
import os

# Load environment variables from .env file
load_dotenv()

# Set up logging format for better tracking and debugging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s app - %(message)s",
)
logger = logging.getLogger("AzureRecommendations")


class Config:
    """
    A configuration class to handle and validate environment variables.

    Attributes:
        GPT3_API_KEY (str): The API key for OpenAI GPT-3.
        TRANSCRIPTS_FOLDER (Path): Path to the folder containing customer
        transcripts.
        RECOMMENDATIONS_FOLDER (Path): Path to the folder where recommendations
        will be saved.
        PROMPT_STRATEGY (str): Strategy for generating prompts (default or
        fixed).
        PROMPT_LENGTH_RATIO (float): Ratio of prompt length to total tokens.
        OUTPUT_TONE (str): Desired tone for the generated recommendations
        (neutral, formal, casual).
        MAX_OUTPUT_LENGTH (int): Maximum length of generated recommendations
        in tokens.
        OUTPUT_VOICE (str): Desired voice for the generated recommendations
        (neutral, professional, friendly).

    Methods:
        validate(): Validates the environment variables and their
        configurations.
    """

    def __init__(self) -> None:
        # Initialization and environment variable extraction
        self.GPT3_API_KEY = os.getenv("GPT3_API_KEY")
        self.TRANSCRIPTS_FOLDER = Path(
            os.getenv("TRANSCRIPTS_FOLDER", "")
        )
        self.RECOMMENDATIONS_FOLDER = Path(
            os.getenv("RECOMMENDATIONS_FOLDER", "")
        )
        self.PROMPT_STRATEGY = os.getenv("PROMPT_STRATEGY", "default")
        self.PROMPT_LENGTH_RATIO = float(
            os.getenv("PROMPT_LENGTH_RATIO", 0.1)
        )
        self.OUTPUT_TONE = os.getenv("OUTPUT_TONE", "neutral")
        self.MAX_OUTPUT_LENGTH = int(
            os.getenv("MAX_OUTPUT_LENGTH", 2048)
        )
        self.OUTPUT_VOICE = os.getenv("OUTPUT_VOICE", "neutral")
        self.validate()

    def validate(self) -> None:
        """
        Validates the environment variables to ensure they meet the criteria.
        Checks include valid and writable directory paths, and proper numerical
        values where required.
        Raises:
            EnvironmentError: If any path is invalid or non-writable.
            ValueError: If numerical values are out of expected range.
        """
        if not self.TRANSCRIPTS_FOLDER.is_dir() or not os.access(
            self.TRANSCRIPTS_FOLDER, os.W_OK
        ):
            raise EnvironmentError(
                f"Invalid or non-writable TRANSCRIPTS_FOLDER path: "
                f"{self.TRANSCRIPTS_FOLDER}"
            )

        if not self.RECOMMENDATIONS_FOLDER.is_dir() or not os.access(
            self.RECOMMENDATIONS_FOLDER, os.W_OK
        ):
            raise EnvironmentError(
                f"Invalid or non-writable RECOMMENDATIONS_FOLDER path: "
                f"{self.RECOMMENDATIONS_FOLDER}"
            )

        if not 0 < self.PROMPT_LENGTH_RATIO <= 1:
            raise ValueError(
                "PROMPT_LENGTH_RATIO should be between 0 and 1."
            )

        if self.MAX_OUTPUT_LENGTH <= 0:
            raise ValueError(
                "MAX_OUTPUT_LENGTH should be a positive integer."
            )


class Transcript:
    """
    A class representing a customer transcript file.

    Attributes:
        path (Path): Path to the transcript file.
        text (str): Content of the transcript.

    Methods:
        load_transcript(): Loads and returns the content of the transcript file
        iter_transcripts(folder_path): A static method to iterate over
        transcripts in a given folder.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.text = self.load_transcript()

    def load_transcript(self) -> str:
        """
        Reads the transcript text from its file.

        Returns:
            str: The content of the transcript file.
        """
        with open(self.path, "r") as file:
            return file.read()

    @staticmethod
    def iter_transcripts(folder_path: Path) -> Iterator["Transcript"]:
        """
        Iterates over all transcript files in a specified folder.

        Args:
            folder_path (Path): The path to the folder containing transcript
            files.

        Yields:
            Iterator[Transcript]: An iterator of Transcript objects.
        """
        for path in folder_path.glob("*.txt"):
            yield Transcript(path)


class RecommendationsGenerator:
    """
    A class to generate recommendations from customer transcripts using
    OpenAI's GPT-3.

    Attributes:
        config (Config): Configuration object containing settings and
        environment variables.

    Methods:
        generate_recommendations(): Generates and saves recommendations for
        each transcript.
        generate_recommendation(transcript): Generates a recommendation for a
        single transcript.
        create_prompt(input_text): Creates a prompt for GPT-3 based on the
        input text.
        calculate_prompt_length(input_text): Calculates the length of the
        prompt based on the input text.
        get_tone_and_voice_prompts(): Determines the tone and voice for the
        prompt based on the configuration.
    """

    def __init__(self, config: Config) -> None:
        self.config = config

    def generate_recommendations(self) -> None:
        """
        Processes each transcript file and generates recommendations.
        The recommendations are saved in the configured recommendations folder.
        """
        self.config.RECOMMENDATIONS_FOLDER.mkdir(exist_ok=True)

        for transcript in Transcript.iter_transcripts(
            self.config.TRANSCRIPTS_FOLDER
        ):
            recommendation_text = self.generate_recommendation(
                transcript
            )

            recommendation_filename = (
                f"azure_recommendation-{transcript.path.name}"
            )
            with open(
                self.config.RECOMMENDATIONS_FOLDER
                / recommendation_filename,
                "w",
            ) as recommendation_file:
                recommendation_file.write(recommendation_text)

            logger.info(
                f"Generated recommendation for {transcript.path.name}"
            )

    def generate_recommendation(self, transcript: Transcript) -> str:
        """
        Generates a recommendation for a given transcript using the OpenAI
        GPT-3 model.

        Args:
            transcript (Transcript): The transcript object containing the text
            for which recommendation is needed.

        Returns:
            str: The generated recommendation text.
        """
        openai.api_key = self.config.GPT3_API_KEY

        prompt = self.create_prompt(transcript.text)
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=prompt,
            temperature=0.8,
            max_tokens=self.config.MAX_OUTPUT_LENGTH,
            n=1,
            stop=None,
        )

        return response.choices[0].text.strip()

    def create_prompt(self, input_text: str) -> str:
        """
        Constructs a prompt for the GPT-3 model based on the input text and
        configured settings.

        Args:
            input_text (str): The text of the transcript.

        Returns:
            str: The constructed prompt for GPT-3.
        """
        prompt_length = self.calculate_prompt_length(input_text)
        tone_prompt, voice_prompt = self.get_tone_and_voice_prompts()

        return (
            f"{tone_prompt}{voice_prompt}Summarize key insights from the "
            f"provided transcripts in a concise executive "
            f"summary ({prompt_length} tokens), suitable for C-Suite "
            f"and other senior executives and business "
            f"leaders. The summary should be clear & comprehensible, neutral, "
            f"objective, & fact-based. Avoid subjective language or tone.\n\n"
            f"- Briefly mention the source and objectives of the discussion.\n"
            f"- Organize the summary with clear section headings such as, "
            f"'Categories', 'Findings', 'Trends', and 'Recommendations'.\n"
            f"- Organize the summary with clear section headings.\n"
            f"- Include bullet points for crucial findings.\n"
            f"- Prioritize the most crucial, actionable findings.\n"
            f"- Highlight important trends.\n"
            f"- Provide forward-looking strategic recommendations.\n\n"
            f"{input_text}"
        )

    def calculate_prompt_length(self, input_text: str) -> int:
        """
        Determines the appropriate length for the GPT-3 prompt based on the
        input text and strategy.

        Args:
            input_text (str): The text of the transcript.

        Returns:
            int: The calculated length for the GPT-3 prompt.
        """
        total_tokens = len(input_text.split())
        if self.config.PROMPT_STRATEGY == "default":
            return max(
                1, int(total_tokens * self.config.PROMPT_LENGTH_RATIO)
            )
        elif self.config.PROMPT_STRATEGY == "fixed":
            return min(self.config.MAX_OUTPUT_LENGTH, total_tokens)
        else:
            raise ValueError(
                "Invalid PROMPT_STRATEGY value. Use 'default' or 'fixed'."
            )

    def get_tone_and_voice_prompts(self) -> tuple[str, str]:
        """
        Retrieves the tone and voice settings for the prompt based on the
        configuration.

        Returns:
            tuple[str, str]: A tuple containing the tone and voice settings.
        """
        tone_prompt = {
            "neutral": "",
            "formal": "Formal tone:\n\n",
            "casual": "Casual tone:\n\n",
        }.get(self.config.OUTPUT_TONE, "")
        voice_prompt = {
            "neutral": "",
            "professional": "Professional voice:\n\n",
            "friendly": "Friendly voice:\n\n",
        }.get(self.config.OUTPUT_VOICE, "")
        return tone_prompt, voice_prompt


def azure_recommendation() -> None:
    """
    Main function for executing the script. It initializes the configuration
    and triggers the recommendation generation process.
    """
    try:
        config = Config()
        recommendations_generator = RecommendationsGenerator(config)
        recommendations_generator.generate_recommendations()
    except Exception as e:
        logger.error(f"Script execution failed: {e}")


if __name__ == "__main__":
    azure_recommendation()
