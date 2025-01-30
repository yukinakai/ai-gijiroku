import os
from typing import List, Dict
import openai
from dotenv import load_dotenv

load_dotenv()

def split_text_into_chunks(text: str, max_tokens: int = 4000) -> List[str]:
    """
    テキストを指定されたトークン数で分割する
    
    Args:
        text: 分割する元のテキスト
        max_tokens: 1チャンクの最大トークン数
        
    Returns:
        分割されたテキストのリスト
    """
    if not text:
        return []

    # 簡易的なトークン数の見積もり (日本語の場合、文字数の2倍程度)
    chars_per_token = 2
    max_chars = max_tokens * chars_per_token
    
    # 行単位で分割
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_length = 0
    
    for line in lines:
        line_length = len(line) + 1  # 改行文字も考慮
        
        # 現在の行が最大文字数を超える場合は、文字単位で分割
        if line_length > max_chars:
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # 長い行を文字単位で分割
            for i in range(0, len(line), max_chars):
                chunk = line[i:i + max_chars]
                chunks.append(chunk)
            continue
        
        if current_length + line_length > max_chars and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = []
            current_length = 0
        
        current_chunk.append(line)
        current_length += line_length
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks

def extract_todos_from_chunk(chunk: str) -> List[Dict[str, str]]:
    """
    テキストチャンクからTODOを抽出する
    
    Args:
        chunk: 分析対象のテキストチャンク
        
    Returns:
        抽出されたTODOのリスト
    """
    openai.api_key = os.getenv('OPENAI_API_KEY')
    
    prompt = f"""
以下の会議の書き起こしテキストから、TODOや課題、アクションアイテムを抽出してください。
重複を避け、関連するタスクはグループ化してください。

各TODOを以下の形式で1行ずつ出力してください：

[タスク内容]|||[担当者]|||[期限]|||[優先度]|||[カテゴリ]

例：
データ分析を実施|||山田|||2025/02/01|||high|||analysis
バグ修正を行う|||null|||null|||medium|||development

注意：
- 担当者や期限が不明な場合は"null"と記入
- 優先度は必ずhigh、medium、lowのいずれかを使用
- カテゴリは必ずdevelopment、analysis、business、otherのいずれかを使用
- フィールドの区切りには必ず|||を使用
- 1行に1つのTODOを記入
- 空行は入れない

書き起こしテキスト:
{chunk}
"""
    
    response = openai.chat.completions.create(
        model="gpt-4",  # 4o-miniに置き換え予定
        messages=[
            {"role": "system", "content": """あなたは会議の書き起こしからTODOを抽出する専門家です。
以下のルールを必ず守ってください：
1. 各TODOを1行で出力してください
2. フィールドは|||で区切ってください
3. 担当者や期限が不明な場合は"null"と記入してください
4. 優先度は必ずhigh、medium、lowのいずれかを使用してください
5. カテゴリは必ずdevelopment、analysis、business、otherのいずれかを使用してください
6. 重複するTODOは統合してください"""},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    
    # レスポンスをパースしてTODOリストを作成
    raw_response = response.choices[0].message.content

    todos = []
    # 行ごとに処理
    for line in raw_response.strip().split('\n'):
        line = line.strip()
        if not line or '|||' not in line:
            continue
            
        # フィールドを分割
        parts = line.split('|||')
        if len(parts) != 5:
            continue
            
        task, assignee, deadline, priority, category = [p.strip() for p in parts]
        
        # 値の正規化
        assignee = None if assignee == 'null' else assignee
        deadline = None if deadline == 'null' else deadline
        priority = priority if priority in ['high', 'medium', 'low'] else 'low'
        category = category if category in ['development', 'analysis', 'business', 'other'] else 'other'
        
        # TODOオブジェクトを作成
        todo = {
            'task': task,
            'assignee': assignee,
            'deadline': deadline,
            'priority': priority,
            'category': category
        }
        
        todos.append(todo)
        
    return todos

def format_todos(todos: List[Dict[str, str]]) -> str:
    """
    抽出されたTODOを整形する
    
    Args:
        todos: TODOのリスト
        
    Returns:
        整形されたTODO文字列
    """
    formatted = "\n\n[抽出されたTODO]\n\n"
    
    for todo in todos:
        formatted += f"[ ] {todo['task']}"
        if todo.get('assignee'):
            formatted += f" (@{todo['assignee']})"
        if todo.get('deadline'):
            formatted += f" (期限: {todo['deadline']})"
        formatted += "\n"
    
    return formatted

def append_todos_to_file(filepath: str, todos_text: str):
    """
    TODOを書き起こしファイルに追記する
    
    Args:
        filepath: 書き起こしファイルのパス
        todos_text: 追記するTODOテキスト
    """
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write("\n" + todos_text)

def process_transcript(filepath: str):
    """
    書き起こしファイルを処理してTODOを抽出・追記する
    
    Args:
        filepath: 処理する書き起こしファイルのパス
    """
    # ファイルを読み込み
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # テキストをチャンクに分割
    chunks = split_text_into_chunks(text)
    
    # 各チャンクからTODOを抽出
    all_todos = []
    for chunk in chunks:
        todos = extract_todos_from_chunk(chunk)
        all_todos.extend(todos)
    
    # TODOを整形
    formatted_todos = format_todos(all_todos)
    
    # ファイルに追記
    append_todos_to_file(filepath, formatted_todos)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python extract_todos.py <transcript_file>")
        sys.exit(1)
    
    transcript_file = sys.argv[1]
    process_transcript(transcript_file)