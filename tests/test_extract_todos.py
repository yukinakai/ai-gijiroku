import pytest
from src.functions.extract_todos import (
    split_text_into_chunks,
    extract_todos_from_chunk,
    format_todos,
    append_todos_to_file
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

def test_format_todos():
    test_todos = [
        {
            'task': 'レポート作成',
            'assignee': '山田',
            'deadline': '来週'
        },
        {
            'task': 'データ集計',
            'assignee': '鈴木',
            'deadline': ''
        }
    ]
    
    formatted = format_todos(test_todos)
    
    assert isinstance(formatted, str)
    assert '[抽出されたTODO]' in formatted
    assert 'レポート作成' in formatted
    assert 'データ集計' in formatted

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