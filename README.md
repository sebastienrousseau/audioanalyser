
<!-- markdownlint-disable MD033 MD041 -->

<img
src="https://kura.pro/audioanalyser/images/logos/audioanalyser.webp"
align="right"
alt="Audio Analyser's logo"
height="261"
width="261"
/>

<!-- markdownlint-enable MD033 MD041 -->

# Audio Analyser: Speech-to-Text & Analysis 🎙️

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

Analyse your conversations with ease. Our speech-to-text tool offers quick conversion and insightful text analysis.

![divider][divider]

## Features

- **Speech to Text**: Convert spoken language into text using Azure's speech-to-text service.
- **Text Analysis**: Analyze text for various features using Azure's text analytics service.
- **Web Server**: A CherryPy-based web server to handle incoming requests and process them.

![divider][divider]

## Installation

### Create a Virtual Environment

We recommend creating a virtual environment to install the Audio Analyser. This will ensure that the package is installed in an isolated environment and will not affect other projects.

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### Getting Started

Install `audioanalyser` with just one command:

```bash
pip install audioanalyser
```

## Usage

To run the application, use the following command:

```
python server.py
```

This will start the CherryPy web server, and you can interact with the application through the defined endpoints.

### Requirements

The minimum supported Python version is 3.6.

- Azure Cognitive Services for speech and text processing.
- CherryPy for the web server.
- Python's standard libraries including asyncio, sqlite3, and threading.

![divider][divider]

## Configuration

Ensure that your Azure credentials and other configurations are correctly set in a `.env` file in the root directory.
Please refer to the `env.example` file for the required environment variables.

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