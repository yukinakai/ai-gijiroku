import pytest
import os
import json
import tempfile
from pathlib import Path
from src.functions.transcribe import (
    format_timestamp,
    transcribe_audio,
    process_directory,
    process_single_file,
    calculate_audio_cost,
    split_audio,
    get_audio_duration,
    CHUNK_SIZE
)
from unittest.mock import patch, MagicMock
from pydub import AudioSegment

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

def create_test_audio(duration_ms=5000, sample_rate=44100):
    """
    テスト用の音声ファイルを作成する
    
    Args:
        duration_ms (int): 音声の長さ（ミリ秒）
        sample_rate (int): サンプルレート
    
    Returns:
        str: 作成した音声ファイルのパス
    """
    # 無音の音声セグメントを作成
    audio = AudioSegment.silent(duration=duration_ms)
    
    # 一時ファイルを作成
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        audio.export(temp_file.name, format="wav")
        return temp_file.name

def test_get_audio_duration():
    """音声の長さ取得機能をテストする"""
    # 正常な長さの音声（1秒）
    normal_file = create_test_audio(duration_ms=1000)
    try:
        duration = get_audio_duration(normal_file)
        assert duration == 1.0
    finally:
        os.remove(normal_file)
    
    # 短い音声（50ミリ秒）
    short_file = create_test_audio(duration_ms=50)
    try:
        duration = get_audio_duration(short_file)
        assert duration == 0.05
    finally:
        os.remove(short_file)

def test_split_audio():
    """音声分割機能をテストする"""
    # 大きなファイルを作成（30MB相当）
    large_file = create_test_audio(duration_ms=30000)
    
    try:
        # ファイルを分割
        chunk_paths = split_audio(large_file)
        
        # チャンクが作成されたことを確認
        assert len(chunk_paths) > 0
        print(f"Created {len(chunk_paths)} chunks")
        
        # 各チャンクのサイズを確認
        for i, chunk_path in enumerate(chunk_paths):
            size = os.path.getsize(chunk_path)
            print(f"Chunk {i}: {size} bytes")
            assert os.path.exists(chunk_path)
            assert size <= CHUNK_SIZE
        
        # オリジナルファイルが分割されたことを確認
        if len(chunk_paths) == 1:
            assert chunk_paths[0] == large_file
        else:
            assert all(chunk_path != large_file for chunk_path in chunk_paths)
        
    finally:
        # テストファイルとチャンクを削除
        os.remove(large_file)
        if len(chunk_paths) > 1:
            temp_dir = os.path.dirname(chunk_paths[0])
            for chunk_path in chunk_paths:
                if chunk_path != large_file:
                    os.remove(chunk_path)
            os.rmdir(temp_dir)

@patch('src.functions.transcribe.client')
def test_transcribe_audio_with_mixed_chunks(mock_client):
    """短いチャンクと正常なチャンクが混在する音声ファイルの文字起こし機能をテストする"""
    # モックの設定
    mock_response = MagicMock()
    mock_response.model_dump_json.return_value = json.dumps({
        "segments": [{
            "start": 0,
            "text": "テストテキスト"
        }],
        "duration": 1.0
    })
    mock_client.audio.transcriptions.create.return_value = mock_response
    
    # テスト用の音声ファイルを作成（1秒）
    test_audio = create_test_audio(duration_ms=1000)
    
    try:
        # 文字起こしを実行
        transcription, prompt_info = transcribe_audio(test_audio)
        
        # 文字起こしテキストの確認
        assert isinstance(transcription, str)
        assert len(transcription) > 0
        assert "テストテキスト" in transcription
        
        # プロンプト情報の確認
        assert isinstance(prompt_info, dict)
        assert prompt_info["model"] == "whisper-1"
        assert prompt_info["language"] == "ja"
        assert prompt_info["duration_seconds"] == 1.0
        assert "timestamp" in prompt_info
        
    finally:
        # テストファイルを削除
        os.remove(test_audio)

@patch('src.functions.transcribe.client')
def test_transcribe_audio_all_chunks_too_short(mock_client):
    """全てのチャンクが短すぎる場合のエラーテスト"""
    # 短すぎる音声ファイルを作成（50ミリ秒）
    test_audio = create_test_audio(duration_ms=50)
    
    try:
        # ValueErrorが発生することを確認
        with pytest.raises(ValueError) as exc_info:
            transcribe_audio(test_audio)
        
        # エラーメッセージを確認
        assert "処理可能な音声チャンクがありません" in str(exc_info.value)
        assert "全てのチャンクが0.1秒未満です" in str(exc_info.value)
    
    finally:
        # テストファイルを削除
        os.remove(test_audio)

@patch('src.functions.transcribe.client')
def test_process_directory(mock_client, tmp_path):
    """ディレクトリ処理機能をテストする"""
    # モックの設定
    mock_response = MagicMock()
    mock_response.model_dump_json.return_value = json.dumps({
        "segments": [{
            "start": 0,
            "text": "テストテキスト"
        }],
        "duration": 60
    })
    mock_client.audio.transcriptions.create.return_value = mock_response
    
    # テスト用のディレクトリ構造を作成
    input_dir = tmp_path / "recordings"
    output_dir = tmp_path / "transcripts"
    input_dir.mkdir()
    
    # テスト用の音声ファイルを作成（正常な長さ）
    test_audio = create_test_audio(duration_ms=1000)
    test_audio_path = input_dir / "test.wav"
    import shutil
    shutil.copy(test_audio, test_audio_path)
    
    try:
        # 処理を実行
        with patch('src.functions.transcribe.process_single_file') as mock_process_single_file:
            mock_process_single_file.return_value = output_dir / "test.txt"
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
            assert "テストテキスト" in content
    
    finally:
        # テストファイルを削除
        os.remove(test_audio)

@patch('src.functions.transcribe.client')
def test_process_single_file(mock_client, tmp_path):
    """単一ファイル処理機能をテストする"""
    # モックの設定
    mock_response = MagicMock()
    mock_response.model_dump_json.return_value = json.dumps({
        "segments": [{
            "start": 0,
            "text": "テストテキスト"
        }],
        "duration": 60
    })
    mock_client.audio.transcriptions.create.return_value = mock_response
    
    # テスト用のディレクトリ構造を作成
    output_dir = tmp_path / "transcripts"
    
    # テスト用の音声ファイルを作成（正常な長さ）
    test_audio = create_test_audio(duration_ms=1000)
    
    try:
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
    
    finally:
        # テストファイルを削除
        os.remove(test_audio)

def test_process_single_file_invalid_file():
    """存在しないファイルを指定した場合のエラーテスト"""
    with pytest.raises(FileNotFoundError):
        process_single_file("non_existent_file.wav")

def test_process_single_file_invalid_format():
    """サポートされていない形式のファイルを指定した場合のエラーテスト"""
    with pytest.raises(ValueError):
        process_single_file("test.txt")