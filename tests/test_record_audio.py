import unittest
from unittest.mock import patch, MagicMock
from src.record_audio import main

class TestRecordAudio(unittest.TestCase):
    def test_main_function_successful(self):
        """メイン関数が正常に実行される場合のテスト"""
        mock_args = MagicMock(
            filename="テスト会議",
            rate=48000,
            no_transcribe=False
        )
        
        with patch('argparse.ArgumentParser.parse_args', return_value=mock_args), \
             patch('src.workflow.recording_workflow.RecordingWorkflow') as mock_workflow_class:
            
            # ワークフローのモックを設定
            mock_workflow = MagicMock()
            mock_workflow.execute.return_value = True
            mock_workflow_class.return_value = mock_workflow
            
            # メイン関数を実行
            exit_code = main()
            
            # アサーション
            self.assertEqual(exit_code, 0)
            mock_workflow.execute.assert_called_once_with(
                filename="テスト会議",
                sample_rate=48000,
                skip_transcribe=False
            )

    def test_main_function_workflow_failed(self):
        """ワークフローが失敗した場合のテスト"""
        mock_args = MagicMock(
            filename="テスト会議",
            rate=48000,
            no_transcribe=False
        )
        
        with patch('argparse.ArgumentParser.parse_args', return_value=mock_args), \
             patch('src.workflow.recording_workflow.RecordingWorkflow') as mock_workflow_class:
            
            # ワークフローのモックを設定（失敗を模擬）
            mock_workflow = MagicMock()
            mock_workflow.execute.return_value = False
            mock_workflow_class.return_value = mock_workflow
            
            # メイン関数を実行
            exit_code = main()
            
            # アサーション
            self.assertEqual(exit_code, 1)
            mock_workflow.execute.assert_called_once_with(
                filename="テスト会議",
                sample_rate=48000,
                skip_transcribe=False
            )

if __name__ == '__main__':
    unittest.main()