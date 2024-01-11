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
import sys
import threading

# Import your custom functions
from audioanalyser.modules.audio_recorder import audio_recorder
from audioanalyser.modules.azure_recommendation import azure_recommendation
from audioanalyser.modules.azure_speech_to_text import azure_speech_to_text
from audioanalyser.modules.azure_text_analysis import azure_text_analysis


class SpeechTextAnalysisServer:
    @cherrypy.expose
    def index(self):
        return open('dashboard/index.html')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def process_all_speech_to_text(self):
        try:
            # Redirect stdout to capture logs
            old_stdout = sys.stdout
            sys.stdout = log_capture_string = io.StringIO()

            # Run the speech-to-text process
            azure_speech_to_text()

            # Reset stdout and get log output
            sys.stdout = old_stdout
            log_output = log_capture_string.getvalue()

            return {"result": "Processing completed", "logs": log_output}
        except Exception as e:
            cherrypy.log(f"Error during speech-to-text processing: {str(e)}")
            cherrypy.response.status = 500
            return {
                "error": "An error occurred during speech-to-text processing"
            }

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def record_audio(self):
        try:
            # Redirect stdout to capture logs
            sys.stdout = log_capture_string = io.StringIO()

            # Start recording and get the file path
            recorded_file_path = audio_recorder()

            # Retrieve the log output
            log_output = log_capture_string.getvalue()

            return {
                "result": "Recording completed",
                "recorded_file": recorded_file_path,
                "logs": log_output
            }
        except Exception as e:
            cherrypy.log(f"Error during audio recording: {str(e)}")
            cherrypy.response.status = 500
            return {
                "error": "An error occurred during audio recording"
            }

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def list_audio_files(self):
        try:
            files_dir = './resources/input'
            files = [
                {
                    'name': file,
                    'full_path': os.path.abspath(os.path.join(files_dir, file))
                } for file in os.listdir(files_dir)
                if os.path.isfile(os.path.join(
                    files_dir, file)
                ) and file.endswith('.wav')
            ]
            return files
        except Exception as e:
            cherrypy.log(f"Error listing audio files: {str(e)}")
            cherrypy.response.status = 500
            return {"error": "An error occurred while fetching the file list"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def process_text_analysis(self):
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
        temporary_folder = './'
        status_file_path = os.path.join(
            temporary_folder,
            'analysis_status.txt'
        )
        try:
            asyncio.run(azure_text_analysis())
            with open(status_file_path, 'w') as file:
                file.write('Completed')
        except Exception as e:
            with open(status_file_path, 'w') as file:
                file.write(f'Error: {str(e)}')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_analysis_status(self):
        temporary_folder = './'
        status_file_path = os.path.join(
            temporary_folder,
            'analysis_status.txt'
        )
        if os.path.exists(status_file_path):
            with open(status_file_path, 'r') as file:
                status = file.read()
            return {"status": status}
        else:
            return {"status": "Processing"}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_transcripts_list(self):
        outputs_folder = './resources/transcripts/'
        try:
            # Find all transcript files in the Outputs folder
            list_of_files = glob.glob(os.path.join(outputs_folder, '*.txt'))
            transcripts = []
            for file_path in list_of_files:
                with open(file_path, 'r') as file:
                    content = file.read()
                    transcripts.append(
                        {
                            "filename": os.path.basename(file_path),
                            "content": content
                        }
                    )
            return transcripts
        except IOError:
            cherrypy.response.status = 500
            return {"error": "Error reading transcript files."}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_reports_list(self):
        outputs_folder = './resources/reports/'
        try:
            # Find all report files in the Outputs folder
            list_of_files = glob.glob(os.path.join(outputs_folder, '*.txt'))
            reports = []
            for file_path in list_of_files:
                with open(file_path, 'r') as file:
                    content = file.read()
                    reports.append(
                        {
                            "filename": os.path.basename(file_path),
                            "content": content
                        }
                    )
            return reports
        except IOError:
            cherrypy.response.status = 500
            return {"error": "Error reading report files."}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_summaries_list(self):
        outputs_folder = './resources/recommendations/'
        try:
            # Find all report files in the Outputs folder
            list_of_files = glob.glob(os.path.join(outputs_folder, '*.txt'))
            reports = []
            for file_path in list_of_files:
                with open(file_path, 'r') as file:
                    content = file.read()
                    reports.append(
                        {
                            "filename": os.path.basename(file_path),
                            "content": content
                        }
                    )
            return reports
        except IOError:
            cherrypy.response.status = 500
            return {"error": "Error reading report files."}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def generate_recommendations(self):

        try:
            # Run the executive summary generation process in a separate thread
            thread = threading.Thread(target=self.run_recommendations_thread)
            thread.start()
            return {"result": "Process started"}
        except Exception as e:
            cherrypy.log(
                f"Error during executive summary generation: {str(e)}"
                )
            cherrypy.response.status = 500
            return {"error": "An error occurred during summary generation"}

    def run_recommendations_thread(self):
        temporary_folder = './'
        status_file_path = os.path.join(
            temporary_folder,
            'recommendations_status.txt'
        )
        try:
            asyncio.run(azure_recommendation())
            with open(status_file_path, 'w') as file:
                file.write('Completed')
        except Exception as e:
            with open(status_file_path, 'w') as file:
                file.write(f'Error: {str(e)}')


def audio_analyser_server():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # print('Current directory: ' + current_dir)

    project_root = os.path.abspath(os.path.join(current_dir, '../..'))
    # print('Project root: ' + project_root)

    dashboard_dir = os.path.join(project_root, 'dashboard')
    # print('Docs directory: ' + dashboard_dir)

    input_dir = os.path.join(project_root, 'resources', 'input')
    print('Input directory: ' + input_dir)

    config = {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.on': True,
            'tools.staticdir.dir': dashboard_dir,
            'tools.staticdir.index': 'index.html',
        },
        '/resources/input/': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': input_dir
        }
    }
    cherrypy.config.update({'server.socket_port': 8080})
    cherrypy.quickstart(SpeechTextAnalysisServer(), '/', config)


if __name__ == '__main__':
    audio_analyser_server()
