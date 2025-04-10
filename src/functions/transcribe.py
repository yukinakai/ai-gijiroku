import os
import argparse
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime
from pydub import AudioSegment
import tempfile
import numpy as np
import soundfile as sf
import threading
import time
from typing import Dict, Any, List, Optional, Tuple, Union
import wave
from pyannote.audio import Pipeline

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
        # その他の場合（属性としてアクセス）
        return {
            'segments': [{
                'start': segment.start,
                'text': segment.text
            } for segment in response.segments],
            'duration': response.duration
        }

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
                    model="whisper-1",
                    file=audio_file,
                    language="ja",
                    response_format="verbose_json"
                )
                
                # レスポンスデータを取得
                response_data = get_response_data(response)
                
                # 結果を整形
                for segment in response_data['segments']:
                    timestamp = format_timestamp(segment['start'] + total_duration)
                    text = segment['text'].strip()
                    all_transcriptions.append(f"{timestamp} {text}")
                
                # チャンクの長さを合計に追加
                total_duration += response_data['duration']
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
    
    # APIの使用情報を作成
    cost = calculate_audio_cost(total_duration)
    prompt_info = {
        "model": "whisper-1",
        "language": "ja",
        "duration_seconds": total_duration,
        "cost_usd": cost,
        "timestamp": datetime.now().isoformat()
    }
    
    return "\n".join(all_transcriptions), prompt_info

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

def transcribe_realtime_chunk(audio_data, sample_rate=48000):
    """
    リアルタイムで録音された音声チャンクを文字起こしする
    
    Args:
        audio_data (numpy.ndarray): 音声データ（NumPy配列）
        sample_rate (int): サンプリングレート
    
    Returns:
        tuple: (文字起こしテキスト, 開始時間)
    """
    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # NumPy配列をWAVファイルとして保存
        sf.write(temp_path, audio_data, sample_rate)
        
        # 音声の長さをチェック
        chunk_duration = get_audio_duration(temp_path)
        if chunk_duration < 0.1:
            return None, 0
        
        with open(temp_path, "rb") as audio_file:
            # OpenAI APIを使用して文字起こし
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ja",
                response_format="verbose_json"
            )
            
            # レスポンスデータを取得
            response_data = get_response_data(response)
            
            # 文字起こし結果を整形
            transcriptions = []
            for segment in response_data['segments']:
                timestamp = format_timestamp(segment['start'])
                text = segment['text'].strip()
                if text:
                    transcriptions.append(f"{timestamp} {text}")
            
            transcription = "\n".join(transcriptions) if transcriptions else None
            return transcription, response_data['duration']
    
    except Exception as e:
        print(f"リアルタイム文字起こし中にエラーが発生しました: {str(e)}")
        return None, 0
    
    finally:
        # 一時ファイルを削除
        if os.path.exists(temp_path):
            os.remove(temp_path)

class RealtimeTranscriber:
    """リアルタイム文字起こしを管理するクラス"""
    
    def __init__(self, output_file, chunk_duration=30.0):
        """
        Parameters:
        - output_file: 文字起こし結果を保存するファイルパス
        - chunk_duration: 一度に処理する音声チャンクの長さ（秒）
        """
        self.output_file = output_file
        self.chunk_duration = chunk_duration
        self.audio_buffer = []
        self.total_duration = 0
        self.lock = threading.Lock()
        self.processing = False
        self.thread = None
        self.should_stop = False
        
        # 出力ファイルの準備
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
        
        # ファイルが既に存在する場合は削除（常に新しく開始）
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
            except Exception as e:
                print(f"警告: 既存のリアルタイム文字起こしファイルを削除できませんでした: {str(e)}")
        
        # 新しいファイルを作成
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# リアルタイム文字起こし\n\n")
    
    def add_audio(self, audio_chunk):
        """
        音声チャンクをバッファに追加
        
        Parameters:
        - audio_chunk: numpy.ndarray形式の音声データ
        """
        with self.lock:
            self.audio_buffer.append(audio_chunk)
            
            # バッファが十分なサイズになったら処理を開始
            buffer_duration = len(self.audio_buffer) * (len(audio_chunk) / 48000)
            if buffer_duration >= self.chunk_duration and not self.processing:
                self._process_buffer()
    
    def _process_buffer(self):
        """バッファ内の音声を処理"""
        self.processing = True
        
        # 処理用のスレッドを開始
        self.thread = threading.Thread(target=self._transcribe_buffer)
        self.thread.daemon = True
        self.thread.start()
    
    def _transcribe_buffer(self):
        """バッファ内の音声を文字起こし"""
        try:
            with self.lock:
                # バッファの音声を結合
                if not self.audio_buffer:
                    self.processing = False
                    return
                    
                audio_data = np.concatenate(self.audio_buffer, axis=0)
                self.audio_buffer = []
            
            # 文字起こし実行
            result, duration = transcribe_realtime_chunk(audio_data)
            if result:
                # 結果をファイルに追記
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    f.write(f"{result}\n")
                
                # 合計時間を更新
                self.total_duration += duration
                
                # コンソールに進捗表示
                print(f"\n新しい文字起こし結果を追加しました（合計: {self.total_duration:.1f}秒）")
                
        except Exception as e:
            print(f"バッファ処理中にエラーが発生しました: {str(e)}")
        
        finally:
            self.processing = False
    
    def start(self):
        """文字起こし処理を開始"""
        self.should_stop = False
    
    def stop(self):
        """文字起こし処理を停止して残りのバッファを処理"""
        self.should_stop = True
        
        # 残りのバッファを処理
        if self.audio_buffer:
            print("\n残りの音声を処理中...")
            self._transcribe_buffer()
        
        # 処理スレッドが存在する場合は終了を待機
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=60)  # 最大60秒待機
        
        # 最終情報を出力
        with open(self.output_file, 'a', encoding='utf-8') as f:
            f.write("\n\n")
            f.write("=" * 50)
            f.write("\n[OpenAI API 使用情報]\n")
            f.write(f"モデル: whisper-1\n")
            f.write(f"言語設定: ja\n")
            f.write(f"音声の長さ: {self.total_duration:.2f}秒\n")
            f.write(f"推定コスト: ${calculate_audio_cost(self.total_duration):.4f}\n")
            f.write(f"処理日時: {datetime.now().isoformat()}\n")
        
        print(f"\n文字起こし完了: {self.output_file}")
        print(f"音声の長さ: {self.total_duration:.2f}秒")
        print(f"推定コスト: ${calculate_audio_cost(self.total_duration):.4f}")
        
        return self.output_file

class SpeakerDiarization:
    """話者判定を行うクラス"""
    
    def __init__(self, access_token=None, min_speech_duration=1.0):
        """
        Parameters:
        - access_token: HuggingFaceのアクセストークン（デフォルトはNone、環境変数から取得）
        - min_speech_duration: 最小発話時間（秒）。これより短い発話は無視される
        """
        self.min_speech_duration = min_speech_duration
        self.pipeline = None
        
        # 環境変数からトークンを取得（引数で指定されていない場合）
        self.token = access_token or os.getenv("HUGGINGFACE_TOKEN")
        
        # HuggingFace対応の初期化
        try:
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization@2.1",
                use_auth_token=self.token
            )
            print("話者判定パイプラインを初期化しました")
        except Exception as e:
            print(f"話者判定パイプラインの初期化に失敗しました: {e}")
            print("HuggingFaceのトークンを取得して環境変数に設定してください。")
            print("https://huggingface.co/pyannote/speaker-diarization から取得できます。")
    
    def process_audio(self, audio_data, sample_rate=48000):
        """
        音声データを処理して話者判定結果を返す
        
        Parameters:
        - audio_data: numpy.ndarray形式の音声データ
        - sample_rate: サンプリングレート
        
        Returns:
        - segments: [(start, end, speaker)] の形式の話者判定結果リスト
        """
        if self.pipeline is None:
            print("話者判定パイプラインが初期化されていません")
            return []
        
        # 一時ファイルに保存して処理
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # NumPy配列をWAVファイルとして保存
            sf.write(temp_path, audio_data, sample_rate)
            
            # 話者判定を実行
            diarization = self.pipeline(temp_path)
            
            # 結果を処理
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                # 最小発話時間よりも短い発話は無視
                if turn.end - turn.start < self.min_speech_duration:
                    continue
                
                segments.append((turn.start, turn.end, speaker))
            
            return segments
            
        except Exception as e:
            print(f"話者判定処理中にエラーが発生しました: {e}")
            return []
            
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def get_speaker_segments(self, audio_data, sample_rate=48000):
        """
        音声データから話者ごとのセグメントを抽出
        
        Parameters:
        - audio_data: numpy.ndarray形式の音声データ
        - sample_rate: サンプリングレート
        
        Returns:
        - speaker_segments: 各話者ごとの音声セグメントのリスト
        [
            {
                'speaker': 'SPEAKER_00',
                'start': 0.0,
                'end': 2.5,
                'audio': numpy array
            },
            ...
        ]
        """
        segments = self.process_audio(audio_data, sample_rate)
        
        if not segments:
            return []
        
        speaker_segments = []
        for start, end, speaker in segments:
            # 時間をサンプル数に変換
            start_sample = int(start * sample_rate)
            end_sample = int(end * sample_rate)
            
            # 範囲チェック
            if end_sample > len(audio_data):
                end_sample = len(audio_data)
            
            if start_sample >= end_sample:
                continue
                
            # その区間の音声を抽出
            segment_audio = audio_data[start_sample:end_sample]
            
            speaker_segments.append({
                'speaker': speaker,
                'start': start,
                'end': end,
                'audio': segment_audio
            })
            
        return speaker_segments

def transcribe_speaker_segments(speaker_segments, sample_rate=48000):
    """
    話者ごとのセグメントを文字起こしする
    
    Parameters:
    - speaker_segments: get_speaker_segments関数で得られた話者セグメントのリスト
    - sample_rate: サンプリングレート
    
    Returns:
    - transcribed_segments: 文字起こし結果を含む話者セグメントのリスト
    [
        {
            'speaker': 'SPEAKER_00',
            'start': 0.0,
            'end': 2.5,
            'text': '文字起こし結果'
        },
        ...
    ]
    """
    transcribed_segments = []
    
    for segment in speaker_segments:
        # セグメントの音声データを取得
        audio_data = segment['audio']
        
        # 一時ファイルに保存して処理
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # NumPy配列をWAVファイルとして保存
            sf.write(temp_path, audio_data, sample_rate)
            
            # 文字起こしを実行
            with open(temp_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja",
                    response_format="verbose_json"
                )
                
                # レスポンスデータを取得
                response_data = get_response_data(response)
                
                # 文字起こし結果を取得（シンプルなテキスト）
                text = response_data['text'].strip()
                
                # 新しいセグメント情報を作成（音声データは含めない）
                transcribed_segment = {
                    'speaker': segment['speaker'],
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': text
                }
                
                transcribed_segments.append(transcribed_segment)
        
        except Exception as e:
            print(f"セグメントの文字起こし中にエラーが発生しました: {e}")
            # エラーが発生した場合も、空のテキストで情報を保持
            transcribed_segment = {
                'speaker': segment['speaker'],
                'start': segment['start'],
                'end': segment['end'],
                'text': ""
            }
            transcribed_segments.append(transcribed_segment)
            
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    return transcribed_segments

def generate_transcript_from_segments(transcribed_segments):
    """
    文字起こしされたセグメントから整形された文字起こしテキストを生成
    
    Parameters:
    - transcribed_segments: transcribe_speaker_segments関数の結果
    
    Returns:
    - transcript: 整形された文字起こしテキスト
    """
    lines = []
    
    for segment in transcribed_segments:
        # タイムスタンプを整形
        timestamp = format_timestamp(segment['start'])
        speaker = segment['speaker']
        text = segment['text']
        
        if text:  # 空のテキストは除外
            line = f"[{timestamp}] [{speaker}] {text}"
            lines.append(line)
    
    return "\n".join(lines)

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