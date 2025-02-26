import os
import psutil
import time
from src.functions.recorder import AudioRecorder

def monitor_memory_usage():
    """現在のプロセスのメモリ使用量を取得"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB単位で返す

def test_recording_memory():
    """録音時のメモリ使用量をモニタリング"""
    recorder = AudioRecorder("test_recordings")
    
    print("メモリ使用量モニタリングを開始します...")
    initial_memory = monitor_memory_usage()
    print(f"初期メモリ使用量: {initial_memory:.2f} MB")
    
    # 5秒ごとにメモリ使用量を記録
    for i in range(6):  # 30秒間
        time.sleep(5)
        current_memory = monitor_memory_usage()
        print(f"経過時間: {i*5}秒, メモリ使用量: {current_memory:.2f} MB, "
              f"差分: {current_memory - initial_memory:.2f} MB")

if __name__ == "__main__":
    test_recording_memory()