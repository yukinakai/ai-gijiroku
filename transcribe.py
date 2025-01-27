import os
from pathlib import Path
from openai import OpenAI
from datetime import timedelta
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
            # 文字起こしの実行
            transcription = transcribe_audio(str(audio_file))
            
            # 出力ファイル名の設定
            output_file = output_path / f"{audio_file.stem}.txt"
            
            # 結果の保存
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(transcription)
            
            print(f"文字起こし完了: {audio_file.name} -> {output_file.name}")
        
        except Exception as e:
            print(f"エラー発生 ({audio_file.name}): {str(e)}")

if __name__ == "__main__":
    process_directory()