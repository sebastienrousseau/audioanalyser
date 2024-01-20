import unittest
from unittest.mock import patch, MagicMock, call
import asyncio
from audioanalyser.__main__ import main

class TestMainFunction(unittest.TestCase):
    @patch('audioanalyser.modules.azure_speech_to_text.azure_speech_to_text')
    def test_speech_to_text(self, mock_stt):
        args = ['--speech_to_text', 'recording_20240119_154702.wav']
        with patch('sys.argv', ['script_name'] + args):
            asyncio.run(main())

        # Expect a single filename string as the argument
        mock_stt.assert_called_with('recording_20240119_154702')

    @patch('audioanalyser.modules.analyze_text_files')
    def test_text_analysis(self, mock_ta):
        args = ['-ta', 'recording_20240119_154702.txt']
        with patch('sys.argv', ['script_name'] + args):
            asyncio.run(main())
        mock_ta.assert_called_with(args[1])
        mock_ta.reset_mock()

    # @patch('audioanalyser.modules.azure_speech_to_text.azure_speech_to_text')
    # def test_speech_to_text_argument(self, mock_speech_to_text):
    #     test_args = ['prog', '--speech_to_text']

    #     with patch('sys.argv', test_args):
    #         asyncio.run(main())

    #         # Expect that azure_speech_to_text is called with None
    #         mock_speech_to_text.assert_called_once_with([])

    # @patch('audioanalyser.modules.analyze_text_files.analyze_text_files')
    # def test_text_analysis_argument(self, mock_text_analysis):
    #     args = ""
    #     test_args = ['prog', '--text_analysis', args]

    #     with patch('sys.argv', test_args):
    #         asyncio.run(main())

    #         # Ensure that analyze_text_files is called with an empty list
    #         mock_text_analysis.assert_called_once_with([])

if __name__ == '__main__':
    unittest.main()



    # @patch('modules.azure_recommendation')
    # def test_summary_argument(self, mock_recommendation):
    #     test_args = ['prog', '--summary']
    #     with patch('sys.argv', test_args):
    #         main()
    #         mock_recommendation.assert_called_once()

    # @patch('modules.server')
    # def test_server_argument(self, mock_server):
    #     test_args = ['prog', '--server']
    #     with patch('sys.argv', test_args):
    #         main()
    #         mock_server.assert_called_once()

    # @patch('modules.audio_recorder')
    # def test_record_argument(self, mock_recorder):
    #     test_args = ['prog', '--record']
    #     with patch('sys.argv', test_args):
    #         main()
    #         mock_recorder.assert_called_once()

    # def test_no_argument_prints_help(self):
    #     with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
    #         test_args = ['prog']
    #         with patch('sys.argv', test_args):
    #             main()
    #             self.assertIn('usage:', mock_stdout.getvalue())
