import pytest
from unittest.mock import patch, mock_open
from src.functions.extract_todos import (
    split_text_into_chunks,
    extract_todos_from_chunk,
    format_todos,
    append_todos_to_file,
    process_transcript
)
import tempfile
import os

def test_split_text_into_chunks():
    # テストデータ作成
    test_text = "1行目\n" * 1000
    max_tokens = 100
    
    # チャンク分割実行
    chunks = split_text_into_chunks(test_text, max_tokens)
    
    # 検証
    assert len(chunks) > 1
    for chunk in chunks:
        # 簡易的なトークン数チェック（日本語2文字≒1トークン）
        assert len(chunk) <= max_tokens * 2

def test_split_text_into_chunks_long_line():
    # 最大トークン数を超える長い行を含むテキスト
    long_line = "あ" * 1000
    test_text = f"通常の行1\n{long_line}\n通常の行2"
    max_tokens = 100
    
    chunks = split_text_into_chunks(test_text, max_tokens)
    
    # 検証
    assert len(chunks) > 2  # 少なくとも3つのチャンクになるはず
    # 長い行が適切に分割されていることを確認
    found_long_line_chunks = False
    for chunk in chunks:
        assert len(chunk) <= max_tokens * 2
        if "あ" * (max_tokens * 2) in chunk:
            found_long_line_chunks = True
    assert found_long_line_chunks

def test_extract_todos_from_chunk():
    test_chunk = """
    山田さん: 来週までにレポートを完成させる必要があります。
    鈴木さん: 承知しました。データの集計は私が担当します。
    """
    
    todos = extract_todos_from_chunk(test_chunk)
    
    assert isinstance(todos, list)
    assert len(todos) > 0
    for todo in todos:
        assert isinstance(todo, dict)
        assert 'task' in todo
        assert 'priority' in todo
        assert 'category' in todo
        assert todo['priority'] in ['high', 'medium', 'low']
        assert todo['category'] in ['development', 'analysis', 'business', 'other']

@patch('openai.chat.completions.create')
def test_extract_todos_from_chunk_invalid_format(mock_create):
    # OpenAIのレスポンスが不正なフォーマットの場合のテスト
    class MockResponse:
        class Choice:
            def __init__(self, content):
                self.message = type('Message', (), {'content': content})
        def __init__(self, content):
            self.choices = [self.Choice(content)]

    mock_create.return_value = MockResponse("不正なフォーマットの応答")
    
    todos = extract_todos_from_chunk("テストテキスト")
    assert len(todos) == 0

def test_format_todos():
    test_todos = [
        {
            'task': 'レポート作成',
            'assignee': '山田',
            'deadline': '来週',
            'priority': 'high',
            'category': 'analysis'
        },
        {
            'task': 'データ集計',
            'assignee': '鈴木',
            'deadline': None,
            'priority': 'medium',
            'category': 'development'
        }
    ]
    
    formatted = format_todos(test_todos)
    
    assert isinstance(formatted, str)
    assert '[抽出されたTODO]' in formatted
    assert 'レポート作成' in formatted
    assert 'データ集計' in formatted
    assert '@山田' in formatted
    assert '@鈴木' in formatted
    assert '来週' in formatted

def test_append_todos_to_file():
    # 一時ファイル作成
    with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
        f.write('元のテキスト\n')
        temp_path = f.name
    
    try:
        todos_text = '[抽出されたTODO]\n1. テストTODO'
        append_todos_to_file(temp_path, todos_text)
        
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert '元のテキスト' in content
            assert todos_text in content
    finally:
        os.unlink(temp_path)

def test_split_text_into_chunks_empty():
    assert split_text_into_chunks("") == []

def test_split_text_into_chunks_single():
    text = "短いテキスト"
    chunks = split_text_into_chunks(text, 1000)
    assert len(chunks) == 1
    assert chunks[0] == text

def test_format_todos_empty():
    assert '[抽出されたTODO]' in format_todos([])

def test_format_todos_missing_fields():
    todos = [{'task': 'タスク'}]  # assigneeとdeadlineが欠落
    formatted = format_todos(todos)
    assert 'タスク' in formatted
    assert '担当' not in formatted
    assert '期限' not in formatted

@patch('builtins.open', new_callable=mock_open, read_data="テスト議事録\n複数行あるテキスト")
@patch('src.functions.extract_todos.extract_todos_from_chunk')
def test_process_transcript(mock_extract, mock_file):
    # extract_todos_from_chunkの戻り値を設定
    mock_extract.return_value = [
        {
            'task': 'テストタスク',
            'assignee': 'テスト太郎',
            'deadline': '2025/02/10',
            'priority': 'high',
            'category': 'development'
        }
    ]
    
    # process_transcriptを実行
    process_transcript('dummy.txt')
    
    # ファイルが読み込まれたことを確認
    mock_file.assert_any_call('dummy.txt', 'r', encoding='utf-8')
    
    # ファイルに書き込みが行われたことを確認
    mock_file().write.assert_called()
    
    # extract_todos_from_chunkが呼び出されたことを確認
    assert mock_extract.called

@patch('builtins.open')
def test_process_transcript_file_not_found(mock_open):
    # ファイルが存在しない場合のテスト
    mock_open.side_effect = FileNotFoundError()
    
    with pytest.raises(FileNotFoundError):
        process_transcript('not_exists.txt')