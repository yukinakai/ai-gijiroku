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
import tempfile
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

class AudioRecorder:
    def __init__(self, recordings_dir: str, min_recording_duration: float = 0.5,
                 chunk_size: int = 1024, buffer_size: int = 10):
        self.recordings_dir = recordings_dir
        self.min_recording_duration = min_recording_duration
        self.chunk_size = chunk_size
        self.buffer_size = buffer_size
        os.makedirs(recordings_dir, exist_ok=True)

    @staticmethod
    def list_devices() -> list[Dict[str, Any]]:
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
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if 'BlackHole' in device['name']:
                return i, device
        return None, None

    @staticmethod
    def _print_progress(elapsed_time: float) -> None:
        sys.stdout.write('\r')
        sys.stdout.write(f"録音時間: {elapsed_time:.1f}秒 ")
        sys.stdout.flush()

    def validate_input_device(self, input_device_id: int) -> Tuple[bool, Optional[str]]:
        devices = sd.query_devices()
        
        if input_device_id >= len(devices):
            return False, "有効な入力デバイスIDを指定してください。"
            
        input_device = devices[input_device_id]
        if input_device['max_input_channels'] == 0:
            return False, f"デバイス {input_device_id} は入力デバイスではありません。"
            
        return True, None

    @staticmethod
    def _is_key_pressed() -> Optional[str]:
        try:
            if select.select([sys.stdin], [], [], 0.0)[0]:
                return sys.stdin.read(1)
        except (select.error, IOError, AttributeError):
            pass
        return None

    def record(self, filename: Optional[str] = None, sample_rate: int = 48000,
               input_device_id: Optional[int] = None) -> Optional[str]:
        is_valid, error_message = self.validate_input_device(input_device_id)
        if not is_valid:
            print(f"\nエラー: {error_message}")
            return None

        blackhole_idx, blackhole_device = self.find_blackhole_device()
        if blackhole_idx is None:
            print("\nエラー: BlackHoleデバイスが見つかりません。")
            print("1. BlackHoleがインストールされているか確認してください。")
            print("2. システム環境設定 > サウンド で BlackHole 2chが表示されているか確認してください。")
            return None

        devices = sd.query_devices()
        input_device = devices[input_device_id]

        current_date = datetime.now().strftime('%Y%m%d')
        if filename:
            if not filename.endswith('.wav'):
                filename = f"{filename}.wav"
            filename = f"{current_date}_{filename}"
        else:
            filename = f"{current_date}.wav"
        
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

        recording_duration = 0
        old_settings = None
        
        # 一時ファイルを作成して録音データを直接書き込む
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_filepath = temp_file.name
        temp_file.close()

        try:
            print("\n録音を開始します...")
            print("qキーを押して録音を停止")
            print("経過時間:")

            try:
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except (termios.error, IOError, AttributeError):
                pass

            # WAVファイルを開いて録音データを直接書き込む
            with sf.SoundFile(temp_filepath, mode='w', samplerate=sample_rate,
                            channels=min(input_device['max_input_channels'],
                                       blackhole_device['max_input_channels']),
                            format='WAV') as wav_file:

                input_stream = sd.InputStream(
                    device=input_device_id,
                    channels=input_device['max_input_channels'],
                    samplerate=sample_rate,
                    callback=None,
                    blocksize=self.chunk_size
                )
                
                blackhole_stream = sd.InputStream(
                    device=blackhole_idx,
                    channels=blackhole_device['max_input_channels'],
                    samplerate=sample_rate,
                    callback=None,
                    blocksize=self.chunk_size
                )

                input_stream.start()
                blackhole_stream.start()

                start_time = time.time()

                while True:
                    input_data = input_stream.read(self.chunk_size)[0]
                    blackhole_data = blackhole_stream.read(self.chunk_size)[0]
                    
                    if input_data.shape[1] != blackhole_data.shape[1]:
                        min_channels = min(input_data.shape[1], blackhole_data.shape[1])
                        input_data = input_data[:, :min_channels]
                        blackhole_data = blackhole_data[:, :min_channels]
                    
                    combined_data = (input_data + blackhole_data) / 2
                    wav_file.write(combined_data)
                    
                    current_time = time.time() - start_time
                    recording_duration = current_time
                    self._print_progress(current_time)

                    key = self._is_key_pressed()
                    if key == 'q':
                        print("\n録音を停止します...")
                        break

        except Exception as e:
            print(f"\nエラー: {str(e)}")
            os.unlink(temp_filepath)
            return None

        finally:
            if old_settings is not None:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except (termios.error, IOError):
                    pass

            if 'input_stream' in locals():
                input_stream.stop()
                input_stream.close()
            if 'blackhole_stream' in locals():
                blackhole_stream.stop()
                blackhole_stream.close()

        if recording_duration < self.min_recording_duration:
            print(f"\nエラー: 録音時間が短すぎます（{recording_duration:.2f}秒）")
            print(f"最小録音時間は{self.min_recording_duration}秒です。")
            os.unlink(temp_filepath)
            return None

        try:
            # 一時ファイルを最終的な保存先にコピー
            os.rename(temp_filepath, filepath)
            print("\n録音が完了しました。")
            print(f"保存先: {filepath}")
            return filepath

        except Exception as e:
            print(f"\n録音データの処理中にエラーが発生しました: {str(e)}")
            os.unlink(temp_filepath)
            return None