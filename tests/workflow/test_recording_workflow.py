import unittest
from unittest.mock import patch, MagicMock
from src.workflow.recording_workflow import RecordingWorkflow

class TestRecordingWorkflow(unittest.TestCase):
    def setUp(self):
        self.workflow = RecordingWorkflow()
        self.mock_devices = [
            {
                'name': 'Device 1',
                'max_input_channels': 2,
                'max_output_channels': 2,
                'default_samplerate': 48000
            },
            {
                'name': 'BlackHole 2ch',
                'max_input_channels': 2,
                'max_output_channels': 2,
                'default_samplerate': 48000
            }
        ]

    def test_select_input_device_valid(self):
        with patch('builtins.input', return_value='0'), \
             patch.object(self.workflow.recorder, 'list_devices', return_value=self.mock_devices):
            device_id = self.workflow.select_input_device()
            self.assertEqual(device_id, 0)

    def test_select_input_device_invalid_then_valid(self):
        with patch('builtins.input', side_effect=['invalid', '99', '0']), \
             patch.object(self.workflow.recorder, 'list_devices', return_value=self.mock_devices):
            device_id = self.workflow.select_input_device()
            self.assertEqual(device_id, 0)

    def test_get_filename_with_default(self):
        default_filename = "テスト会議"
        filename = self.workflow.get_filename(default_filename)
        self.assertEqual(filename, default_filename)

    def test_get_filename_without_default(self):
        with patch('builtins.input', return_value="テスト会議"):
            filename = self.workflow.get_filename()
            self.assertEqual(filename, "テスト会議")

    def test_execute_successful_with_transcribe(self):
        mock_audio_path = "recordings/test_audio.wav"
        mock_transcript_path = "transcripts/test_transcript.txt"

        with patch.object(self.workflow, 'select_input_device', return_value=0), \
             patch.object(self.workflow.recorder, 'record', return_value=mock_audio_path), \
             patch('src.workflow.recording_workflow.process_single_file', return_value=mock_transcript_path):
            
            success = self.workflow.execute(filename="テスト会議", sample_rate=48000)
            self.assertTrue(success)

    def test_execute_successful_without_transcribe(self):
        mock_audio_path = "recordings/test_audio.wav"

        with patch.object(self.workflow, 'select_input_device', return_value=0), \
             patch.object(self.workflow.recorder, 'record', return_value=mock_audio_path), \
             patch('src.workflow.recording_workflow.process_single_file') as mock_process:
            
            success = self.workflow.execute(filename="テスト会議", sample_rate=48000, skip_transcribe=True)
            self.assertTrue(success)
            mock_process.assert_not_called()

    def test_execute_recording_failed(self):
        with patch.object(self.workflow, 'select_input_device', return_value=0), \
             patch.object(self.workflow.recorder, 'record', return_value=None):
            
            success = self.workflow.execute(filename="テスト会議", sample_rate=48000)
            self.assertFalse(success)

    def test_execute_transcribe_failed(self):
        mock_audio_path = "recordings/test_audio.wav"

        with patch.object(self.workflow, 'select_input_device', return_value=0), \
             patch.object(self.workflow.recorder, 'record', return_value=mock_audio_path), \
             patch('src.workflow.recording_workflow.process_single_file', side_effect=Exception("Transcribe error")):
            
            success = self.workflow.execute(filename="テスト会議", sample_rate=48000)
            self.assertFalse(success)

if __name__ == '__main__':
    unittest.main()