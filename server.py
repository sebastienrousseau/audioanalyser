import cherrypy
import glob
import os
import io
import sys
import threading
import asyncio

# Import your custom functions
from azure_speech_to_text import run_speech_to_text_process
from azure_text_analysis import run_text_analysis_process

class SpeechTextAnalysisServer:
    @cherrypy.expose
    def index(self):
        return open('index.html')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def process_all_speech_to_text(self):
        try:
            # Redirect stdout to capture logs
            old_stdout = sys.stdout
            sys.stdout = log_capture_string = io.StringIO()

            # Run the speech-to-text process
            run_speech_to_text_process()

            # Reset stdout and get log output
            sys.stdout = old_stdout
            log_output = log_capture_string.getvalue()

            return {"result": "Processing completed", "logs": log_output}
        except Exception as e:
            cherrypy.log(f"Error during speech-to-text processing: {str(e)}")
            cherrypy.response.status = 500
            return {"error": "An error occurred during speech-to-text processing"}

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
        asyncio.run(run_text_analysis_process())

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_transcripts_list(self):
        outputs_folder = './Outputs/'  # Path to the Outputs folder
        try:
            # Find all transcript files in the Outputs folder
            list_of_files = glob.glob(os.path.join(outputs_folder, '*.txt'))
            transcripts = []
            for file_path in list_of_files:
                with open(file_path, 'r') as file:
                    content = file.read()
                    transcripts.append({"filename": os.path.basename(file_path), "content": content})
            return transcripts
        except IOError:
            cherrypy.response.status = 500
            return "Error reading transcript files."

if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config = {
        '/': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': current_dir
        }
    }
    cherrypy.quickstart(SpeechTextAnalysisServer(), '/', config)
