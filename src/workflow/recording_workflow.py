#!/usr/bin/env python
import os
from typing import Optional
from src.audio.recorder import AudioRecorder
from src.transcribe import process_single_file

class RecordingWorkflow:
    """録音から文字起こしまでのワークフローを管理するクラス"""
    
    def __init__(self):
        """ワークフローの初期化"""
        self.recorder = AudioRecorder(
            recordings_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'recordings')
        )

    def select_input_device(self) -> Optional[int]:
        """
        ユーザーに入力デバイスを選択させる
        
        Returns:
        - Optional[int]: 選択されたデバイスID。キャンセル時はNone
        """
        devices = self.recorder.list_devices()
        
        while True:
            try:
                device_id = int(input("\n使用する入力デバイスのIDを入力してください: "))
                if 0 <= device_id < len(devices):
                    return device_id
                print("無効なデバイスIDです。もう一度入力してください。")
            except ValueError:
                print("数値を入力してください。")

    def get_filename(self, default_filename: Optional[str] = None) -> str:
        """
        ファイル名を取得する
        
        Parameters:
        - default_filename: デフォルトのファイル名（指定がある場合）
        
        Returns:
        - str: 使用するファイル名
        """
        if default_filename:
            return default_filename
        
        return input("\n録音ファイルの名前を入力してください（拡張子.wavは自動的に追加されます）: ").strip()

    def execute(self, filename: Optional[str] = None, sample_rate: int = 48000,
                skip_transcribe: bool = False) -> bool:
        """
        録音から文字起こしまでのワークフローを実行
        
        Parameters:
        - filename: 保存するファイル名（オプション）
        - sample_rate: サンプリングレート
        - skip_transcribe: 文字起こしをスキップするかどうか
        
        Returns:
        - bool: ワークフローが正常に完了したかどうか
        """
        # 入力デバイスの選択
        device_id = self.select_input_device()
        if device_id is None:
            return False

        # ファイル名の取得
        filename = self.get_filename(filename)
        
        # 録音の実行
        audio_file = self.recorder.record(filename, sample_rate, device_id)
        if not audio_file:
            return False
            
        # 文字起こしの実行（スキップが指定されていない場合）
        if not skip_transcribe:
            print("\n文字起こしを開始します...")
            try:
                output_file = process_single_file(audio_file)
                print(f"文字起こしが完了しました。")
                print(f"出力ファイル: {output_file}")
            except Exception as e:
                print(f"文字起こし中にエラーが発生しました: {str(e)}")
                return False
                
        return True