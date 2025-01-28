import pytest
import os
from src.transcribe import (
    format_timestamp,
    transcribe_audio,
    process_directory,
    process_single_file,
    calculate_audio_cost
)
from unittest.mock import patch, MagicMock

def test_format_timestamp():
    """タイムスタンプのフォーマット機能をテストする"""
    assert format_timestamp(0) == "[00:00:00]"
    assert format_timestamp(61) == "[00:01:01]"
    assert format_timestamp(3661) == "[01:01:01]"

def test_calculate_audio_cost():
    """音声コスト計算機能をテストする"""
    # 1分の音声（$0.006）
    assert calculate_audio_cost(60) == 0.006
    # 30秒の音声（$0.003）
    assert calculate_audio_cost(30) == 0.003
    # 2分の音声（$0.012）
    assert calculate_audio_cost(120) == 0.012

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
    mock_response.duration = 60  # 1分の音声を想定
    
    mock_client.audio.transcriptions.create.return_value = mock_response
    
    # テスト用の音声ファイル
    test_audio = "test_audio.wav"
    
    if os.path.exists(test_audio):
        transcription, prompt_info = transcribe_audio(test_audio)
        # 文字起こしテキストの確認
        assert isinstance(transcription, str)
        assert len(transcription) > 0
        assert transcription.startswith("[")
        assert "]" in transcription
        
        # プロンプト情報の確認
        assert isinstance(prompt_info, dict)
        assert prompt_info["model"] == "whisper-1"
        assert prompt_info["language"] == "ja"
        assert prompt_info["duration_seconds"] == 60
        assert prompt_info["cost_usd"] == 0.006
        assert "timestamp" in prompt_info

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
    mock_response.duration = 60
    
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
        output_files = list(output_dir.glob("*.txt"))
        assert len(output_files) > 0
        
        # 出力ファイルの内容を確認
        with open(output_files[0], "r", encoding="utf-8") as f:
            content = f.read()
            assert "[OpenAI API 使用情報]" in content
            assert "モデル: whisper-1" in content
            assert "推定コスト: $" in content

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
    mock_response.duration = 60
    
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
            assert "[OpenAI API 使用情報]" in content
            assert "モデル: whisper-1" in content
            assert "言語設定: ja" in content
            assert "音声の長さ:" in content
            assert "推定コスト: $" in content
            assert "処理日時:" in content

def test_process_single_file_invalid_file():
    """存在しないファイルを指定した場合のエラーテスト"""
    with pytest.raises(FileNotFoundError):
        process_single_file("non_existent_file.wav")

def test_process_single_file_invalid_format():
    """サポートされていない形式のファイルを指定した場合のエラーテスト"""
    with pytest.raises(ValueError):
        process_single_file("test.txt")