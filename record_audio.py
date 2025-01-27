#!/Users/carat_yuki/.pyenv/versions/ai-gijiroku/bin/python
import sounddevice as sd
import soundfile as sf
import numpy as np
import argparse
from datetime import datetime
import os
import time
import sys
from transcribe import process_single_file

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

def record_audio(filename=None, sample_rate=48000, input_device_id=None):
    """
    指定された入力デバイスとBlackHoleを使用してオーディオを録音
    
    Parameters:
    - filename: 保存するファイル名（指定がない場合は日時から自動生成）
    - sample_rate: サンプリングレート（デフォルト48kHz）
    - input_device_id: 入力デバイスのID
    """
    # 入力デバイスの確認
    devices = sd.query_devices()
    if input_device_id is None or input_device_id >= len(devices):
        print("\nエラー: 有効な入力デバイスIDを指定してください。")
        return

    # BlackHoleデバイスを検索
    blackhole_idx, blackhole_device = find_blackhole_device()
    if blackhole_idx is None:
        print("\nエラー: BlackHoleデバイスが見つかりません。")
        print("1. BlackHoleがインストールされているか確認してください。")
        print("2. システム環境設定 > サウンド で BlackHole 2chが表示されているか確認してください。")
        return

    input_device = devices[input_device_id]
    if input_device['max_input_channels'] == 0:
        print(f"\nエラー: デバイス {input_device_id} は入力デバイスではありません。")
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

        # 入力デバイスのストリームを開く
        input_stream = sd.InputStream(
            device=input_device_id,
            channels=input_device['max_input_channels'],
            samplerate=sample_rate,
            callback=None
        )
        
        # BlackHoleのストリームを開く
        blackhole_stream = sd.InputStream(
            device=blackhole_idx,
            channels=blackhole_device['max_input_channels'],
            samplerate=sample_rate,
            callback=None
        )

        input_stream.start()
        blackhole_stream.start()

        # 録音開始時間
        start_time = time.time()

        while True:
            # 両方のデバイスからデータを読み取り
            input_data = input_stream.read(1024)[0]
            blackhole_data = blackhole_stream.read(1024)[0]
            
            # 両方のデータをミックス
            # 入力デバイスとBlackHoleのチャンネル数を合わせる
            if input_data.shape[1] != blackhole_data.shape[1]:
                # チャンネル数の少ない方に合わせる
                min_channels = min(input_data.shape[1], blackhole_data.shape[1])
                input_data = input_data[:, :min_channels]
                blackhole_data = blackhole_data[:, :min_channels]
            
            # 音声をミックス（加算）して音量を調整
            combined_data = (input_data + blackhole_data) / 2
            frames.append(combined_data)
            
            # 経過時間を表示
            current_time = time.time() - start_time
            print_progress(current_time)

    except KeyboardInterrupt:
        print("\n録音を停止します...")
    finally:
        # ストリームを停止・クローズ
        if 'input_stream' in locals():
            input_stream.stop()
            input_stream.close()
        if 'blackhole_stream' in locals():
            blackhole_stream.stop()
            blackhole_stream.close()

        if frames:
            print("\n録音処理中...")
            
            try:
                # 録音データを numpy 配列に変換
                recording = np.concatenate(frames)

                # チャンネル数を確認し、必要に応じてモノラルに変換
                if recording.ndim > 1 and recording.shape[1] > 1:
                    # ステレオの場合は両チャンネルの平均を取ってモノラルに変換
                    recording = np.mean(recording, axis=1)

                # 録音データをファイルに保存（モノラルとして保存）
                sf.write(filepath, recording, sample_rate)
                print(f"録音が完了しました。")
                print(f"保存先: {filepath}")
                return filepath

            except Exception as e:
                print(f"\n録音データの処理中にエラーが発生しました: {str(e)}")
                return None

def main():
    parser = argparse.ArgumentParser(description='オーディオ録音スクリプト')
    parser.add_argument('-f', '--filename', type=str,
                       help='保存するファイル名')
    parser.add_argument('-r', '--rate', type=int, default=48000,
                       help='サンプリングレート（Hz）')
    parser.add_argument('--no-transcribe', action='store_true',
                       help='文字起こしをスキップする')
    
    args = parser.parse_args()
    
    # デバイス一覧を表示
    devices = list_devices()
    
    # ユーザーに入力デバイスの選択を求める
    while True:
        try:
            device_id = int(input("\n使用する入力デバイスのIDを入力してください: "))
            if 0 <= device_id < len(devices):
                break
            print("無効なデバイスIDです。もう一度入力してください。")
        except ValueError:
            print("数値を入力してください。")
    
    # 選択された入力デバイスとBlackHoleを使用して録音
    audio_file = record_audio(args.filename, args.rate, device_id)
    
    if audio_file and not args.no_transcribe:
        print("\n文字起こしを開始します...")
        try:
            output_file = process_single_file(audio_file)
            print(f"文字起こしが完了しました。")
            print(f"出力ファイル: {output_file}")
        except Exception as e:
            print(f"文字起こし中にエラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main()