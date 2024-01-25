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

import asyncio
import cherrypy
import glob
import io
import os
import signal
import sys
import threading

# Import your custom functions
from audioanalyser.modules.audio_recorder import audio_recorder
from audioanalyser.modules.azure_recommendation import (
    azure_recommendation,
)
from audioanalyser.modules.transcribe_audio_files import (
    transcribe_audio_files,
)
from audioanalyser.modules.analyze_text_files import analyze_text_files
from audioanalyser.modules.azure_translator import azure_translator


class SpeechTextAnalysisServer:
    """
    A CherryPy web server for speech-to-text and text analysis tasks.
    """

    @cherrypy.expose
    def index(self):
        """
        Default endpoint to serve the dashboard.
        """
        return open("dashboard/index.html")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def process_all_speech_to_text(self):
        """
        Endpoint to process audio files and perform speech-to-text conversion.
        """
        try:
            # Redirect stdout to capture logs
            old_stdout = sys.stdout
            sys.stdout = log_capture_string = io.StringIO()

            # Run the speech-to-text process
            transcribe_audio_files()

            # Reset stdout and get log output
            sys.stdout = old_stdout
            log_output = log_capture_string.getvalue()

            return {
                "result": "Processing completed",
                "logs": log_output,
            }
        except Exception as e:
            cherrypy.log(
                f"Error during speech-to-text processing: {str(e)}"
            )
            cherrypy.response.status = 500
            return {
                "error": "An error occurred during speech-to-text processing"
            }

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def record_audio(self):
        """
        Endpoint to record audio.
        """
        try:
            # Redirect stdout to capture logs
            sys.stdout = log_capture_string = io.StringIO()

            # Start recording and get the file path
            recorded_file_path = audio_recorder()  # Removed asyncio.run

            # Check if recording was successful
            if recorded_file_path is None:
                raise Exception("Failed to record audio.")

            # Retrieve the log output
            log_output = log_capture_string.getvalue()

            return {
                "result": "Recording completed",
                "recorded_file": recorded_file_path,
                "logs": log_output,
            }
        except Exception as e:
            cherrypy.log(f"Error during audio recording: {str(e)}")
            cherrypy.response.status = 500
            return {"error": str(e)}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def list_audio_files(self):
        """
        Endpoint to list available audio files for processing.
        """
        try:
            files_dir = "./resources/input"
            files = [
                {
                    "name": file,
                    "full_path": os.path.abspath(
                        os.path.join(files_dir, file)
                    ),
                }
                for file in os.listdir(files_dir)
                if os.path.isfile(os.path.join(files_dir, file))
                and file.endswith(".wav")
            ]
            return files
        except Exception as e:
            cherrypy.log(f"Error listing audio files: {str(e)}")
            cherrypy.response.status = 500
            return {
                "error": "An error occurred while fetching the file list"
            }

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def process_text_analysis(self):
        """
        Endpoint to trigger text analysis asynchronously.
        """
        try:
            # Run the text analysis process in a separate thread
            thread = threading.Thread(target=self.run_analysis_thread)
            thread.start()
            return {"result": "Text analysis process started"}
        except Exception as e:
            cherrypy.log(f"Error during text analysis: {str(e)}")
            cherrypy.response.status = 500
            return {"error": "An error occurred during text analysis"}

    def run_analysis_thread(self):
        """
        Worker thread for text analysis.
        """
        file_paths = "./resources/transcripts/*.txt"
        temporary_folder = "./"
        status_file_path = os.path.join(
            temporary_folder, "analysis_status.txt"
        )
        try:
            asyncio.run(analyze_text_files(file_paths))
            with open(status_file_path, "w") as file:
                file.write("Completed")
        except Exception as e:
            with open(status_file_path, "w") as file:
                file.write(f"Error: {str(e)}")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_analysis_status(self):
        """
        Endpoint to check the status of text analysis.
        """
        temporary_folder = "./"
        status_file_path = os.path.join(
            temporary_folder, "analysis_status.txt"
        )
        if os.path.exists(status_file_path):
            with open(status_file_path, "r") as file:
                status = file.read()
            return {"status": status}
        else:
            return {"status": "Processing"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_transcripts_list(self):
        """
        Endpoint to retrieve a list of transcripts.
        """
        outputs_folder = "./resources/transcripts/"
        try:
            # Find all transcript files in the Outputs folder
            list_of_files = glob.glob(
                os.path.join(outputs_folder, "*.txt")
            )
            transcripts = []
            for file_path in list_of_files:
                with open(file_path, "r") as file:
                    content = file.read()
                    transcripts.append(
                        {
                            "filename": os.path.basename(file_path),
                            "content": content,
                        }
                    )
            return transcripts
        except IOError:
            cherrypy.response.status = 500
            return {"error": "Error reading transcript files."}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_reports_list(self):
        """
        Endpoint to retrieve a list of reports.
        """
        outputs_folder = "./resources/reports/"
        try:
            # Find all report files in the Outputs folder
            list_of_files = glob.glob(
                os.path.join(outputs_folder, "*.txt")
            )
            reports = []
            for file_path in list_of_files:
                with open(file_path, "r") as file:
                    content = file.read()
                    reports.append(
                        {
                            "filename": os.path.basename(file_path),
                            "content": content,
                        }
                    )
            return reports
        except IOError:
            cherrypy.response.status = 500
            return {"error": "Error reading report files."}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_summaries_list(self):
        """
        Endpoint to retrieve a list of summaries.
        """
        outputs_folder = "./resources/recommendations/"
        try:
            # Find all report files in the Outputs folder
            list_of_files = glob.glob(
                os.path.join(outputs_folder, "*.txt")
            )
            reports = []
            for file_path in list_of_files:
                with open(file_path, "r") as file:
                    content = file.read()
                    reports.append(
                        {
                            "filename": os.path.basename(file_path),
                            "content": content,
                        }
                    )
            return reports
        except IOError:
            cherrypy.response.status = 500
            return {"error": "Error reading report files."}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_translations_list(self):
        """
        Endpoint to retrieve a list of translations.
        """
        outputs_folder = "./resources/translations/"
        try:
            # Find all report files in the Outputs folder
            list_of_files = glob.glob(
                os.path.join(outputs_folder, "*.txt")
            )
            reports = []
            for file_path in list_of_files:
                with open(file_path, "r") as file:
                    content = file.read()
                    reports.append(
                        {
                            "filename": os.path.basename(file_path),
                            "content": content,
                        }
                    )
            return reports
        except IOError:
            cherrypy.response.status = 500
            return {"error": "Error reading report files."}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def generate_recommendations(self):
        """
        Endpoint to trigger executive summary generation.
        """
        try:
            # Run the executive summary generation process in a separate thread
            thread = threading.Thread(
                target=self.run_recommendations_thread
            )
            thread.start()
            return {"result": "Process started"}
        except Exception as e:
            cherrypy.log(
                f"Error during executive summary generation: {str(e)}"
            )
            cherrypy.response.status = 500
            return {
                "error": "An error occurred during summary generation"
            }

    def run_recommendations_thread(self):
        """
        Worker thread for executive summary generation.
        """
        temporary_folder = "./"
        status_file_path = os.path.join(
            temporary_folder, "recommendations_status.txt"
        )
        try:
            asyncio.run(azure_recommendation())
            with open(status_file_path, "w") as file:
                file.write("Completed")
        except Exception as e:
            with open(status_file_path, "w") as file:
                file.write(f"Error: {str(e)}")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()  # to parse JSON body
    def process_all_translations(self):
        """
        Endpoint to trigger text translation asynchronously.
        """
        try:
            # Retrieve data from the request body
            data = cherrypy.request.json
            countryCode = data.get('countryCode')

            # Run the text translation process in a separate thread
            thread = threading.Thread(
                target=self.run_translation_thread,
                args=(countryCode,)
            )
            thread.start()

            message = "Translation process started for country code: "
            result_message = message + str(countryCode)
            return {"result": result_message}

        except Exception as e:
            cherrypy.log(f"Error during text translation: {str(e)}")
            return {"error": "An error occurred during text translation"}, 500

    def run_translation_thread(self, countryCode=None):
        """
        Worker thread for text translation.
        """
        try:
            # Assuming azure_translator is a synchronous function
            azure_translator(countryCode)
        except Exception as e:
            cherrypy.log(f"Error in translation thread: {str(e)}")


def graceful_shutdown(signum, frame):
    """
    Gracefully shutdown the server on receiving specified signal.
    """
    print("Signal received: {}. Shutting down server...".format(signum))
    cherrypy.engine.exit()


def speech_text_server():
    """
    Function to start the CherryPy server for audio analysis.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../.."))
    dashboard_dir = os.path.join(project_root, "dashboard")
    input_dir = os.path.join(project_root, "resources", "input")
    config = {
        "/": {
            "tools.sessions.on": True,
            "tools.staticdir.on": True,
            "tools.staticdir.dir": dashboard_dir,
            "tools.staticdir.index": "index.html",
        },
        "/resources/input/": {
            "tools.staticdir.on": True,
            "tools.staticdir.dir": input_dir,
        },
    }
    cherrypy.config.update({"server.socket_port": 8080})

    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, graceful_shutdown)

    cherrypy.quickstart(SpeechTextAnalysisServer(), "/", config)


if __name__ == "__main__":
    speech_text_server()
