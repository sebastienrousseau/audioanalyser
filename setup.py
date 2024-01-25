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
#
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
from setuptools import setup, find_packages

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read the contents of your README file
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    author="Sebastien Rousseau",
    author_email="sebastian.rousseau@gmail.com",
    description="""
        Audio Analyser: Transform call recordings into actionable insights
        using Microsoft Azure AI. Advanced transcription and analysis for
        insightful reports.
    """,
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="Apache Software License",
    name='audioanalyser',
    version='0.0.5',
    url='https://audioanalyser.pro',
    packages=find_packages(),
    install_requires=[
        'azure-cognitiveservices-speech>=1.34.0',
        'python-dotenv>=0.15.0',
        'requests>=2.25.1',
        'cherrypy>=18.6.0',
    ],
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)
