import os
import argparse
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# OpenAI APIキーの確認
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("環境変数 OPENAI_API_KEY が設定されていません。.envファイルを確認してください。")

# OpenAIクライアントの初期化
client = OpenAI()

def format_timestamp(seconds):
    """
    秒数を[00:00:00]形式の文字列に変換する
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"

def transcribe_audio(audio_path):
    """
    音声ファイルを文字起こしする
    """
    # 音声ファイルを開く
    with open(audio_path, "rb") as audio_file:
        # OpenAI APIを使用して文字起こし
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ja",
            response_format="verbose_json"
        )
    
    # 結果を整形
    transcription = []
    for segment in transcript.segments:
        timestamp = format_timestamp(segment.start)
        text = segment.text.strip()
        transcription.append(f"{timestamp} {text}")
    
    return "\n".join(transcription)

def process_single_file(input_file, output_dir="transcripts"):
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
        transcription = transcribe_audio(str(input_path))
        
        # 出力ファイル名の設定
        output_file = output_path / f"{input_path.stem}.txt"
        
        # 結果の保存
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(transcription)
        
        print(f"文字起こし完了: {input_path.name} -> {output_file.name}")
        return output_file
    
    except Exception as e:
        print(f"エラー発生 ({input_path.name}): {str(e)}")
        raise

def process_directory(input_dir="recordings", output_dir="transcripts"):
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
    
    for audio_file in audio_files:
        try:
            process_single_file(audio_file, output_dir)
        except Exception as e:
            print(f"エラー発生 ({audio_file.name}): {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="音声ファイルの文字起こしを行います")
    parser.add_argument("-f", "--file", help="文字起こしする音声ファイルのパス")
    parser.add_argument("-d", "--directory", help="文字起こしする音声ファイルのディレクトリ")
    parser.add_argument("-o", "--output", default="transcripts", help="出力先ディレクトリ（デフォルト: transcripts）")
    
    args = parser.parse_args()
    
    if args.file:
        process_single_file(args.file, args.output)
    elif args.directory:
        process_directory(args.directory, args.output)
    else:
        process_directory(output_dir=args.output)