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

def find_blackhole_device():
    """BlackHoleデバイスのインデックスを検索"""
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if 'BlackHole' in device['name']:
            return i, device
    return None, None

def print_progress(elapsed_time):
    """録音の経過時間を表示"""
    sys.stdout.write('\r')
    sys.stdout.write(f"録音時間: {elapsed_time:.1f}秒 ")
    sys.stdout.flush()

def record_audio(filename=None, sample_rate=48000):
    """
    BlackHoleを使用してオーディオを録音
    
    Parameters:
    - filename: 保存するファイル名（指定がない場合は日時から自動生成）
    - sample_rate: サンプリングレート（デフォルト48kHz）
    """
    # BlackHoleデバイスを検索
    blackhole_idx, blackhole_device = find_blackhole_device()
    if blackhole_idx is None:
        print("\nエラー: BlackHoleデバイスが見つかりません。")
        print("1. BlackHoleがインストールされているか確認してください。")
        print("2. システム環境設定 > サウンド で BlackHole 2chが表示されているか確認してください。")
        return

    # recordingsディレクトリが存在しない場合は作成
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    
    if filename is None:
        filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    
    # ファイルパスを生成（recordingsディレクトリ内に保存）
    filepath = os.path.join(RECORDINGS_DIR, filename)

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

    # 録音データを格納するリスト
    frames = []
    
    try:
        print("\n録音を開始します...")
        print("Ctrl+Cで録音を停止")
        print("経過時間:")

        # ストリームを開く
        stream = sd.InputStream(
            device=blackhole_idx,
            channels=blackhole_device['max_input_channels'],
            samplerate=sample_rate,
            callback=None
        )
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
    list_devices()
    
    # BlackHoleを使用して録音
    record_audio(args.filename, args.rate)

if __name__ == "__main__":
    main()