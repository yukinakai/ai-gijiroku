import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from transcribe import format_timestamp, transcribe_audio, process_directory

def test_format_timestamp():
    """タイムスタンプのフォーマット機能のテスト"""
    assert format_timestamp(0) == "[00:00:00]"
    assert format_timestamp(61) == "[00:01:01]"
    assert format_timestamp(3661) == "[01:01:01]"

@pytest.fixture
def mock_whisper_result():
    """Whisperの結果をモックするフィクスチャ"""
    return {
        "segments": [
            {"start": 0.0, "text": "こんにちは"},
            {"start": 2.5, "text": "テストです"},
            {"start": 5.0, "text": "さようなら"}
        ]
    }

@patch("whisper.load_model")
def test_transcribe_audio(mock_load_model, tmp_path, mock_whisper_result):
    """音声ファイルの文字起こし機能のテスト"""
    # モックの設定
    mock_model = MagicMock()
    mock_model.transcribe.return_value = mock_whisper_result
    mock_load_model.return_value = mock_model
    
    # テスト用の入力ファイルと出力ディレクトリを作成
    input_file = "test.wav"
    output_dir = tmp_path / "output"
    
    # 関数を実行
    output_path = transcribe_audio(input_file, str(output_dir))
    expected_output = output_dir / "test.txt"
    
    # アサーション
    assert Path(output_path) == expected_output
    assert expected_output.exists()
    
    # 出力ファイルの内容を確認
    content = expected_output.read_text(encoding="utf-8").splitlines()
    assert content == [
        "[00:00:00] こんにちは",
        "[00:00:02] テストです",
        "[00:00:05] さようなら"
    ]

@patch("transcribe.transcribe_audio")
def test_process_directory(mock_transcribe_audio, tmp_path):
    """ディレクトリ処理機能のテスト"""
    # テスト用のディレクトリ構造を作成
    input_dir = tmp_path / "recordings"
    input_dir.mkdir()
    
    # テスト用の音声ファイルを作成（実際の内容は不要）
    (input_dir / "test1.wav").touch()
    (input_dir / "test2.mp3").touch()
    (input_dir / "ignore.txt").touch()
    
    # モックの設定
    mock_transcribe_audio.side_effect = lambda f, o: str(Path(o) / Path(f).stem) + ".txt"
    
    # 関数を実行
    output_dir = "transcripts"
    result = process_directory(str(input_dir), output_dir)
    
    # アサーション
    assert len(result) == 2
    assert all(f.endswith(".txt") for f in result)
    assert mock_transcribe_audio.call_count == 2

def test_process_directory_empty(tmp_path):
    """空のディレクトリを処理した場合のテスト"""
    input_dir = tmp_path / "empty"
    input_dir.mkdir()
    
    result = process_directory(str(input_dir))
    assert result == []