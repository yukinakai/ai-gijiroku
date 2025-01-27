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
    return devices

def select_device(devices):
    """
    ユーザーにデバイスを選択させる
    
    Parameters:
    - devices: デバイス一覧
    
    Returns:
    - 選択されたデバイスのインデックス
    """
    while True:
        try:
            device_idx = int(input("\n録音するデバイスの番号を入力してください: "))
            if 0 <= device_idx < len(devices):
                device = devices[device_idx]
                if device['max_input_channels'] == 0:
                    print("エラー: 選択されたデバイスは入力に対応していません。")
                    continue
                return device_idx
            else:
                print("エラー: 無効なデバイス番号です。")
        except ValueError:
            print("エラー: 数値を入力してください。")

def print_progress(elapsed_time):
    """録音の経過時間を表示"""
    sys.stdout.write('\r')
    sys.stdout.write(f"録音時間: {elapsed_time:.1f}秒 ")
    sys.stdout.flush()

def record_audio(filename=None, sample_rate=48000, device_idx=None):
    """
    オーディオを録音
    
    Parameters:
    - filename: 保存するファイル名（指定がない場合は日時から自動生成）
    - sample_rate: サンプリングレート（デフォルト48kHz）
    - device_idx: 録音デバイスのインデックス
    """
    # recordingsディレクトリが存在しない場合は作成
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    
    if filename is None:
        filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    
    # ファイルパスを生成（recordingsディレクトリ内に保存）
    filepath = os.path.join(RECORDINGS_DIR, filename)

    # デバイス情報を取得
    devices = sd.query_devices()
    device = devices[device_idx]
    channels = device['max_input_channels']

    print(f"\n使用するデバイス:")
    print(f"デバイス: {device['name']}")
    print(f"保存先: {filepath}")

    # 録音データを格納するリスト
    frames = []
    
    try:
        print("\n録音を開始します...")
        print("Ctrl+Cで録音を停止")
        print("経過時間:")

        # ストリームを開く
        stream = sd.InputStream(device=device_idx, channels=channels, samplerate=sample_rate, callback=None)
        stream.start()

        # 録音開始時間
        start_time = time.time()

        while True:
            # チャンクサイズ分のデータを読み取り
            data = stream.read(1024)[0]
            frames.append(data)
            
            # 経過時間を表示
            current_time = time.time() - start_time
            print_progress(current_time)

    except KeyboardInterrupt:
        print("\n録音を停止します...")
    finally:
        # ストリームを停止・クローズ
        if 'stream' in locals():
            stream.stop()
            stream.close()

        if frames:
            print("\n録音処理中...")
            
            try:
                # 録音データを numpy 配列に変換
                recording = np.concatenate(frames)

                # 録音データをファイルに保存
                sf.write(filepath, recording, sample_rate)
                print(f"録音が完了しました。")
                print(f"保存先: {filepath}")

            except Exception as e:
                print(f"\n録音データの処理中にエラーが発生しました: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='オーディオ録音スクリプト')
    parser.add_argument('-f', '--filename', type=str,
                      help='保存するファイル名')
    parser.add_argument('-r', '--rate', type=int, default=48000,
                      help='サンプリングレート（Hz）')
    
    args = parser.parse_args()
    
    # デバイス一覧を表示
    devices = list_devices()
    
    # デバイスの選択
    device_idx = select_device(devices)
    
    record_audio(args.filename, args.rate, device_idx)

if __name__ == "__main__":
    main()