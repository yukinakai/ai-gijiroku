import os
import whisper
from datetime import timedelta
from pathlib import Path

def format_timestamp(seconds: float) -> str:
    """秒数を[HH:MM:SS]形式の文字列に変換する"""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"

def transcribe_audio(audio_path: str, output_dir: str = "transcripts") -> str:
    """
    音声ファイルを文字起こしし、指定されたフォーマットでテキストファイルに保存する
    
    Args:
        audio_path: 音声ファイルのパス
        output_dir: 出力ディレクトリ（デフォルト: "transcripts"）
    
    Returns:
        生成されたテキストファイルのパス
    """
    # 出力ディレクトリの作成
    os.makedirs(output_dir, exist_ok=True)
    
    # Whisperモデルの読み込み
    model = whisper.load_model("base")
    
    # 音声の文字起こし
    result = model.transcribe(audio_path, language="ja")
    
    # 出力ファイル名の生成
    audio_file = Path(audio_path)
    output_path = Path(output_dir) / f"{audio_file.stem}.txt"
    
    # 結果をファイルに書き出し
    with open(output_path, "w", encoding="utf-8") as f:
        for segment in result["segments"]:
            timestamp = format_timestamp(segment["start"])
            text = segment["text"].strip()
            f.write(f"{timestamp} {text}\n")
    
    return str(output_path)

def process_directory(input_dir: str = "recordings", output_dir: str = "transcripts") -> list[str]:
    """
    指定されたディレクトリ内の全ての音声ファイルを処理する
    
    Args:
        input_dir: 入力ディレクトリ（デフォルト: "recordings"）
        output_dir: 出力ディレクトリ（デフォルト: "transcripts"）
    
    Returns:
        生成されたテキストファイルのパスのリスト
    """
    audio_extensions = {".mp3", ".wav", ".m4a", ".flac"}
    processed_files = []
    
    for file_path in Path(input_dir).glob("*"):
        if file_path.suffix.lower() in audio_extensions:
            output_path = transcribe_audio(str(file_path), output_dir)
            processed_files.append(output_path)
    
    return processed_files

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="音声ファイルの文字起こしツール")
    parser.add_argument("--input", "-i", default="recordings",
                      help="入力ディレクトリのパス（デフォルト: recordings）")
    parser.add_argument("--output", "-o", default="transcripts",
                      help="出力ディレクトリのパス（デフォルト: transcripts）")
    
    args = parser.parse_args()
    
    processed_files = process_directory(args.input, args.output)
    print(f"処理完了: {len(processed_files)}ファイルを変換しました")
    for file_path in processed_files:
        print(f"- {file_path}")