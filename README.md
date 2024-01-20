<!-- markdownlint-disable MD033 MD041 -->

<img
src="https://kura.pro/audioanalyser/images/logos/audioanalyser.webp"
align="right"
alt="Audio Analyser's logo"
height="261"
width="261"
/>

<!-- markdownlint-enable MD033 MD041 -->

# Audio Analyser: Speech-to-Text & Analysis

![Audio Analyser banner][banner]

<!-- markdownlint-disable MD033 MD041 -->
<center>
<!-- markdownlint-enable MD033 MD041 -->

[![PyPI][pypi-badge]][03] [![PyPI Downloads][pypi-downloads-badge]][07] [![License][license-badge]][01] [![Codecov][codecov-badge]][06] [![License][license-badge]][02]

• [Website][00]
• [Report Bug][03]
• [Request Feature][03]
• [Contributing Guidelines][04]

<!-- markdownlint-disable MD033 MD041 -->
</center>
<!-- markdownlint-enable MD033 MD041 -->

![divider][divider]

## Overview

**Audio Analyser** leverages the power of Microsoft Azure's advanced AI services to transform your audio data into valuable insight reports in no time through automatic speech-to-text, text analysis, and recommendations.

- **Solve the pain of manual audio analysis:** Manually analyzing audio is time consuming and limited. Audio Analyser automates the process, quickly surfacing key insights through AI-powered speech and language processing.
- **Discover Hidden Insights in Minutes**: AI-Powered Audio Analysis for Your Call Recordings and Audio Files.
- **Streamline call recording and audio file transcription**, uncover actionable insights in seconds with advanced text analysis, powered by Microsoft Azure AI services
- **Go beyond simple transcription:** Discover sentiment, key information, and gain a multi-faceted understanding of your conversations through in-depth analysis and comprehensive reports.
- **Audio Analyser** leverages the power of Azure's advanced AI services to transform your audio data into valuable insight reports in no time.

![divider][divider]

## Key Features

- **Audio Recording**: Record audio files and conversations.
- **Speech to Text**: Convert spoken language into text using Azure's speech-to-text service.
- **Instant Transcription:** Instantly transcribe audio files and recordings into text.
- **Text Analysis**: Analyze text for various features using Azure's text analytics service.
- **Recommendations:** Get actionable recommendations based on the results of the analysis.
- **Support for outputting results in different formats**, including JSON, TXT and SQLite.
- **Actionable Insights:**
  - Analyze text for various features, including Overall Sentiment, Positive/Negative Sentiment Analysis,  Identify Key Topics and Entities, Language, Personally Identifiable Information (PII).
  - Uncover sentiment and key information within conversations.
- **Data-Driven Reports:**
  - Generate detailed reports for easy sharing and analysis.
- **Web Server**: A CherryPy-based web server to handle incoming requests and process them.

![divider][divider]

## Built on a Robust Foundation

- **Azure-powered technology** and a secure **CherryPy web server** ensure accurate analysis and reliable data management.
- **Scalable architecture:** Adapt seamlessly to your needs, handling large datasets with ease.

**Experience the power of Audio Analyser today!**

![divider][divider]

## Dependencies

- CherryPy
- Azure Cognitive Services Speech SDK
- Azure AI Text Analytics
- Azure Open AI Services
- Python standard libraries: asyncio, threading, logging, sqlite3, json
- Dotenv for environment variable management

![divider][divider]

## Installation

Audio Analyser is built on Azure Cognitive Services for speech and language processing, with a CherryPy web server frontend. Key components include:

- **Audio Recorder** - record audio clips
- **Speech-to-Text** - transcribe audio
- **Text Analytics** - analyze transcripts
- **Recommendation Generator** - suggest actions
- **Web Server** - handle API requests

### Create a Virtual Environment

We recommend creating a virtual environment to install the Audio Analyser. This will ensure that the package is installed in an isolated environment and will not affect other projects.

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### Installation and Setup

1. Install required Python packages:

```bash
   pip install cherrypy azure-ai-textanalytics azure-cognitiveservices-speech
```

2. Set up Azure services and obtain necessary API keys.

3. Configure environment variables for Azure services in a `.env` file.

### Getting Started

Install `audioanalyser` with just one command:

```bash
pip install audioanalyser
```

### Usage Instructions

#### To run the Audio Analyser CLI

1. Start the CLI using `audioanalyser`:

```bash
python -m audioanalyser
```

2. Follow the instructions to utilize speech-to-text and text analysis features.

3. Access the generated transcript and report files in the `resources` directory in the root folder.

#### To run the Audio Analyser server

1. Start the server using `audioanalyser`:

```bash
python -m audioanalyser -s
```

2. Access the server at the specified host and port to utilize speech-to-text and text analysis features.

## Usage

To run the application, use the following command:

``` bash
python server.py
```

This will start the CherryPy web server, and you can interact with the application through the defined endpoints.

### Requirements

The minimum supported Python version is 3.6.

- Azure Cognitive Services for speech and text processing.
- CherryPy for the web server.
- Open AI Services for summarization.
- Python's standard libraries including asyncio, sqlite3, and threading.

![divider][divider]

## Configuration

Ensure that your Azure credentials and other configurations are correctly set in a `.env` file in the root directory.
Please refer to the `env.example` file for the required environment variables.

![divider][divider]

## Modules

### Audio Recorder Module

This module is designed for audio recording. It includes the `audio_recorder` main function, which initiates the audio recording process, leveraging the `Config` class for loading settings from a `.env` file and the `AudioRecorder` class for managing the recording process.

#### Functionality

- Ensures the audio recording environment is correctly set up.
- Validates input and output directories.
- Validates audio settings.
- Generates output file paths for recorded audio.

### Analyze Text Files Module

This module is designed for analyzing text files using Azure Text Analytics. It leverages the `Config` class for setting up the environment and the `TextAnalysis` class for performing and managing text analytics.

#### Functionality

- **Config Class:**
  - Sets up environment variables for Azure Language services.
  - Validates the presence of required environment variables for analysis.

- **TextAnalysis Class:**
  - Performs text analytics tasks, such as sentiment analysis and entity recognition.
  - Processes text for analysis, including handling associated filenames.
  - Saves analysis results in various formats.

- **Main Function:**
  - Runs text analysis on text files in a specified directory.

### Azure Recommendation Module

This module automates the generation of Azure service recommendations from customer transcripts, utilizing the OpenAI API.

#### Functionality

- Reads customer transcripts from a specified directory.
- Generates recommendations using OpenAI's GPT-3 service.
- Saves the recommendations to a designated folder.
- Configurable through environment variables like API key, transcript and recommendation folder paths, prompt strategy, and output preferences.

### Speech Text Server Module

This module serves as a server for processing speech-to-text analysis.

#### Functionality

- Manages speech-to-text operations.
- Provides functionalities like audio recording, text analysis, and recommendations generation.
- Handles various server operations and client requests.

### Transcribe Audio Files Module

This module is designed for transcribing audio files using Azure's Speech-to-Text API.

#### Functionality

- Processes audio files, either individually or in a batch, for transcription.
- Transcribes audio files to text using Azure's Speech-to-Text API.
- Supports error handling during the transcription process.
- Allows results to be written in different formats, including file, JSON, and SQLite database.

![divider][divider]

## License

The project is licensed under the terms of both the MIT license and the
Apache License (Version 2.0).

- [Apache License, Version 2.0][01]
- [MIT license][02]

![divider][divider]

## Contribution

We welcome contributions to **audioanalyser**. Please see the
[contributing instructions][04] for more information.

Unless you explicitly state otherwise, any contribution intentionally
submitted for inclusion in the work by you, as defined in the
Apache-2.0 license, shall be dual licensed as above, without any
additional terms or conditions.

![divider][divider]

## Acknowledgements

We would like to extend a big thank you to all the awesome contributors
of [audioanalyser][05] for their help and support.

[00]: https://audioanalyser.pro/ "Speech-to-Text & Analysis: Easy, Fast, Accurate."
[01]: https://opensource.org/license/apache-2-0/ "Apache License, Version 2.0"
[02]: http://opensource.org/licenses/MIT "MIT license"
[03]: https://github.com/sebastienrousseau/audioanalyser/issues "Audio Analyser on GitHub"
[04]: https://github.com/sebastienrousseau/audioanalyser/blob/main/CONTRIBUTING.md "Contributing Guidelines"
[05]: https://github.com/sebastienrousseau/audioanalyser/graphs/contributors "Contributors"
[06]: https://codecov.io/github/sebastienrousseau/audioanalyser?branch=main "Codecov"
[07]: https://pypi.org/project/audioanalyser/ "Audio Analyser on PyPI"

[banner]: https://kura.pro/audioanalyser/images/titles/title-audioanalyser.webp "Speech-to-Text & Analysis: Easy, Fast, Accurate."
[codecov-badge]: https://img.shields.io/codecov/c/github/sebastienrousseau/audioanalyser?style=for-the-badge&token=AaUxKfRiou 'Codecov badge'
[license-badge]: https://img.shields.io/pypi/l/audioanalyser?style=for-the-badge 'License badge'
[pypi-badge]: https://img.shields.io/pypi/pyversions/audioanalyser.svg?style=for-the-badge 'PyPI badge'
[pypi-downloads-badge]:https://img.shields.io/pypi/dm/audioanalyser.svg?style=for-the-badge 'PyPI Downloads badge'

[divider]: https://kura.pro/common/images/elements/divider.svg "Divider"
