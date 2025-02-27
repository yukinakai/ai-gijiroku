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