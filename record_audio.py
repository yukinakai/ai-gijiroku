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

def print_progress(elapsed_time):
    """録音の経過時間を表示"""
    sys.stdout.write('\r')
    sys.stdout.write(f"録音時間: {elapsed_time:.1f}秒 ")
    sys.stdout.flush()

def record_audio(filename=None, sample_rate=48000):
    """
    マイクとシステムオーディオを同時に録音
    
    Parameters:
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

    # 十分に長い録音時間を設定（24時間）
    max_duration = 24 * 60 * 60  # 24時間
    num_samples = int(max_duration * sample_rate)
    
    try:
        print("\n録音を開始します...")
        print("Ctrl+Cで録音を停止")
        print("経過時間:")

        # 両方のデバイスから同時に録音を開始
        mic_recording = sd.rec(num_samples, samplerate=sample_rate, channels=1, device=mic_idx)
        system_recording = sd.rec(num_samples, samplerate=sample_rate, channels=2, device=blackhole_idx)
        
        # 進行状況の表示
        start_time = time.time()
        try:
            while sd.get_stream().active:
                current_time = time.time() - start_time
                print_progress(current_time)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n録音を停止します...")
            sd.stop()
        
        # 録音完了まで待機
        sd.wait()
        
        print("\n録音処理中...")
        
        # 実際に録音されたサンプル数を取得
        actual_samples = len(mic_recording)
        
        # マイク入力をステレオに変換
        mic_stereo = np.column_stack((mic_recording[:actual_samples], mic_recording[:actual_samples]))
        
        # システム音声も同じ長さに切り詰める
        system_recording = system_recording[:actual_samples]
        
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
    parser.add_argument('-f', '--filename', type=str,
                      help='保存するファイル名')
    parser.add_argument('-r', '--rate', type=int, default=48000,
                      help='サンプリングレート（Hz）')
    
    args = parser.parse_args()
    
    if args.list:
        list_devices()
        return
    
    record_audio(args.filename, args.rate)

if __name__ == "__main__":
    main()