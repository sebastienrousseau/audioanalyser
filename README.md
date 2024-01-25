<!-- markdownlint-disable MD033 MD041 -->

<img
src="https://kura.pro/audioanalyser/images/logos/audioanalyser.webp"
align="right"
alt="Audio Analyser's logo"
height="261"
width="261"
/>

<!-- markdownlint-enable MD033 MD041 -->

# Audio Analyser: Speech-to-Text, Analysis, Recommendations & Translations

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

## Table of Contents

- [Audio Analyser: Speech-to-Text, Analysis, Recommendations \& Translations](#audio-analyser-speech-to-text-analysis-recommendations--translations)
  - [Overview](#overview)
  - [Table of Contents](#table-of-contents)
  - [Key Features](#key-features)
  - [Built on a Robust Foundation](#built-on-a-robust-foundation)
  - [Dependencies](#dependencies)
  - [Installation](#installation)
    - [Create a Virtual Environment](#create-a-virtual-environment)
    - [Installation and Setup](#installation-and-setup)
    - [Getting Started](#getting-started)
    - [Usage Instructions](#usage-instructions)
      - [To run the Audio Analyser CLI](#to-run-the-audio-analyser-cli)
      - [To run the Audio Analyser server](#to-run-the-audio-analyser-server)
  - [Usage](#usage)
    - [Requirements](#requirements)
  - [Configuration](#configuration)
  - [Modules](#modules)
    - [Audio Recorder Module](#audio-recorder-module)
      - [Key Features](#key-features-1)
      - [How It Works](#how-it-works)
      - [Usage](#usage-1)
      - [Customization and Flexibility](#customization-and-flexibility)
      - [Scalability and Reliability](#scalability-and-reliability)
    - [Analyze Text Files Module](#analyze-text-files-module)
      - [Key Features](#key-features-2)
      - [How It Works](#how-it-works-1)
      - [Usage](#usage-2)
      - [Customization](#customization)
      - [Scalability and Performance](#scalability-and-performance)
    - [Azure Recommendation Module](#azure-recommendation-module)
      - [Key Features](#key-features-3)
      - [How It Works](#how-it-works-2)
      - [Usage](#usage-3)
      - [Customization and Flexibility](#customization-and-flexibility-1)
      - [Scalability and Innovation](#scalability-and-innovation)
    - [Speech Text Server Module](#speech-text-server-module)
      - [Key Features](#key-features-4)
      - [How It Works](#how-it-works-3)
      - [Usage](#usage-4)
      - [Customization and Scalability](#customization-and-scalability)
      - [Advanced Technology Integration](#advanced-technology-integration)
    - [Transcribe Audio Files Module](#transcribe-audio-files-module)
      - [Key Features](#key-features-5)
      - [How It Works](#how-it-works-4)
      - [Usage](#usage-5)
      - [Customization and Versatility](#customization-and-versatility)
      - [Scalability and Integration](#scalability-and-integration)
    - [Translations Module](#translations-module)
      - [Key Features](#key-features-6)
      - [How It Works](#how-it-works-5)
      - [Usage](#usage-6)
      - [Supported Languages](#supported-languages)
      - [Error Handling and Logging](#error-handling-and-logging)
      - [Extensibility](#extensibility)
  - [License](#license)
  - [Contribution](#contribution)
  - [Acknowledgements](#acknowledgements)

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
- **Translations:** Translate text to and from a variety of languages using Azure's Translator API.
  - **Support for Multiple Languages:** Supports a wide range of languages, including English, French, German, Spanish, and more.
  - **Batch Translation:** Translate multiple text files simultaneously, saving time and effort.
  - **Flexible Output Options:** Output translation results in various formats, including plain text files, JSON, and SQLite databases.
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

![Audio Analyser Architecture][diagram]

### Audio Recorder Module

The Audio Recorder Module in Audio Analyser is a robust tool designed for high-quality audio recording. It integrates seamlessly with the rest of the application, providing a user-friendly interface for capturing audio data, which is essential for the subsequent speech-to-text and analysis processes.

#### Key Features

- **High-Quality Recording**: Capture clear and crisp audio, which is vital for accurate speech-to-text conversion.
- **Flexible Configuration**: Utilizes a `Config` class to load settings from a `.env` file, allowing for easy customization of recording parameters such as duration, format, and quality.
- **Directory Management**: Automatically validates and manages input and output directories, ensuring a smooth and error-free recording experience.
- **Advanced Audio Settings Validation**: Checks and confirms audio settings before recording begins, thereby minimizing potential issues during the recording process.
- **Automated File Path Generation**: Dynamically generates file paths for the recorded audio, streamlining the file management process.

#### How It Works

1. **Setup and Configuration**: The module reads configurations from the `.env` file, setting up necessary parameters for recording.
2. **Directory Validation**: It checks the specified input and output directories to ensure they exist and are accessible.
3. **Recording Execution**: On initiating the recording process, the module captures audio based on predefined settings. This can be triggered manually or automatically as part of a larger workflow.
4. **File Management**: After recording, the audio file is saved to the designated output directory, with a file name generated based on customizable rules.

#### Usage

- To start recording, ensure that the environment variables are set up in the `.env` file.
- Run the Audio Recorder Module through the Audio Analyser interface or as a standalone process.
- The module will handle the rest, from validating settings to saving the recorded audio file.

#### Customization and Flexibility

- The module can be customized to record audio for variable durations and in different formats, as required by the user.
- It's designed to be flexible enough to integrate with different audio sources and output requirements.

#### Scalability and Reliability

- Designed to handle both small-scale and large-scale audio recording tasks.
- Implements robust error handling to deal with potential recording issues, ensuring reliability in diverse environments.

---

### Analyze Text Files Module

The Analyze Text Files Module in Audio Analyser is a sophisticated tool designed for in-depth analysis of text data, utilizing Azure Text Analytics. It’s capable of extracting meaningful insights from text files, such as sentiment, key entities, and more, making it an essential component for understanding and interpreting textual data.

#### Key Features

- **Advanced Text Analytics**: Leverages Azure's AI capabilities for comprehensive analysis including sentiment analysis, entity recognition, and key phrase extraction.
- **Configurable Environment**: Uses the `Config` class to seamlessly integrate with Azure Language services, ensuring a flexible and customizable setup.
- **Diverse Output Formats**: Capable of saving analysis results in multiple formats, accommodating various data presentation and storage needs.
- **Efficient File Processing**: Processes text files for analysis efficiently, handling both single files and batches, suitable for different scales of data.

#### How It Works

1. **Environment Setup**: The module begins by setting up necessary configurations using environment variables. This includes connecting to Azure Language services.
2. **File Processing**: It reads text files from a specified directory, preparing them for analysis.
3. **Executing Text Analysis**: The `TextAnalysis` class performs various analytics tasks on the text data, extracting insights like overall sentiment, key entities, and phrases.
4. **Storing Results**: Analysis results are then stored in the preferred format, be it plain text, JSON, or another format, in the designated output directory.

#### Usage

- Ensure that the Azure service credentials and other settings are correctly configured in the `.env` file.
- Place the text files to be analyzed in the specified input directory.
- Execute the Analyze Text Files Module, which will automatically process the files and save the analysis results.

#### Customization

- The module allows for customization of analysis parameters and output formats, catering to specific needs of the analysis task.
- Users can specify particular aspects of text analysis to focus on, such as sentiment analysis or entity extraction, based on their requirements.

#### Scalability and Performance

- Optimized for performance, the module can handle large volumes of text data without compromising on speed or accuracy.
- Scalable architecture ensures that the module can adapt to increasing amounts of data as the application grows.

This module represents a vital part of the Audio Analyser’s capability to turn textual data into actionable insights, enhancing the overall value of the analysis process.

---

### Azure Recommendation Module

The Azure Recommendation Module in Audio Analyser is an advanced tool that leverages the power of OpenAI's GPT-3 to generate insightful and relevant recommendations from customer transcripts. This module transforms raw text data into actionable advice, enhancing decision-making processes.

#### Key Features

- **Intelligent Recommendations**: Utilizes OpenAI's GPT-3 for generating smart and contextually relevant recommendations based on the content of customer transcripts.
- **Automated Transcript Processing**: Automatically reads and processes transcripts from a designated directory, streamlining the workflow.
- **Customizable Output**: Offers flexibility in saving recommendations to a preferred format and location, tailored to user requirements.
- **Configurable Settings**: Allows users to configure various parameters like API keys, folder paths, and output preferences through environment variables.

#### How It Works

1. **Reading Transcripts**: The module scans a specified directory to load customer transcripts, ensuring that all relevant data is considered for analysis.
2. **Generating Recommendations**: Leverages GPT-3's advanced natural language understanding capabilities to analyze the transcripts and generate recommendations.
3. **Saving Outputs**: The insightful recommendations are then saved in a designated folder, in a format that facilitates easy review and implementation.

#### Usage

- Set up the necessary environment variables, including API keys and directory paths, in the `.env` file.
- Place the transcripts in the specified input directory.
- Run the Azure Recommendation Module to automatically process the transcripts and generate recommendations.
- Access the generated recommendations in the specified output directory.

#### Customization and Flexibility

- Users can customize the type of recommendations generated by tweaking the prompt strategy sent to GPT-3, enabling tailored advice for different scenarios.
- The module supports various output preferences, allowing users to choose how and where the recommendations are stored.

#### Scalability and Innovation

- Designed to handle a wide range of transcript volumes, from individual files to large batches, ensuring scalability.
- Represents a cutting-edge application of AI in text analysis, setting a new standard for automated recommendation systems.

This module is a testament to the Audio Analyser's commitment to harnessing the latest in AI technology to provide valuable, data-driven insights and recommendations.

---

### Speech Text Server Module

The Speech Text Server Module in Audio Analyser is a robust server-side component designed to handle speech-to-text processing efficiently. This module serves as the backbone of the application, managing the conversion of audio data into text and further analyzing this textual data for insights.

#### Key Features

- **Comprehensive Speech-to-Text Operations**: Employs advanced algorithms to accurately transcribe spoken words into written text, forming the basis for further analysis.
- **Integrated Audio Recording and Analysis**: Seamlessly records audio, transcribes it, and then analyzes the text to extract meaningful insights.
- **Recommendation Generation**: Utilizes transcribed text to generate actionable recommendations, adding significant value to the analysis process.
- **Efficient Request Handling**: Capable of managing various server operations and handling multiple client requests simultaneously, ensuring a smooth user experience.

#### How It Works

1. **Audio Processing**: Initially, the module captures and processes audio recordings, preparing them for transcription.
2. **Speech-to-Text Conversion**: Utilizes advanced speech recognition technology to transcribe audio data into text with high accuracy.
3. **Text Analysis and Recommendations**: Once the audio is transcribed, the module analyzes the text data, extracting key insights and generating recommendations based on the content.
4. **Server Operations**: Manages all server-side functionalities, ensuring efficient processing and response to client requests.

#### Usage

- The module is typically used as a part of the Audio Analyser's server-side operations.
- It can handle requests for audio processing, transcription, text analysis, and recommendation generation.
- Ideal for applications requiring real-time speech-to-text conversion and subsequent analysis.

#### Customization and Scalability

- Customizable to suit various speech-to-text scenarios and can be configured to handle specific analysis requirements.
- Scalable to accommodate a growing number of requests and larger data sets, making it suitable for both small-scale and large-scale applications.

#### Advanced Technology Integration

- Integrates state-of-the-art speech recognition and natural language processing technologies to provide fast and accurate transcriptions.
- The module's architecture allows for easy integration with additional AI services and tools for enhanced functionality.

The Speech Text Server Module is crucial for transforming raw audio data into actionable textual information, thereby playing a vital role in the Audio Analyser's capability to deliver comprehensive audio analysis solutions.

---

### Transcribe Audio Files Module

The Transcribe Audio Files Module in Audio Analyser is a specialized component designed to convert spoken language in audio files into accurate text. Utilizing Azure's state-of-the-art Speech-to-Text API, this module is an essential tool for transforming audio data into a format that can be easily analyzed and processed.

#### Key Features

- **High-Efficiency Transcription**: Leverages Azure's powerful Speech-to-Text API to provide fast and accurate transcription of audio files.
- **Batch Processing Capability**: Capable of processing both individual audio files and large batches, making it versatile for various project sizes.
- **Robust Error Handling**: Incorporates sophisticated error handling mechanisms to ensure reliability even in cases of challenging audio quality or API issues.
- **Flexible Output Options**: Transcriptions can be saved in multiple formats, including plain text files, JSON, and SQLite databases, catering to diverse data management needs.

#### How It Works

1. **Audio File Processing**: The module accepts audio files as input, processing them individually or in batches based on user requirements.
2. **Speech-to-Text Conversion**: Utilizes Azure's Speech-to-Text API to accurately transcribe the spoken words in the audio files into written text.
3. **Error Management**: During transcription, the module efficiently handles any errors or exceptions, ensuring consistent output quality.
4. **Saving Transcripts**: The transcribed text is then saved in the specified format, allowing for easy integration with other modules or systems.

#### Usage

- Place the audio files in the designated input directory.
- Execute the Transcribe Audio Files Module through the Audio Analyser interface.
- The module will automatically process the audio files and save the transcriptions in the chosen format.

#### Customization and Versatility

- Users can customize various aspects of the transcription process, including the choice of output format and error handling strategies.
- The module's design allows it to handle different audio formats and qualities, making it adaptable to a wide range of audio data sources.

#### Scalability and Integration

- Scalable to handle increasing volumes of audio data, suitable for both small-scale and large-scale transcription tasks.
- Seamlessly integrates with other Azure services and modules within the Audio Analyser application, enhancing the overall functionality of the system.

This module plays a pivotal role in the Audio Analyser's ability to extract textual data from audio, laying the foundation for in-depth analysis and insight generation.

---

### Translations Module

The Translations Module in Audio Analyser is specifically designed to handle multilingual text translation tasks, leveraging Azure AI Translator API. This powerful service offers cloud-based neural machine translation, compatible across different operating systems, to provide seamless translation experiences.

#### Key Features

- **Batch Translation**: Process multiple text files simultaneously, offering efficiency and time-saving for large-scale translation tasks.
- **Support for Multiple Languages**: Capable of translating text to and from a variety of languages, as listed in the Languages Supported section.
- **Format Versatility**: Output translation results in diverse formats, including plain text files, JSON, and SQLite databases, catering to different use case requirements.
- **Seamless Integration with Azure Translator API**: Utilizes Azure's robust machine translation capabilities for accurate and context-aware translations.
- **Error Handling**: Incorporates comprehensive error handling mechanisms to ensure reliable translation processes even in case of unexpected API behavior.

#### How It Works

1. **File Processing**: The module takes text files as input. It can process individual files or batches of files, making it adaptable to both small and large-scale translation tasks.
2. **Translation Execution**: Utilizes Azure's Translator API to translate the content of the text files. It supports a wide range of languages, providing versatility for global use cases.
3. **Output Generation**: After translation, the results are outputted in the user-preferred format. The module supports various output formats like JSON, TXT, and SQLite, providing flexibility in how the results are utilized.

#### Usage

- To translate a text file, place it in the specified input directory.
- Run the translation module through the Audio Analyser interface.
- Choose your target language and output format.
- The translated text will be saved in the designated output directory in the chosen format.

#### Supported Languages

Below is a list of languages supported by the Translations Module, along with their respective language codes:

| Language                  | Language code |
|---------------------------|---------------|
| Afrikaans                 | af            |
| Albanian                  | sq            |
| Amharic                   | am            |
| Arabic                    | ar            |
| Armenian                  | hy            |
| Assamese                  | as            |
| Azerbaijani (Latin)       | az            |
| Bangla                    | bn            |
| Bashkir                   | ba            |
| Basque                    | eu            |
| Bhojpuri                  | bho           |
| Bodo                      | brx           |
| Bosnian (Latin)           | bs            |
| Bulgarian                 | bg            |
| Cantonese (Traditional)   | yue           |
| Catalan                   | ca            |
| Chinese (Literary)        | lzh           |
| Chinese Simplified        | zh            |
| Chinese Traditional       | zh            |
| chiShona                  | sn            |
| Croatian                  | hr            |
| Czech                     | cs            |
| Danish                    | da            |
| Dari                      | prs           |
| Divehi                    | dv            |
| Dogri                     | doi           |
| Dutch                     | nl            |
| English                   | en            |
| Estonian                  | et            |
| Faroese                   | fo            |
| Fijian                    | fj            |
| Filipino                  | fil           |
| Finnish                   | fi            |
| French                    | fr            |
| French (Canada)           | fr            |
| Galician                  | gl            |
| Georgian                  | ka            |
| German                    | de            |
| Greek                     | el            |
| Gujarati                  | gu            |
| Haitian Creole            | ht            |
| Hausa                     | ha            |
| Hebrew                    | he            |
| Hindi                     | hi            |
| Hmong Daw (Latin)         | mww           |
| Hungarian                 | hu            |
| Icelandic                 | is            |
| Igbo                      | ig            |
| Indonesian                | id            |
| Inuinnaqtun               | ikt           |
| Inuktitut                 | iu            |
| Inuktitut (Latin)         | iu            |
| Irish                     | ga            |
| Italian                   | it            |
| Japanese                  | ja            |
| Kannada                   | kn            |
| Kashmiri                  | ks            |
| Kazakh                    | kk            |
| Khmer                     | km            |
| Kinyarwanda               | rw            |
| Klingon                   | tlh           |
| Klingon (plqaD)           | tlh           |
| Konkani                   | gom           |
| Korean                    | ko            |
| Kurdish (Central)         | ku            |
| Kurdish (Northern)        | kmr           |
| Kyrgyz (Cyrillic)         | ky            |
| Lao                       | lo            |
| Latvian                   | lv            |
| Lithuanian                | lt            |
| Lingala                   | ln            |
| Lower Sorbian             | dsb           |
| Luganda                   | lug           |
| Macedonian                | mk            |
| Maithili                  | mai           |
| Malagasy                  | mg            |
| Malay (Latin)             | ms            |
| Malayalam                 | ml            |
| Maltese                   | mt            |
| Maori                     | mi            |
| Marathi                   | mr            |
| Mongolian (Cyrillic)      | mn            |
| Mongolian (Traditional)   | mn            |
| Myanmar                   | my            |
| Nepali                    | ne            |
| Norwegian                 | nb            |
| Nyanja                    | nya           |
| Odia                      | or            |
| Pashto                    | ps            |
| Persian                   | fa            |
| Polish                    | pl            |
| Portuguese (Brazil)       | pt            |
| Portuguese (Portugal)     | pt            |
| Punjabi                   | pa            |
| Queretaro Otomi           | otq           |
| Romanian                  | ro            |
| Rundi                     | run           |
| Russian                   | ru            |
| Samoan (Latin)            | sm            |
| Serbian (Cyrillic)        | sr            |
| Serbian (Latin)           | sr            |
| Sesotho                   | st            |
| Sesotho sa Leboa          | nso           |
| Setswana                  | tn            |
| Sindhi                    | sd            |
| Sinhala                   | si            |
| Slovak                    | sk            |
| Slovenian                 | sl            |
| Somali (Arabic)           | so            |
| Spanish                   | es            |
| Swahili (Latin)           | sw            |
| Swedish                   | sv            |
| Tahitian                  | ty            |
| Tamil                     | ta            |
| Tatar (Latin)             | tt            |
| Telugu                    | te            |
| Thai                      | th            |
| Tibetan                   | bo            |
| Tigrinya                  | ti            |
| Tongan                    | to            |
| Turkish                   | tr            |
| Turkmen (Latin)           | tk            |
| Ukrainian                 | uk            |
| Upper Sorbian             | hsb           |
| Urdu                      | ur            |
| Uyghur (Arabic)           | ug            |
| Uzbek (Latin)             | uz            |
| Vietnamese                | vi            |
| Welsh                     | cy            |
| Xhosa                     | xh            |
| Yoruba                    | yo            |
| Yucatec Maya              | yua           |
| Zulu                      | zu            |

#### Error Handling and Logging

The module is designed to robustly handle various errors, including API connection issues, file reading/writing errors, and unsupported language codes. Detailed logs are generated for troubleshooting and audit purposes.

#### Extensibility

This module is built with extensibility in mind, allowing for future enhancements such as additional language support, improved translation accuracy, and integration with other translation services or custom models.

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
[diagram]: ./audio-analyser-architecture.png "Audio Analyser Architecture"
[license-badge]: https://img.shields.io/pypi/l/audioanalyser?style=for-the-badge 'License badge'
[pypi-badge]: https://img.shields.io/pypi/pyversions/audioanalyser.svg?style=for-the-badge 'PyPI badge'
[pypi-downloads-badge]:https://img.shields.io/pypi/dm/audioanalyser.svg?style=for-the-badge 'PyPI Downloads badge'

[divider]: https://kura.pro/common/images/elements/divider.svg "Divider"
