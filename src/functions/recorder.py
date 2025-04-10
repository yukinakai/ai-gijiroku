#!/usr/bin/env python
import sounddevice as sd
import soundfile as sf
import numpy as np
import os
import time
import sys
import select
import termios
import tty
from typing import Optional, Tuple, Dict, Any, List, Union
from datetime import datetime
from src.functions.transcribe import RealtimeTranscriber, SpeakerDiarization, transcribe_speaker_segments, generate_transcript_from_segments, calculate_audio_cost

class AudioRecorder:
    """オーディオ録音を管理するクラス"""
    
    def __init__(self, recordings_dir: str, min_recording_duration: float = 0.5):
        """
        Parameters:
        - recordings_dir: 録音ファイルの保存ディレクトリ
        - min_recording_duration: 最小録音時間（秒）
        """
        self.recordings_dir = recordings_dir
        self.min_recording_duration = min_recording_duration
        os.makedirs(recordings_dir, exist_ok=True)

    @staticmethod
    def list_devices() -> list[Dict[str, Any]]:
        """利用可能なオーディオデバイスを一覧表示"""
        devices = sd.query_devices()
        print("\n利用可能なオーディオデバイス:")
        for i, device in enumerate(devices):
            print(f"\nデバイス {i}:")
            print(f"  名前: {device['name']}")
            print(f"  入力チャンネル: {device['max_input_channels']}")
            print(f"  出力チャンネル: {device['max_output_channels']}")
            print(f"  デフォルトサンプルレート: {device['default_samplerate']}")
        return devices

    @staticmethod
    def find_blackhole_device() -> Tuple[Optional[int], Optional[Dict[str, Any]]]:
        """BlackHoleデバイスのインデックスを検索"""
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if 'BlackHole' in device['name']:
                return i, device
        return None, None

    @staticmethod
    def _print_progress(elapsed_time: float) -> None:
        """録音の経過時間を表示"""
        sys.stdout.write('\r')
        sys.stdout.write(f"録音時間: {elapsed_time:.1f}秒 ")
        sys.stdout.flush()

    def validate_input_device(self, input_device_id: int) -> Tuple[bool, Optional[str]]:
        """入力デバイスが有効かどうかを検証"""
        devices = sd.query_devices()
        
        if input_device_id >= len(devices):
            return False, "有効な入力デバイスIDを指定してください。"
            
        input_device = devices[input_device_id]
        if input_device['max_input_channels'] == 0:
            return False, f"デバイス {input_device_id} は入力デバイスではありません。"
            
        return True, None

    @staticmethod
    def _is_key_pressed() -> Optional[str]:
        """キー入力をチェック（非ブロッキング）"""
        try:
            if select.select([sys.stdin], [], [], 0.0)[0]:
                return sys.stdin.read(1)
        except (select.error, IOError, AttributeError):
            # テスト環境やリダイレクトされた標準入力の場合は
            # _is_key_pressed_mockメソッドが使用される
            pass
        return None

    def record(self, filename: Optional[str] = None, sample_rate: int = 48000, 
               input_device_id: Optional[int] = None) -> Optional[str]:
        """
        指定された入力デバイスとBlackHoleを使用してオーディオを録音
        
        Parameters:
        - filename: 保存するファイル名（YYYYMMDD_[指定された名前].wav形式）
        - sample_rate: サンプリングレート（デフォルト48kHz）
        - input_device_id: 入力デバイスのID
        
        Returns:
        - Optional[str]: 録音ファイルのパス。エラー時はNone
        """
        # 入力デバイスの検証
        is_valid, error_message = self.validate_input_device(input_device_id)
        if not is_valid:
            print(f"\nエラー: {error_message}")
            return None

        # BlackHoleデバイスを検索
        blackhole_idx, blackhole_device = self.find_blackhole_device()
        if blackhole_idx is None:
            print("\nエラー: BlackHoleデバイスが見つかりません。")
            print("1. BlackHoleがインストールされているか確認してください。")
            print("2. システム環境設定 > サウンド で BlackHole 2chが表示されているか確認してください。")
            return None

        devices = sd.query_devices()
        input_device = devices[input_device_id]

        # ファイル名の生成 - メモリリーク対策：文字列操作を最適化
        current_date = datetime.now().strftime('%Y%m%d')
        filename_base = filename if filename else current_date
        if filename and not filename.endswith('.wav'):
            filename = f"{current_date}_{filename_base}.wav"
        else:
            filename = f"{current_date}_{filename_base}"
        
        filepath = os.path.join(self.recordings_dir, filename)

        print("\n録音の準備:")
        print("1. システム環境設定 > サウンド > 出力 で録音したいデバイスを選択")
        print("2. オーディオMIDI設定を開き、複数出力装置を作成")
        print("3. 複数出力装置に、録音したいデバイスとBlackHole 2chの両方を追加")
        print("4. システム環境設定 > サウンド > 出力 で作成した複数出力装置を選択")
        print("\n上記の設定が完了したら、Enterキーを押して録音を開始してください。")
        input()

        print(f"\n使用するデバイス:")
        print(f"録音デバイス: {blackhole_device['name']}")
        print(f"保存先: {filepath}")

        # メモリリーク対策：事前に固定サイズのバッファを確保
        max_frames = 3600 * sample_rate // 1024  # 最大1時間分のフレーム
        frames = []
        recording_duration = 0
        old_settings = None
        input_stream = None
        blackhole_stream = None
        
        try:
            print("\n録音を開始します...")
            print("qキーを押して録音を停止")
            print("経過時間:")

            # ターミナルの設定を変更（キー入力を即座に取得するため）
            try:
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except (termios.error, IOError, AttributeError):
                # テスト環境やリダイレクトされた標準入力の場合はスキップ
                pass

            input_stream = sd.InputStream(
                device=input_device_id,
                channels=input_device['max_input_channels'],
                samplerate=sample_rate,
                callback=None
            )
            
            blackhole_stream = sd.InputStream(
                device=blackhole_idx,
                channels=blackhole_device['max_input_channels'],
                samplerate=sample_rate,
                callback=None
            )

            input_stream.start()
            blackhole_stream.start()

            start_time = time.time()
            
            # メモリリーク対策：処理をより効率的に
            while True:
                # 一度に大きなチャンクを読み込む
                input_data = input_stream.read(1024)[0]
                blackhole_data = blackhole_stream.read(1024)[0]
                
                if input_data.shape[1] != blackhole_data.shape[1]:
                    min_channels = min(input_data.shape[1], blackhole_data.shape[1])
                    input_data = input_data[:, :min_channels]
                    blackhole_data = blackhole_data[:, :min_channels]
                
                # メモリリーク対策：一時変数を最小限に
                frames.append((input_data + blackhole_data) / 2)
                
                # フレーム数が最大値を超えた場合、古いフレームを削除
                if len(frames) > max_frames:
                    frames = frames[-max_frames:]
                
                current_time = time.time() - start_time
                recording_duration = current_time
                
                # 表示更新は0.5秒ごとに行う
                if int(current_time * 2) % 2 == 0:
                    self._print_progress(current_time)

                # qキーが押されたかチェック - メモリリーク対策：効率的なキー処理
                key = self._is_key_pressed()
                if key == 'q':
                    print("\n録音を停止します...")
                    break

                # メモリリーク対策：スリープでCPU使用率を下げる
                time.sleep(0.01)

        except Exception as e:
            print(f"\nエラー: {str(e)}")
            return None
        finally:
            # ターミナルの設定を元に戻す
            if old_settings is not None:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except (termios.error, IOError):
                    pass

            # ストリームのクリーンアップ
            if input_stream is not None:
                input_stream.stop()
                input_stream.close()
            if blackhole_stream is not None:
                blackhole_stream.stop()
                blackhole_stream.close()

            if frames:
                if recording_duration < self.min_recording_duration:
                    print(f"\nエラー: 録音時間が短すぎます（{recording_duration:.2f}秒）")
                    print(f"最小録音時間は{self.min_recording_duration}秒です。")
                    return None

                print("\n録音処理中...")
                print(f"録音時間: {recording_duration:.2f}秒")
                
                try:
                    # メモリリーク対策：より効率的なnumpy処理
                    recording = np.concatenate(frames, axis=0)

                    if recording.ndim > 1 and recording.shape[1] > 1:
                        recording = np.mean(recording, axis=1)

                    sf.write(filepath, recording, sample_rate)
                    
                    # メモリリーク対策：明示的にメモリ解放
                    del frames
                    del recording
                    
                    print(f"録音が完了しました。")
                    print(f"保存先: {filepath}")
                    return filepath

                except Exception as e:
                    print(f"\n録音データの処理中にエラーが発生しました: {str(e)}")
                    return None
            else:
                print("\nエラー: 録音データが空です。")
                return None

    def record_realtime(self, filename: Optional[str] = None, sample_rate: int = 48000, 
                    input_device_id: Optional[int] = None) -> Optional[str]:
        """
        リアルタイム文字起こし付きで録音を行う
        新機能: 話者判定を使用したリアルタイム文字起こし
        
        Parameters:
        - filename: 録音ファイル名（デフォルトは日時から自動生成）
        - sample_rate: サンプリングレート（デフォルトは48000Hz）
        - input_device_id: 入力デバイスID（デフォルトはNone、ユーザーから入力を求める）
        
        Returns:
        - filepath: 録音ファイルのパス、エラーが発生した場合はNone
        """
        # 入力デバイスの選択または確認
        if input_device_id is None:
            print("\n利用可能なオーディオデバイス:")
            devices = self.list_devices()
            for idx, device in enumerate(devices):
                print(f"{idx}: {device['name']} (入力: {device['max_input_channels']}ch, 出力: {device['max_output_channels']}ch)")
            
            try:
                input_device_id = int(input("使用する入力デバイスの番号を入力してください: "))
                if input_device_id < 0 or input_device_id >= len(devices):
                    print("無効なデバイス番号です。")
                    return None
            except ValueError:
                print("数値を入力してください。")
                return None
        
        # 入力デバイスの検証
        is_valid, error_message = self.validate_input_device(input_device_id)
        if not is_valid:
            print(f"エラー: {error_message}")
            return None
        
        # BlackHoleデバイスの検索
        blackhole_idx, blackhole_device = self.find_blackhole_device()
        if blackhole_idx is None:
            print("BlackHole 2chデバイスが見つかりませんでした。インストールしてください。")
            return None
        
        # すべてのデバイス一覧を取得
        devices = self.list_devices()
        input_device = devices[input_device_id]
        
        # 録音ファイル名の設定
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        if filename is None:
            filename = f"{timestamp}_audio.wav"
        elif not filename.endswith('.wav'):
            filename = f"{filename}.wav"
        
        # ファイルパスを作成
        filepath = os.path.join(self.recordings_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 文字起こしファイルパスの設定
        transcription_dir = "src/transcripts"
        os.makedirs(transcription_dir, exist_ok=True)
        
        realtime_filepath = os.path.join(transcription_dir, "realtime.txt")
        transcript_basename = filename.replace('.wav', '.txt')
        final_transcription_filepath = os.path.join(transcription_dir, transcript_basename)
        
        # 録音設定の説明
        print("\n録音の準備:")
        print("1. システム環境設定 > サウンド > 出力 でBlackHole 2chを選択")
        print("2. オーディオMIDI設定を開き、複数出力装置を作成")
        print("3. 複数出力装置に、録音したいデバイスとBlackHole 2chの両方を追加")
        print("4. システム環境設定 > サウンド > 出力 で作成した複数出力装置を選択")
        print("\n上記の設定が完了したら、Enterキーを押して録音を開始してください。")
        input()

        print(f"\n使用するデバイス:")
        print(f"録音デバイス: {blackhole_device['name']}")
        print(f"保存先: {filepath}")
        print(f"リアルタイム文字起こし結果: {realtime_filepath}")
        print(f"（録音終了後のファイル名: {final_transcription_filepath}）")

        # リアルタイム文字起こしファイルの初期化
        with open(realtime_filepath, 'w', encoding='utf-8') as f:
            f.write("# リアルタイム文字起こし（話者判定付き）\n\n")
            
        # 話者判定モジュールの初期化
        diarization = SpeakerDiarization()
            
        # メモリリーク対策：事前に固定サイズのバッファを確保
        frames = []
        recording_duration = 0
        old_settings = None
        input_stream = None
        blackhole_stream = None
        
        try:
            print("\n録音を開始します...")
            print("qキーを押して録音を停止")
            print("経過時間:")

            # ターミナルの設定を変更（キー入力を即座に取得するため）
            try:
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except (termios.error, IOError, AttributeError):
                # テスト環境やリダイレクトされた標準入力の場合はスキップ
                pass

            input_stream = sd.InputStream(
                device=input_device_id,
                channels=input_device['max_input_channels'],
                samplerate=sample_rate,
                callback=None
            )
            
            blackhole_stream = sd.InputStream(
                device=blackhole_idx,
                channels=blackhole_device['max_input_channels'],
                samplerate=sample_rate,
                callback=None
            )

            input_stream.start()
            blackhole_stream.start()

            start_time = time.time()
            chunk_size = 1024  # 一度に読み込むフレームのサイズ
            speaker_buffer = []  # 話者判定用のバッファ
            speaker_samples = 0  # 話者判定用のサンプル数カウンタ
            last_speaker_time = start_time  # 最後に話者判定を実行した時間
            last_speaker = None  # 最後に検出された話者
            
            # 音声データのバッファ（話者ごとに分けて保存）
            current_speaker_audio = []
            
            while True:
                # 一度に大きなチャンクを読み込む
                input_data = input_stream.read(chunk_size)[0]
                blackhole_data = blackhole_stream.read(chunk_size)[0]
                
                if input_data.shape[1] != blackhole_data.shape[1]:
                    min_channels = min(input_data.shape[1], blackhole_data.shape[1])
                    input_data = input_data[:, :min_channels]
                    blackhole_data = blackhole_data[:, :min_channels]
                
                # 録音データをバッファに追加
                mixed_data = (input_data + blackhole_data) / 2
                frames.append(mixed_data)
                
                # 話者判定用のバッファにも追加
                speaker_buffer.append(mixed_data)
                speaker_samples += len(mixed_data)
                
                # 一定量（10秒分）のデータが貯まったら話者判定を実行
                current_time = time.time()
                buffer_duration_sec = speaker_samples / sample_rate
                time_since_last_process = current_time - last_speaker_time
                
                if buffer_duration_sec >= 10.0 and time_since_last_process >= 5.0:
                    # 十分なデータが貯まっていれば話者判定を実行
                    combined_buffer = np.concatenate(speaker_buffer, axis=0)
                    
                    # 現在のバッファ内で話者判定
                    speaker_segments = diarization.get_speaker_segments(combined_buffer, sample_rate)
                    
                    if speaker_segments:
                        # 話者が検出された場合、セグメントごとに文字起こし
                        transcribed_segments = transcribe_speaker_segments(speaker_segments, sample_rate)
                        
                        # 文字起こし結果をファイルに追記
                        transcript_text = generate_transcript_from_segments(transcribed_segments)
                        if transcript_text:
                            with open(realtime_filepath, 'a', encoding='utf-8') as f:
                                f.write(f"{transcript_text}\n\n")
                            
                            # コンソールに進捗表示
                            print(f"\n新しい文字起こし結果を追加しました（{len(transcribed_segments)}セグメント）")
                    
                    # バッファをリセット
                    speaker_buffer = []
                    speaker_samples = 0
                    last_speaker_time = current_time
                
                current_time = time.time() - start_time
                recording_duration = current_time
                
                # 表示更新は0.5秒ごとに行う
                if int(current_time * 2) % 2 == 0:
                    self._print_progress(current_time)

                # qキーが押されたかチェック
                key = self._is_key_pressed()
                if key == 'q':
                    break
                    
            # 録音の終了処理
            print("\n\n録音を停止しました。ファイルに保存中...")
            
            # 録音が最小録音時間より短い場合はスキップ
            if recording_duration < self.min_recording_duration:
                print(f"録音時間が短すぎます（{recording_duration:.2f}秒 < {self.min_recording_duration}秒）。ファイルは保存されません。")
                return None
            
            # NumPy配列を結合し、ファイルに保存
            data = np.concatenate(frames, axis=0)
            sf.write(filepath, data, sample_rate)
            
            print(f"録音完了: {filepath}")
            print(f"録音時間: {recording_duration:.2f}秒")
            
            # 残りの音声データを処理
            if speaker_buffer:
                combined_buffer = np.concatenate(speaker_buffer, axis=0)
                speaker_segments = diarization.get_speaker_segments(combined_buffer, sample_rate)
                
                if speaker_segments:
                    transcribed_segments = transcribe_speaker_segments(speaker_segments, sample_rate)
                    transcript_text = generate_transcript_from_segments(transcribed_segments)
                    
                    if transcript_text:
                        with open(realtime_filepath, 'a', encoding='utf-8') as f:
                            f.write(f"{transcript_text}\n\n")
            
            # 最終的な統計情報を追記
            with open(realtime_filepath, 'a', encoding='utf-8') as f:
                f.write("\n\n")
                f.write("=" * 50)
                f.write("\n[OpenAI API 使用情報]\n")
                f.write(f"モデル: whisper-1\n")
                f.write(f"言語設定: ja\n")
                f.write(f"音声の長さ: {recording_duration:.2f}秒\n")
                f.write(f"推定コスト: ${calculate_audio_cost(recording_duration):.4f}\n")
                f.write(f"処理日時: {datetime.now().isoformat()}\n")
            
            # 文字起こしファイルをリネーム
            try:
                if os.path.exists(realtime_filepath):
                    if os.path.exists(final_transcription_filepath):
                        os.remove(final_transcription_filepath)  # 既存ファイルがある場合は削除
                    os.rename(realtime_filepath, final_transcription_filepath)
                    print(f"文字起こし結果をリネームしました: {final_transcription_filepath}")
            except Exception as e:
                print(f"文字起こしファイルのリネーム中にエラーが発生しました: {str(e)}")
            
            return filepath
            
        except Exception as e:
            print(f"\nエラーが発生しました: {str(e)}")
            return None
            
        finally:
            # ストリームのクリーンアップ
            if input_stream:
                input_stream.stop()
                input_stream.close()
            if blackhole_stream:
                blackhole_stream.stop()
                blackhole_stream.close()
                
            # ターミナルの設定を元に戻す
            if old_settings:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except (termios.error, IOError):
                    pass