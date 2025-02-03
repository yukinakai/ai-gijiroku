import pytest
from unittest.mock import patch, MagicMock
from src.main import main

def test_main_with_default_arguments():
    """デフォルト引数でのmain関数の動作テスト"""
    with patch('argparse.ArgumentParser.parse_args') as mock_args, \
         patch('src.workflow.recording_workflow.AudioRecorder') as mock_recorder, \
         patch('builtins.input') as mock_input, \
         patch('src.workflow.recording_workflow.process_single_file') as mock_process, \
         patch('src.workflow.recording_workflow.process_transcript') as mock_process_transcript:
        # モックの設定
        mock_args.return_value = MagicMock(
            filename=None,
            rate=48000,
            no_transcribe=False
        )
        
        # AudioRecorderのモック設定
        mock_recorder_instance = mock_recorder.return_value
        mock_recorder_instance.list_devices.return_value = [
            {'name': 'Test Device', 'index': 0}
        ]
        mock_recorder_instance.record.return_value = 'test.wav'
        
        # input関数のモック設定
        mock_input.return_value = "0"  # デバイスID 0を選択
        
        # 文字起こし処理のモック設定
        mock_process.return_value = 'test_transcript.txt'
        mock_process_transcript.return_value = None
        
        # テスト実行
        result = main()

        # アサーション
        assert result == 0
        mock_recorder_instance.record.assert_called_once()
        mock_process.assert_called_once_with('test.wav', extract_todos=False)
        mock_process_transcript.assert_called_once_with('test_transcript.txt')

def test_main_with_custom_arguments():
    """カスタム引数でのmain関数の動作テスト"""
    with patch('argparse.ArgumentParser.parse_args') as mock_args, \
         patch('src.workflow.recording_workflow.AudioRecorder') as mock_recorder, \
         patch('builtins.input') as mock_input:
        # モックの設定
        mock_args.return_value = MagicMock(
            filename="test_recording",
            rate=44100,
            no_transcribe=True
        )
        
        # AudioRecorderのモック設定
        mock_recorder_instance = mock_recorder.return_value
        mock_recorder_instance.list_devices.return_value = [
            {'name': 'Test Device', 'index': 0}
        ]
        mock_recorder_instance.record.return_value = 'test_recording.wav'
        
        # input関数のモック設定
        mock_input.return_value = "0"  # デバイスID 0を選択
        
        # テスト実行
        result = main()

        # アサーション
        assert result == 0
        mock_recorder_instance.record.assert_called_once()

def test_main_workflow_failure():
    """ワークフロー実行失敗時のテスト"""
    with patch('argparse.ArgumentParser.parse_args') as mock_args, \
         patch('src.workflow.recording_workflow.AudioRecorder') as mock_recorder, \
         patch('builtins.input') as mock_input:
        # モックの設定
        mock_args.return_value = MagicMock(
            filename=None,
            rate=48000,
            no_transcribe=False
        )
        
        # AudioRecorderのモック設定
        mock_recorder_instance = mock_recorder.return_value
        mock_recorder_instance.list_devices.return_value = [
            {'name': 'Test Device', 'index': 0}
        ]
        mock_recorder_instance.record.return_value = None  # 録音失敗をシミュレート
        
        # input関数のモック設定
        mock_input.return_value = "0"  # デバイスID 0を選択
        
        # テスト実行
        result = main()

        # アサーション
        assert result == 1
        mock_recorder_instance.record.assert_called_once()