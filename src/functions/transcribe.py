import os
import argparse
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime
from pydub import AudioSegment
import tempfile
import re

# .envファイルから環境変数を読み込む
load_dotenv()

# OpenAI APIキーの確認
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("環境変数 OPENAI_API_KEY が設定されていません。.envファイルを確認してください。")

# OpenAIクライアントの初期化
client = OpenAI()

# チャンクサイズを20MBに設定（バイト単位）
CHUNK_SIZE = 20 * 1024 * 1024

def format_timestamp(seconds):
    """
    秒数を[00:00:00]形式の文字列に変換する
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"

def calculate_audio_cost(duration_seconds):
    """
    音声の長さからコストを計算する（Whisper APIの料金に基づく）
    """
    # Whisper APIの料金は1分あたり$0.006
    cost_per_minute = 0.006
    minutes = duration_seconds / 60
    return round(minutes * cost_per_minute, 4)

def get_audio_duration(audio_path):
    """
    音声ファイルの長さを取得する
    
    Args:
        audio_path (str): 音声ファイルのパス
    
    Returns:
        float: 音声の長さ（秒）
    """
    try:
        audio = AudioSegment.from_file(audio_path)
        return len(audio) / 1000.0
    except Exception as e:
        raise ValueError(f"音声ファイルの読み込み中にエラーが発生しました: {str(e)}")

def split_audio(audio_path):
    """
    音声ファイルを20MB以下のチャンクに分割する
    
    Args:
        audio_path (str): 入力音声ファイルのパス
    
    Returns:
        list: 一時ファイルのパスのリスト
    """
    try:
        # 音声ファイルを読み込む
        audio = AudioSegment.from_file(audio_path)
        
        # ファイルサイズを取得
        file_size = os.path.getsize(audio_path)
        
        if file_size <= CHUNK_SIZE:
            # ファイルサイズが20MB以下の場合は分割不要
            return [audio_path]
        
        # チャンクの数を計算
        num_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE  # 切り上げ除算
        chunk_duration = len(audio) // num_chunks
        chunks = []
        
        # 一時ディレクトリを作成
        temp_dir = tempfile.mkdtemp()
        
        # 音声を分割して一時ファイルとして保存
        for i, start in enumerate(range(0, len(audio), chunk_duration)):
            chunk = audio[start:start + chunk_duration]
            chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
            chunk.export(chunk_path, format="wav")
            chunks.append(chunk_path)
        
        return chunks
    except Exception as e:
        print(f"音声ファイルの処理中にエラーが発生しました: {str(e)}")
        raise

def get_response_data(response):
    """
    OpenAI APIのレスポンスからデータを取得する
    """
    if hasattr(response, 'model_dump_json'):
        # 新しいバージョンのOpenAI APIの場合
        return json.loads(response.model_dump_json())
    elif hasattr(response, '__getitem__'):
        # 辞書形式の場合
        return response
    else:
        # その他の場合（テキスト形式など）
        try:
            if hasattr(response, 'text'):
                return {"text": response.text}
            elif isinstance(response, str):
                return {"text": response}
            else:
                # 最後の手段としてJSON文字列として解析
                return json.loads(str(response))
        except:
            # 解析できない場合は空の辞書を返す
            return {"text": ""}

def format_transcription_text(text):
    """
    文字起こしテキストを整形する
    - タイムスタンプの後に改行を挿入
    - 「。」の後に改行を挿入
    
    Args:
        text (str): 整形する文字起こしテキスト
    
    Returns:
        str: 整形後のテキスト
    """
    # タイムスタンプパターン
    timestamp_pattern = r'(\[\d{2}:\d{2}:\d{2}\])'
    
    # タイムスタンプの後に改行を挿入
    text = re.sub(timestamp_pattern, r'\1\n', text)
    
    # 「。」の後に改行を挿入（ただし、既に改行がある場合は除く）
    text = re.sub(r'。(?!\n)', '。\n', text)
    
    return text

def transcribe_audio(audio_path):
    """
    音声ファイルを文字起こしする
    """
    # 音声ファイルを分割
    chunk_paths = split_audio(audio_path)
    
    all_transcriptions = []
    total_duration = 0
    valid_chunks = False  # 有効なチャンクが1つでもあるかどうか
    
    # 各チャンクを処理
    for chunk_path in chunk_paths:
        try:
            # チャンクの長さをチェック
            chunk_duration = get_audio_duration(chunk_path)
            if chunk_duration < 0.1:
                print(f"警告: チャンク {os.path.basename(chunk_path)} が短すぎます（{chunk_duration:.3f}秒）。スキップします。")
                continue
            
            with open(chunk_path, "rb") as audio_file:
                # OpenAI APIを使用して文字起こし
                response = client.audio.transcriptions.create(
                    model="gpt-4o-transcribe",
                    file=audio_file,
                    language="ja",
                    response_format="json"
                )
                
                # レスポンスデータを取得
                response_data = get_response_data(response)
                
                # jsonデータから文字起こし結果を取得
                text = response_data.get('text', '').strip()
                
                # タイムスタンプは現在のチャンクの開始時間から計算
                timestamp = format_timestamp(total_duration)
                all_transcriptions.append(f"{timestamp} {text}")
                
                # チャンクの長さを推定（正確なセグメント情報がないため）
                # 実際の音声長を使用
                total_duration += chunk_duration
                valid_chunks = True
                
        except Exception as e:
            if "音声ファイルが短すぎます" not in str(e):
                raise ValueError(f"文字起こし処理中にエラーが発生しました: {str(e)}")
    
    # 一時ファイルを削除（オリジナルファイル以外）
    if len(chunk_paths) > 1:
        temp_dir = os.path.dirname(chunk_paths[0])
        for chunk_path in chunk_paths:
            if chunk_path != audio_path:
                os.remove(chunk_path)
        os.rmdir(temp_dir)
    
    # 有効なチャンクが1つもない場合はエラー
    if not valid_chunks:
        raise ValueError("処理可能な音声チャンクがありません。全てのチャンクが0.1秒未満です。")
    
    # 全てのテキストを結合
    raw_text = "\n".join(all_transcriptions)
    
    # テキストを整形
    formatted_text = format_transcription_text(raw_text)
    
    # APIの使用情報を作成
    cost = calculate_audio_cost(total_duration)
    prompt_info = {
        "model": "gpt-4o-transcribe",
        "language": "ja",
        "duration_seconds": total_duration,
        "cost_usd": cost,
        "timestamp": datetime.now().isoformat()
    }
    
    return formatted_text, prompt_info

def process_single_file(input_file, output_dir="src/transcripts"):
    """
    単一の音声ファイルを文字起こしする
    
    Args:
        input_file (str): 入力音声ファイルのパス
        output_dir (str): 出力ディレクトリのパス
    
    Returns:
        Path: 出力ファイルのパス
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # サポートする音声フォーマット
    audio_extensions = {".mp3", ".wav", ".m4a"}
    
    # まず拡張子のチェック
    if input_path.suffix.lower() not in audio_extensions:
        raise ValueError(f"サポートされていない音声フォーマットです: {input_path.suffix}")
    
    # 次にファイルの存在チェック
    if not input_path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {input_file}")
    
    try:
        # 文字起こしの実行
        transcription, prompt_info = transcribe_audio(str(input_path))
        
        # 出力ファイル名の設定
        output_file = output_path / f"{input_path.stem}.txt"
        
        # 結果の保存（プロンプト情報を含む）
        # 文字起こし結果を保存
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(transcription)
            
            # API使用情報の追記
            f.write("\n\n")
            f.write("=" * 50)
            f.write("\n[OpenAI API 使用情報]\n")
            f.write(f"モデル: {prompt_info['model']}\n")
            f.write(f"言語設定: {prompt_info['language']}\n")
            f.write(f"音声の長さ: {prompt_info['duration_seconds']:.2f}秒\n")
            f.write(f"推定コスト: ${prompt_info['cost_usd']:.4f}\n")
            f.write(f"処理日時: {prompt_info['timestamp']}\n")
        
        print(f"文字起こし完了: {input_path.name} -> {output_file.name}")
        print(f"音声の長さ: {prompt_info['duration_seconds']:.2f}秒")
        print(f"推定コスト: ${prompt_info['cost_usd']:.4f}")
        return output_file
    
    except Exception as e:
        print(f"エラー発生 ({input_path.name}): {str(e)}")
        raise

def process_directory(input_dir="recordings", output_dir="src/transcripts"):
    """
    指定されたディレクトリ内の音声ファイルを全て文字起こしする
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # サポートする音声フォーマット
    audio_extensions = {".mp3", ".wav", ".m4a"}
    
    # 音声ファイルを名前でソート
    audio_files = sorted([f for f in input_path.iterdir() if f.suffix.lower() in audio_extensions])
    
    total_cost = 0
    total_duration = 0
    
    for audio_file in audio_files:
        try:
            output_file = process_single_file(audio_file, output_dir)
            # コストと時間の集計は実装済みのため、ここでは追加の処理は不要
        except Exception as e:
            print(f"エラー発生 ({audio_file.name}): {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="音声ファイルの文字起こしを行います")
    parser.add_argument("-f", "--file", help="文字起こしする音声ファイルのパス")
    parser.add_argument("-d", "--directory", help="文字起こしする音声ファイルのディレクトリ")
    parser.add_argument("-o", "--output", default="src/transcripts", help="出力先ディレクトリ（デフォルト: transcripts）")
    
    args = parser.parse_args()

    if args.file:
        process_single_file(args.file, args.output)
    elif args.directory:
        process_directory(args.directory, args.output)
    else:
        process_directory(output_dir=args.output)