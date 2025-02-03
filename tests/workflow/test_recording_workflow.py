import unittest
from unittest.mock import patch, MagicMock
from src.workflow.recording_workflow import RecordingWorkflow

class TestRecordingWorkflow(unittest.TestCase):
    def setUp(self):
        self.workflow = RecordingWorkflow()

    @patch('builtins.input')
    def test_select_input_device_valid_input(self, mock_input):
        # 有効なデバイスIDを入力した場合のテスト
        with patch.object(self.workflow.recorder, 'list_devices', return_value=['device1', 'device2']):
            mock_input.return_value = "1"
            result = self.workflow.select_input_device()
            self.assertEqual(result, 1)

    @patch('builtins.input')
    def test_select_input_device_invalid_then_valid(self, mock_input):
        # 無効な入力の後に有効な入力をした場合のテスト
        with patch.object(self.workflow.recorder, 'list_devices', return_value=['device1', 'device2']):
            mock_input.side_effect = ["invalid", "3", "1"]
            result = self.workflow.select_input_device()
            self.assertEqual(result, 1)

    def test_get_filename_with_default(self):
        # デフォルトファイル名が提供された場合のテスト
        result = self.workflow.get_filename("test_file")
        self.assertEqual(result, "test_file")

    @patch('builtins.input')
    def test_get_filename_without_default(self, mock_input):
        # ユーザー入力でファイル名を取得する場合のテスト
        mock_input.return_value = "user_file"
        result = self.workflow.get_filename()
        self.assertEqual(result, "user_file")

    @patch.object(RecordingWorkflow, 'select_input_device')
    @patch.object(RecordingWorkflow, 'get_filename')
    def test_execute_successful_workflow(self, mock_get_filename, mock_select_input_device):
        # 正常なワークフローの実行テスト
        mock_select_input_device.return_value = 1
        mock_get_filename.return_value = "test_file"
        
        with patch.object(self.workflow.recorder, 'record', return_value="test_audio.wav") as mock_record:
            with patch('src.workflow.recording_workflow.process_single_file', return_value="test_transcript.txt") as mock_transcribe:
                with patch('src.workflow.recording_workflow.process_transcript') as mock_process_transcript:
                    result = self.workflow.execute()
                    
                    self.assertTrue(result)
                    mock_record.assert_called_once()
                    mock_transcribe.assert_called_once()
                    mock_process_transcript.assert_called_once()

    @patch.object(RecordingWorkflow, 'select_input_device')
    def test_execute_device_selection_cancelled(self, mock_select_input_device):
        # デバイス選択がキャンセルされた場合のテスト
        mock_select_input_device.return_value = None
        result = self.workflow.execute()
        self.assertFalse(result)

    @patch.object(RecordingWorkflow, 'select_input_device')
    @patch.object(RecordingWorkflow, 'get_filename')
    def test_execute_recording_failed(self, mock_get_filename, mock_select_input_device):
        # 録音が失敗した場合のテスト
        mock_select_input_device.return_value = 1
        mock_get_filename.return_value = "test_file"
        
        with patch.object(self.workflow.recorder, 'record', return_value=None):
            result = self.workflow.execute()
            self.assertFalse(result)

    @patch.object(RecordingWorkflow, 'select_input_device')
    @patch.object(RecordingWorkflow, 'get_filename')
    def test_execute_skip_transcribe(self, mock_get_filename, mock_select_input_device):
        # 文字起こしをスキップする場合のテスト
        mock_select_input_device.return_value = 1
        mock_get_filename.return_value = "test_file"
        
        with patch.object(self.workflow.recorder, 'record', return_value="test_audio.wav"):
            result = self.workflow.execute(skip_transcribe=True)
            self.assertTrue(result)

    @patch.object(RecordingWorkflow, 'select_input_device')
    @patch.object(RecordingWorkflow, 'get_filename')
    def test_execute_without_todo_extraction(self, mock_get_filename, mock_select_input_device):
        # TODO抽出を行わない場合のテスト
        mock_select_input_device.return_value = 1
        mock_get_filename.return_value = "test_file"
        
        with patch.object(self.workflow.recorder, 'record', return_value="test_audio.wav"):
            with patch('src.workflow.recording_workflow.process_single_file', return_value="test_transcript.txt"):
                result = self.workflow.execute(extract_todos=False)
                self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()