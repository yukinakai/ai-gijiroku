#!/Users/carat_yuki/.pyenv/versions/ai-gijiroku/bin/python
import sounddevice as sd
import soundfile as sf
import numpy as np
import argparse
from datetime import datetime
import os
import time
import sys

# 録音ファイルの保存ディレクトリ
RECORDINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recordings')

def list_devices():
    """利用可能なオーディオデバイスを一覧表示"""
    devices = sd.query_devices()
    print("\n利用可能なオーディオデバイス:")
    for i, device in enumerate(devices):
        print(f"\nデバイス {i}:")
        print(f"  名前: {device['name']}")
        print(f"  入力チャンネル: {device['max_input_channels']}")
        print(f"  出力チャンネル: {device['max_output_channels']}")
        print(f"  デフォルトサンプルレート: {device['default_samplerate']}")

def find_blackhole_device():
    """BlackHoleデバイスのインデックスを検索"""
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if 'BlackHole' in device['name']:
            return i
    return None

def find_macbook_mic():
    """MacBook Airのマイクのインデックスを検索"""
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if 'MacBook Air' in device['name'] and 'マイク' in device['name']:
            return i
    return None

def print_progress(current_time, total_time):
    """録音の進行状況を表示"""
    progress = int((current_time / total_time) * 50)
    sys.stdout.write('\r')
    sys.stdout.write(f"[{'=' * progress}{' ' * (50-progress)}] {current_time:.1f}/{total_time:.1f}秒 ")
    sys.stdout.flush()

def record_audio(duration, filename=None, sample_rate=48000):
    """
    マイクとシステムオーディオを同時に録音
    
    Parameters:
    - duration: 録音時間（秒）
    - filename: 保存するファイル名（指定がない場合は日時から自動生成）
    - sample_rate: サンプリングレート（デフォルト48kHz）
    """
    # recordingsディレクトリが存在しない場合は作成
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    
    if filename is None:
        filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    
    # ファイルパスを生成（recordingsディレクトリ内に保存）
    filepath = os.path.join(RECORDINGS_DIR, filename)
    
    # BlackHoleデバイスを検索
    blackhole_idx = find_blackhole_device()
    if blackhole_idx is None:
        print("エラー: BlackHoleデバイスが見つかりません。")
        print("システムの音声設定でBlackHoleが正しく設定されているか確認してください。")
        return

    # MacBook Airのマイクを検索
    mic_idx = find_macbook_mic()
    if mic_idx is None:
        print("エラー: MacBook Airのマイクが見つかりません。")
        return

    print(f"使用するデバイス:")
    print(f"マイク: {sd.query_devices(mic_idx)['name']}")
    print(f"システムオーディオ: {sd.query_devices(blackhole_idx)['name']}")
    print(f"保存先: {filepath}")

    # 録音時間からサンプル数を計算
    num_samples = int(duration * sample_rate)
    
    try:
        print(f"\n録音を開始します... {duration}秒間")
        print("Ctrl+Cで録音を停止")
        print("進行状況:")

        # 両方のデバイスから同時に録音を開始
        mic_recording = sd.rec(num_samples, samplerate=sample_rate, channels=1, device=mic_idx)
        system_recording = sd.rec(num_samples, samplerate=sample_rate, channels=2, device=blackhole_idx)
        
        # 進行状況の表示
        start_time = time.time()
        try:
            while sd.get_stream().active:
                current_time = time.time() - start_time
                if current_time > duration:
                    break
                print_progress(current_time, duration)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n録音を停止します...")
            sd.stop()
            return
        
        # 録音完了まで待機
        sd.wait()
        
        print("\n録音処理中...")
        
        # マイク入力をステレオに変換
        mic_stereo = np.column_stack((mic_recording, mic_recording))
        
        # 音量を調整して合成
        combined_audio = (mic_stereo * 0.5 + system_recording * 0.5)
        
        # 録音データをファイルに保存
        sf.write(filepath, combined_audio, sample_rate)
        print(f"録音が完了しました。")
        print(f"保存先: {filepath}")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='オーディオ録音スクリプト')
    parser.add_argument('-l', '--list', action='store_true',
                      help='利用可能なオーディオデバイスを表示')
    parser.add_argument('-d', '--duration', type=float, default=10.0,
                      help='録音時間（秒）')
    parser.add_argument('-f', '--filename', type=str,
                      help='保存するファイル名')
    parser.add_argument('-r', '--rate', type=int, default=48000,
                      help='サンプリングレート（Hz）')
    
    args = parser.parse_args()
    
    if args.list:
        list_devices()
        return
    
    record_audio(args.duration, args.filename, args.rate)

if __name__ == "__main__":
    main()