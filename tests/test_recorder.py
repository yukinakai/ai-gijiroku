import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from datetime import datetime
from src.functions.recorder import record_audio, list_devices, find_blackhole_device, MIN_RECORDING_DURATION

class TestRecordAudio(unittest.TestCase):
    def setUp(self):
        self.mock_devices = [
            {
                'name': 'Device 1',
                'max_input_channels': 2,
                'max_output_channels': 2,
                'default_samplerate': 48000
            },
            {
                'name': 'BlackHole 2ch',
                'max_input_channels': 2,
                'max_output_channels': 2,
                'default_samplerate': 48000
            },
            {
                'name': 'Device 3',
                'max_input_channels': 0,
                'max_output_channels': 2,
                'default_samplerate': 44100
            }
        ]

    def test_list_devices(self):
        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            devices = list_devices()
            self.assertEqual(devices, self.mock_devices)

    def test_find_blackhole_device_found(self):
        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            idx, device = find_blackhole_device()
            self.assertEqual(idx, 1)
            self.assertEqual(device, self.mock_devices[1])

    def test_find_blackhole_device_not_found(self):
        mock_devices = [
            {
                'name': 'Device 1',
                'max_input_channels': 2,
                'max_output_channels': 2,
                'default_samplerate': 48000
            }
        ]
        with patch('sounddevice.query_devices', return_value=mock_devices):
            idx, device = find_blackhole_device()
            self.assertIsNone(idx)
            self.assertIsNone(device)

    @patch('sounddevice.InputStream')
    @patch('builtins.input', return_value='')
    @patch('soundfile.write')
    @patch('time.time')
    def test_record_audio_filename_format(self, mock_time, mock_write, mock_input, mock_input_stream):
        """ファイル名のフォーマットをテスト"""
        # 録音時間をモック
        mock_time.side_effect = [
            0,  # 1回目開始
            0.5, 1.0, 1.5,  # 1回目ループ
            2.0,  # 1回目終了
            3.0,  # 2回目開始
            3.5, 4.0, 4.5,  # 2回目ループ
            5.0,  # 2回目終了
        ]

        # テスト用のデータを作成
        mock_input_data = np.ones((1024, 2)) * 0.5
        mock_blackhole_data = np.ones((1024, 2)) * 0.3

        # 1回目のストリーム設定
        mock_input_device_stream1 = MagicMock()
        mock_blackhole_stream1 = MagicMock()
        mock_input_device_stream1.read.side_effect = [(mock_input_data, None)] * 3 + [KeyboardInterrupt]
        mock_blackhole_stream1.read.side_effect = [(mock_blackhole_data, None)] * 3

        # 2回目のストリーム設定
        mock_input_device_stream2 = MagicMock()
        mock_blackhole_stream2 = MagicMock()
        mock_input_device_stream2.read.side_effect = [(mock_input_data, None)] * 3 + [KeyboardInterrupt]
        mock_blackhole_stream2.read.side_effect = [(mock_blackhole_data, None)] * 3

        # ストリームの設定
        mock_input_stream.side_effect = [
            mock_input_device_stream1,
            mock_blackhole_stream1,
            mock_input_device_stream2,
            mock_blackhole_stream2
        ]

        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch('datetime.datetime') as mock_datetime:
            # 日付を固定
            mock_datetime.now.return_value = datetime(2025, 1, 30)
            
            # カスタムファイル名でテスト
            result = record_audio(filename="テスト会議", input_device_id=0)
            self.assertIsNotNone(result)
            # ファイル名が正しいフォーマットになっているか確認
            self.assertTrue(mock_write.call_args[0][0].endswith("20250130_テスト会議.wav"))

            # ファイル名なしでテスト
            result = record_audio(input_device_id=0)
            self.assertIsNotNone(result)
            # ファイル名が日付のみになっているか確認
            self.assertTrue(mock_write.call_args[0][0].endswith("20250130.wav"))

    @patch('sounddevice.InputStream')
    @patch('builtins.input', return_value='')
    @patch('soundfile.write')
    @patch('time.time')
    def test_record_audio_with_valid_duration(self, mock_time, mock_write, mock_input, mock_input_stream):
        # 録音時間をモック
        mock_time.side_effect = [0, MIN_RECORDING_DURATION + 1]  # 開始時間と終了時間

        # ストリームのモック設定
        mock_input_device_stream = MagicMock()
        mock_blackhole_stream = MagicMock()
        
        # read メソッドが呼ばれたときのデータを設定
        mock_input_data = np.ones((1024, 2)) * 0.5
        mock_blackhole_data = np.ones((1024, 2)) * 0.3
        
        mock_input_device_stream.read.return_value = (mock_input_data, None)
        mock_blackhole_stream.read.return_value = (mock_blackhole_data, None)
        
        mock_input_stream.side_effect = [mock_input_device_stream, mock_blackhole_stream]

        # 2回目のループで KeyboardInterrupt を発生させる
        mock_input_device_stream.read.side_effect = [
            (mock_input_data, None),
            KeyboardInterrupt
        ]

        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            result = record_audio(input_device_id=0)
            
        self.assertIsNotNone(result)
        mock_write.assert_called_once()

    @patch('sounddevice.InputStream')
    @patch('builtins.input', return_value='')
    @patch('soundfile.write')
    @patch('time.time')
    def test_record_audio_with_too_short_duration(self, mock_time, mock_write, mock_input, mock_input_stream):
        # 録音時間をモック（最小録音時間未満）
        mock_time.side_effect = [0, MIN_RECORDING_DURATION / 2]

        # ストリームのモック設定
        mock_input_device_stream = MagicMock()
        mock_blackhole_stream = MagicMock()
        
        mock_input_data = np.ones((1024, 2)) * 0.5
        mock_blackhole_data = np.ones((1024, 2)) * 0.3
        
        mock_input_device_stream.read.return_value = (mock_input_data, None)
        mock_blackhole_stream.read.return_value = (mock_blackhole_data, None)
        
        mock_input_stream.side_effect = [mock_input_device_stream, mock_blackhole_stream]

        mock_input_device_stream.read.side_effect = [
            (mock_input_data, None),
            KeyboardInterrupt
        ]

        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch('builtins.print') as mock_print:
            result = record_audio(input_device_id=0)
            
        self.assertIsNone(result)
        mock_write.assert_not_called()
        mock_print.assert_any_call(f"\nエラー: 録音時間が短すぎます（{MIN_RECORDING_DURATION/2:.2f}秒）")

    @patch('sounddevice.InputStream')
    @patch('builtins.input', return_value='')
    @patch('soundfile.write')
    def test_record_audio_with_empty_frames(self, mock_write, mock_input, mock_input_stream):
        # ストリームのモック設定
        mock_input_device_stream = MagicMock()
        mock_blackhole_stream = MagicMock()
        
        mock_input_stream.side_effect = [mock_input_device_stream, mock_blackhole_stream]

        # すぐにKeyboardInterruptを発生させて空のフレームリストを作成
        mock_input_device_stream.read.side_effect = KeyboardInterrupt

        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch('builtins.print') as mock_print:
            result = record_audio(input_device_id=0)
            
        self.assertIsNone(result)
        mock_write.assert_not_called()
        mock_print.assert_any_call("\nエラー: 録音データが空です。")

    def test_record_audio_no_blackhole(self):
        mock_devices = [
            {
                'name': 'Device 1',
                'max_input_channels': 2,
                'max_output_channels': 2,
                'default_samplerate': 48000
            }
        ]
        with patch('sounddevice.query_devices', return_value=mock_devices), \
             patch('builtins.print') as mock_print:
            record_audio(input_device_id=0)  # 有効な入力デバイスIDを指定
            mock_print.assert_any_call("\nエラー: BlackHoleデバイスが見つかりません。")

    def test_record_audio_invalid_device_id(self):
        """無効なデバイスIDを指定した場合のテスト"""
        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch('builtins.print') as mock_print:
            record_audio(input_device_id=len(self.mock_devices))  # 存在しないインデックス
            mock_print.assert_any_call("\nエラー: 有効な入力デバイスIDを指定してください。")

    def test_record_audio_non_input_device(self):
        """入力チャンネルがないデバイスを指定した場合のテスト"""
        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch('builtins.print') as mock_print:
            record_audio(input_device_id=2)  # Device 3 (入力チャンネルなし)
            mock_print.assert_any_call("\nエラー: デバイス 2 は入力デバイスではありません。")
    def test_main_function_with_transcribe(self):
        with patch('src.record_audio.list_devices') as mock_list_devices, \
             patch('src.record_audio.record_audio') as mock_record_audio, \
             patch('src.record_audio.process_single_file') as mock_process_single_file, \
             patch('argparse.ArgumentParser.parse_args') as mock_args, \
             patch('builtins.input') as mock_input:
            
            mock_args.return_value = MagicMock(
                filename=None,
                rate=48000,
                no_transcribe=False
            )
            mock_list_devices.return_value = self.mock_devices
            
            # デバイスIDとファイル名の入力をシミュレート
            mock_input.side_effect = ['0', 'テスト会議']
            
            # record_audioが音声ファイルのパスを返すように設定
            mock_audio_path = "recordings/test_audio.wav"
            mock_record_audio.return_value = mock_audio_path
            
            # process_single_fileが文字起こしファイルのパスを返すように設定
            mock_transcript_path = "transcripts/test_audio.txt"
            mock_process_single_file.return_value = mock_transcript_path
            
            from src.functions.recorder import main
            main()
            
            # 各関数が正しく呼び出されたことを確認
            mock_list_devices.assert_called_once()
            mock_record_audio.assert_called_once_with('テスト会議', 48000, 0)
            mock_process_single_file.assert_called_once_with(mock_audio_path)
            self.assertEqual(mock_input.call_count, 2)  # デバイスIDとファイル名の2回の入力

    def test_main_function_without_transcribe(self):
        with patch('src.record_audio.list_devices') as mock_list_devices, \
             patch('src.record_audio.record_audio') as mock_record_audio, \
             patch('src.record_audio.process_single_file') as mock_process_single_file, \
             patch('argparse.ArgumentParser.parse_args') as mock_args, \
             patch('builtins.input') as mock_input:
            
            mock_args.return_value = MagicMock(
                filename=None,
                rate=48000,
                no_transcribe=True
            )
            mock_list_devices.return_value = self.mock_devices
            
            # デバイスIDとファイル名の入力をシミュレート
            mock_input.side_effect = ['0', 'テスト会議']
            
            # record_audioが音声ファイルのパスを返すように設定
            mock_audio_path = "recordings/test_audio.wav"
            mock_record_audio.return_value = mock_audio_path
            
            from src.functions.recorder import main
            main()
            
            # 各関数が正しく呼び出されたことを確認
            mock_list_devices.assert_called_once()
            mock_record_audio.assert_called_once_with('テスト会議', 48000, 0)
            # 文字起こしが呼ばれていないことを確認
            mock_process_single_file.assert_not_called()
            self.assertEqual(mock_input.call_count, 2)  # デバイスIDとファイル名の2回の入力

if __name__ == '__main__':
    unittest.main()