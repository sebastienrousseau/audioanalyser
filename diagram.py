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

from diagrams import Diagram, Cluster
from diagrams.custom import Custom
from diagrams.azure.compute import FunctionApps


# Define custom components
class Transcription(Custom):
    def __init__(self, label, icon_path):
        super().__init__(label, icon_path)


class Analysis(Custom):
    def __init__(self, label, icon_path):
        super().__init__(label, icon_path)


class Reports(Custom):
    def __init__(self, label, icon_path):
        super().__init__(label, icon_path)


class Storage(Custom):
    def __init__(self, label, icon_path):
        super().__init__(label, icon_path)


class SpeechTextServer(Custom):
    def __init__(self, label, icon_path):
        super().__init__(label, icon_path)


class Translations(Custom):
    def __init__(self, label, icon_path):
        super().__init__(label, icon_path)


# Define the graph attributes
graph_attr = {
    "bgcolor": "#fafafa",
    "fontcolor": "#0171e3",
    "fontname": "Arial",
    "fontsize": "50",
    "pad": "0.618",
    "rankdir": "LR",
    "concentrate": "true",
}

# Create the diagram with the filename specifying the output format
with Diagram(
    "Audio Analyser Architecture",
    show=False,
    filename='audio-analyser-architecture',
    graph_attr=graph_attr
):
    # Define the "Source" cluster
    with Cluster("Source"):
        audio_recorder = FunctionApps(
            "Audio files",
        )  # Create an audio recorder component

    # Define the "Targets" cluster with a top-to-bottom direction
    with Cluster("Targets", direction="TB"):
        # Define the "Data Flow" cluster
        with Cluster("Data Flow"):
            analyze = Analysis(
                "Analysis",
                "./icons/analyze.png"
            )  # Create an analysis component
            recommend = Reports(
                "Reports",
                "./icons/recommend.png"
            )  # Create a reports component
            transcribe = Transcription(
                "Transcription",
                "./icons/transcribe.png"
            )  # Create a transcription component
            translate = Translations(
                "Translations",
                "./icons/translate.png"
            )  # Create a translations component

        # Define the "Data Lake" cluster
        with Cluster("Data Lake"):
            store = Storage(
                "Storage",
                "./icons/store.png"
            )  # Create a storage component

        # Define the "Event Driven" cluster
        with Cluster("Event Driven"):
            # Define the "Processing" cluster
            with Cluster("Processing"):
                # Connect data flow components
                transcribe >> analyze >> recommend >> translate

            # Define the "Serverless" cluster
            with Cluster("Serverless"):
                # Create a server component
                server = SpeechTextServer("Server", "./icons/server.png")

    # Connect the audio recorder to transcription component
    audio_recorder >> transcribe
    # Connect storage to transcription component (reversed arrow)
    store << transcribe
