import pytest
from pathlib import Path
import os
from transcribe import format_timestamp, transcribe_audio, process_directory, process_single_file
from unittest.mock import patch, MagicMock

def test_format_timestamp():
    """タイムスタンプのフォーマット機能をテストする"""
    assert format_timestamp(0) == "[00:00:00]"
    assert format_timestamp(61) == "[00:01:01]"
    assert format_timestamp(3661) == "[01:01:01]"

@patch('openai.OpenAI')
def test_transcribe_audio(mock_openai):
    """音声ファイルの文字起こし機能をテストする"""
    # モックの設定
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_segment = MagicMock()
    mock_segment.start = 0
    mock_segment.text = "テストテキスト"
    mock_response.segments = [mock_segment]
    
    mock_client.audio.transcriptions.create.return_value = mock_response
    
    # テスト用の音声ファイル
    test_audio = "test_audio.wav"
    
    if os.path.exists(test_audio):
        result = transcribe_audio(test_audio)
        assert isinstance(result, str)
        assert len(result) > 0
        assert result.startswith("[")
        assert "]" in result

@patch('openai.OpenAI')
def test_process_directory(mock_openai, tmp_path):
    """ディレクトリ処理機能をテストする"""
    # モックの設定
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_segment = MagicMock()
    mock_segment.start = 0
    mock_segment.text = "テストテキスト"
    mock_response.segments = [mock_segment]
    
    mock_client.audio.transcriptions.create.return_value = mock_response
    
    # テスト用のディレクトリ構造を作成
    input_dir = tmp_path / "recordings"
    output_dir = tmp_path / "transcripts"
    input_dir.mkdir()
    
    # テスト用の音声ファイル
    test_audio = "test_audio.wav"
    
    if os.path.exists(test_audio):
        # テスト用音声ファイルをコピー
        import shutil
        shutil.copy(test_audio, input_dir / "test.wav")
        
        # 処理を実行
        process_directory(str(input_dir), str(output_dir))
        
        # 出力を確認
        assert output_dir.exists()
        assert len(list(output_dir.glob("*.txt"))) > 0

@patch('openai.OpenAI')
def test_process_single_file(mock_openai, tmp_path):
    """単一ファイル処理機能をテストする"""
    # モックの設定
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_segment = MagicMock()
    mock_segment.start = 0
    mock_segment.text = "テストテキスト"
    mock_response.segments = [mock_segment]
    
    mock_client.audio.transcriptions.create.return_value = mock_response
    
    # テスト用のディレクトリ構造を作成
    output_dir = tmp_path / "transcripts"
    
    # テスト用の音声ファイル
    test_audio = "test_audio.wav"
    
    if os.path.exists(test_audio):
        # 処理を実行
        output_file = process_single_file(test_audio, str(output_dir))
        
        # 出力を確認
        assert output_dir.exists()
        assert output_file.exists()
        assert output_file.suffix == ".txt"
        
        # ファイル内容の確認
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert content.startswith("[")
            assert "テストテキスト" in content

def test_process_single_file_invalid_file():
    """存在しないファイルを指定した場合のエラーテスト"""
    with pytest.raises(FileNotFoundError):
        process_single_file("non_existent_file.wav")

def test_process_single_file_invalid_format():
    """サポートされていない形式のファイルを指定した場合のエラーテスト"""
    with pytest.raises(ValueError):
        process_single_file("test.txt")