import azure.cognitiveservices.speech as speechsdk
import logging
import os
import json
import sqlite3
from dotenv import load_dotenv
import threading

# Load environment variables from .env file
load_dotenv()

# Set up logging format
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s app - %(message)s')
logger = logging.getLogger('AzureSpeechToText')

def validate_environment_vars():
    required_vars = ['API_KEY', 'AUDIO_EXTENSION', 'REGION', 'INPUT_FOLDER', 'OUTPUT_FOLDER']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        raise EnvironmentError("Missing required environment variables.")

def speech_to_text_long(api_key, service_region, audio_filename):
    logger.info(f"Starting speech recognition for {audio_filename}. Please wait...")
    speech_config = speechsdk.SpeechConfig(subscription=api_key, region=service_region)
    audio_input = speechsdk.audio.AudioConfig(filename=audio_filename)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

    all_results = []
    done = threading.Event()

    def handle_final_result(evt):
        logger.info(f"Recognized: {evt.result.text}")
        all_results.append(evt.result.text)

    def handle_recognition_error(evt):
        if evt.result.reason == speechsdk.ResultReason.Canceled:
            cancellation = evt.result.cancellation_details
            if cancellation.reason == speechsdk.CancellationReason.EndOfStream:
                logger.info("Recognition completed: End of audio stream reached.")
            elif cancellation.reason == speechsdk.CancellationReason.Error:
                logger.error(f"Recognition canceled due to an error: {cancellation.error_details}")
            else:
                logger.error(f"Recognition canceled: Reason={cancellation.reason}")
        else:
            logger.error(f"Recognition error: {evt}")
        done.set()

    speech_recognizer.recognized.connect(handle_final_result)
    speech_recognizer.canceled.connect(handle_recognition_error)
    speech_recognizer.session_stopped.connect(lambda evt: done.set())

    speech_recognizer.start_continuous_recognition()
    done.wait()

    if not all_results:
        logger.warning(f"No results for {audio_filename}. Check the audio file format and content.")

    return all_results

def write_to_text_file(output_filename, results):
    with open(output_filename, 'w') as file:
        for result in results:
            file.write(result + "\n")

def write_to_json_file(json_filename, results):
    with open(json_filename, 'w') as json_file:
        json.dump(results, json_file, indent=4)

def write_to_sqlite(db_filename, audio_filename, results):
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS transcriptions
                      (filename TEXT, transcription TEXT)''')
    for result in results:
        cursor.execute("INSERT INTO transcriptions (filename, transcription) VALUES (?, ?)",
                       (audio_filename, result))
    conn.commit()
    conn.close()

def process_audio_files(samples_folder, outputs_folder, api_key, service_region):
    for filename in os.listdir(samples_folder):
        if filename.endswith(os.getenv('AUDIO_EXTENSION')):
            input_path = os.path.join(samples_folder, filename)
            output_filename = os.path.splitext(filename)[0] + '.txt'
            json_filename = os.path.splitext(filename)[0] + '.json'
            db_filename = os.path.join(outputs_folder, 'transcriptions.db')

            output_path = os.path.join(outputs_folder, output_filename)
            json_path = os.path.join(outputs_folder, json_filename)

            logger.info(f"Processing {input_path}")
            results = speech_to_text_long(api_key, service_region, input_path)

            write_to_text_file(output_path, results)
            write_to_json_file(json_path, results)
            write_to_sqlite(db_filename, filename, results)

if __name__ == "__main__":
    try:
        validate_environment_vars()
        api_key = os.getenv('API_KEY')
        region = os.getenv('REGION')
        samples_folder = os.getenv('INPUT_FOLDER')
        outputs_folder = os.getenv('OUTPUT_FOLDER')

        if not os.path.exists(outputs_folder):
            os.makedirs(outputs_folder)

        process_audio_files(samples_folder, outputs_folder, api_key, region)
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
