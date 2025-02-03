#!/usr/bin/env python
import sounddevice as sd
import soundfile as sf
import numpy as np
import os
import time
import sys
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

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

        # ファイル名の生成
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

        frames = []
        recording_duration = 0
        
        try:
            print("\n録音を開始します...")
            print("Ctrl+Cで録音を停止")
            print("経過時間:")

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

            while True:
                input_data = input_stream.read(1024)[0]
                blackhole_data = blackhole_stream.read(1024)[0]
                
                if input_data.shape[1] != blackhole_data.shape[1]:
                    min_channels = min(input_data.shape[1], blackhole_data.shape[1])
                    input_data = input_data[:, :min_channels]
                    blackhole_data = blackhole_data[:, :min_channels]
                
                combined_data = (input_data + blackhole_data) / 2
                frames.append(combined_data)
                
                current_time = time.time() - start_time
                recording_duration = current_time
                self._print_progress(current_time)

        except KeyboardInterrupt:
            print("\n録音を停止します...")
        finally:
            if 'input_stream' in locals():
                input_stream.stop()
                input_stream.close()
            if 'blackhole_stream' in locals():
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
                    recording = np.concatenate(frames)

                    if recording.ndim > 1 and recording.shape[1] > 1:
                        recording = np.mean(recording, axis=1)

                    sf.write(filepath, recording, sample_rate)
                    print(f"録音が完了しました。")
                    print(f"保存先: {filepath}")
                    return filepath

                except Exception as e:
                    print(f"\n録音データの処理中にエラーが発生しました: {str(e)}")
                    return None
            else:
                print("\nエラー: 録音データが空です。")
                return None