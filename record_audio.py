#!/usr/bin/env python3
import sounddevice as sd
import soundfile as sf
import numpy as np
import argparse
from datetime import datetime
import os
import time

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

def record_audio(duration, filename=None, sample_rate=44100):
    """
    マイクとシステムオーディオを同時に録音
    
    Parameters:
    - duration: 録音時間（秒）
    - filename: 保存するファイル名（指定がない場合は日時から自動生成）
    - sample_rate: サンプリングレート（デフォルト44.1kHz）
    """
    if filename is None:
        filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    
    # BlackHoleデバイスを検索
    blackhole_idx = find_blackhole_device()
    if blackhole_idx is None:
        print("エラー: BlackHoleデバイスが見つかりません。")
        print("システムの音声設定でBlackHoleが正しく設定されているか確認してください。")
        return

    # デフォルトのマイク入力デバイスを使用
    mic_idx = sd.default.device[0]
    
    # 録音チャンネル数（ステレオ）
    channels = 2
    
    try:
        # マイク入力の録音ストリーム
        mic_stream = sd.InputStream(
            device=mic_idx,
            channels=channels,
            samplerate=sample_rate
        )
        
        # システムオーディオ（BlackHole）の録音ストリーム
        system_stream = sd.InputStream(
            device=blackhole_idx,
            channels=channels,
            samplerate=sample_rate
        )
        
        # 録音データを格納する配列
        mic_data = []
        system_data = []
        
        print(f"録音を開始します... {duration}秒間")
        print("Ctrl+Cで録音を停止")
        
        # ストリームを開始
        mic_stream.start()
        system_stream.start()
        
        # 録音
        start_time = time.time()
        try:
            while (time.time() - start_time) < duration:
                # マイクからの入力を読み取り
                mic_frames, _ = mic_stream.read(1024)
                mic_data.append(mic_frames.copy())
                
                # システムオーディオを読み取り
                system_frames, _ = system_stream.read(1024)
                system_data.append(system_frames.copy())
                
        except KeyboardInterrupt:
            print("\n録音を停止します...")
        
        # ストリームを停止
        mic_stream.stop()
        system_stream.stop()
        
        # データを結合
        mic_data = np.concatenate(mic_data)
        system_data = np.concatenate(system_data)
        
        # マイクとシステムオーディオを合成（単純な加算とボリューム調整）
        combined_audio = (mic_data + system_data) * 0.5
        
        # 録音データをファイルに保存
        sf.write(filename, combined_audio, sample_rate)
        print(f"録音が完了しました。ファイル名: {filename}")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
    finally:
        # ストリームを閉じる
        mic_stream.close()
        system_stream.close()

def main():
    parser = argparse.ArgumentParser(description='オーディオ録音スクリプト')
    parser.add_argument('-l', '--list', action='store_true',
                      help='利用可能なオーディオデバイスを表示')
    parser.add_argument('-d', '--duration', type=float, default=10.0,
                      help='録音時間（秒）')
    parser.add_argument('-f', '--filename', type=str,
                      help='保存するファイル名')
    parser.add_argument('-r', '--rate', type=int, default=44100,
                      help='サンプリングレート（Hz）')
    
    args = parser.parse_args()
    
    if args.list:
        list_devices()
        return
    
    record_audio(args.duration, args.filename, args.rate)

if __name__ == "__main__":
    main()