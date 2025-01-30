import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from datetime import datetime
import os
from src.audio.recorder import AudioRecorder

class TestAudioRecorder(unittest.TestCase):
    def setUp(self):
        self.recordings_dir = "test_recordings"
        self.recorder = AudioRecorder(self.recordings_dir)
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

    def tearDown(self):
        # テスト用ディレクトリの削除
        if os.path.exists(self.recordings_dir):
            for file in os.listdir(self.recordings_dir):
                os.remove(os.path.join(self.recordings_dir, file))
            os.rmdir(self.recordings_dir)

    def test_list_devices(self):
        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            devices = self.recorder.list_devices()
            self.assertEqual(devices, self.mock_devices)

    def test_find_blackhole_device_found(self):
        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            idx, device = self.recorder.find_blackhole_device()
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
            idx, device = self.recorder.find_blackhole_device()
            self.assertIsNone(idx)
            self.assertIsNone(device)

    def test_validate_input_device_valid(self):
        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            is_valid, error = self.recorder.validate_input_device(0)
            self.assertTrue(is_valid)
            self.assertIsNone(error)

    def test_validate_input_device_invalid_id(self):
        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            is_valid, error = self.recorder.validate_input_device(len(self.mock_devices))
            self.assertFalse(is_valid)
            self.assertEqual(error, "有効な入力デバイスIDを指定してください。")

    def test_validate_input_device_non_input_device(self):
        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            is_valid, error = self.recorder.validate_input_device(2)
            self.assertFalse(is_valid)
            self.assertEqual(error, "デバイス 2 は入力デバイスではありません。")

    @patch('sounddevice.InputStream')
    @patch('builtins.input', return_value='')
    @patch('soundfile.write')
    @patch('time.time')
    def test_record_filename_format(self, mock_time, mock_write, mock_input, mock_input_stream):
        """ファイル名のフォーマットをテスト"""
        # 録音時間をモック
        mock_time.side_effect = [0, 1.0]  # 開始時間と終了時間

        # テスト用のデータを作成
        mock_input_data = np.ones((1024, 2)) * 0.5
        mock_blackhole_data = np.ones((1024, 2)) * 0.3

        # ストリーム設定
        mock_input_device_stream = MagicMock()
        mock_blackhole_stream = MagicMock()
        mock_input_device_stream.read.side_effect = [(mock_input_data, None), KeyboardInterrupt]
        mock_blackhole_stream.read.side_effect = [(mock_blackhole_data, None)]

        mock_input_stream.side_effect = [mock_input_device_stream, mock_blackhole_stream]

        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch('datetime.datetime') as mock_datetime:
            # 日付を固定
            mock_datetime.now.return_value = datetime(2025, 1, 30)
            
            # カスタムファイル名でテスト
            result = self.recorder.record(filename="テスト会議", input_device_id=0)
            self.assertIsNotNone(result)
            # ファイル名が正しいフォーマットになっているか確認
            self.assertTrue(mock_write.call_args[0][0].endswith("20250130_テスト会議.wav"))

            # ファイル名なしでテスト
            result = self.recorder.record(input_device_id=0)
            self.assertIsNotNone(result)
            # ファイル名が日付のみになっているか確認
            self.assertTrue(mock_write.call_args[0][0].endswith("20250130.wav"))

    @patch('sounddevice.InputStream')
    @patch('builtins.input', return_value='')
    @patch('soundfile.write')
    @patch('time.time')
    def test_record_with_valid_duration(self, mock_time, mock_write, mock_input, mock_input_stream):
        # 録音時間をモック
        mock_time.side_effect = [0, self.recorder.min_recording_duration + 1]

        # ストリームのモック設定
        mock_input_device_stream = MagicMock()
        mock_blackhole_stream = MagicMock()
        
        mock_input_data = np.ones((1024, 2)) * 0.5
        mock_blackhole_data = np.ones((1024, 2)) * 0.3
        
        mock_input_device_stream.read.side_effect = [(mock_input_data, None), KeyboardInterrupt]
        mock_blackhole_stream.read.return_value = (mock_blackhole_data, None)
        
        mock_input_stream.side_effect = [mock_input_device_stream, mock_blackhole_stream]

        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            result = self.recorder.record(input_device_id=0)
            
        self.assertIsNotNone(result)
        mock_write.assert_called_once()

    @patch('sounddevice.InputStream')
    @patch('builtins.input', return_value='')
    @patch('soundfile.write')
    @patch('time.time')
    def test_record_with_too_short_duration(self, mock_time, mock_write, mock_input, mock_input_stream):
        # 録音時間をモック（最小録音時間未満）
        mock_time.side_effect = [0, self.recorder.min_recording_duration / 2]

        # ストリームのモック設定
        mock_input_device_stream = MagicMock()
        mock_blackhole_stream = MagicMock()
        
        mock_input_data = np.ones((1024, 2)) * 0.5
        mock_blackhole_data = np.ones((1024, 2)) * 0.3
        
        mock_input_device_stream.read.side_effect = [(mock_input_data, None), KeyboardInterrupt]
        mock_blackhole_stream.read.return_value = (mock_blackhole_data, None)
        
        mock_input_stream.side_effect = [mock_input_device_stream, mock_blackhole_stream]

        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch('builtins.print') as mock_print:
            result = self.recorder.record(input_device_id=0)
            
        self.assertIsNone(result)
        mock_write.assert_not_called()
        mock_print.assert_any_call(f"\nエラー: 録音時間が短すぎます（{self.recorder.min_recording_duration/2:.2f}秒）")

    @patch('sounddevice.InputStream')
    @patch('builtins.input', return_value='')
    @patch('soundfile.write')
    def test_record_with_empty_frames(self, mock_write, mock_input, mock_input_stream):
        # ストリームのモック設定
        mock_input_device_stream = MagicMock()
        mock_blackhole_stream = MagicMock()
        
        mock_input_stream.side_effect = [mock_input_device_stream, mock_blackhole_stream]

        # すぐにKeyboardInterruptを発生させて空のフレームリストを作成
        mock_input_device_stream.read.side_effect = KeyboardInterrupt

        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch('builtins.print') as mock_print:
            result = self.recorder.record(input_device_id=0)
            
        self.assertIsNone(result)
        mock_write.assert_not_called()
        mock_print.assert_any_call("\nエラー: 録音データが空です。")

    def test_record_no_blackhole(self):
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
            self.recorder.record(input_device_id=0)
            mock_print.assert_any_call("\nエラー: BlackHoleデバイスが見つかりません。")

if __name__ == '__main__':
    unittest.main()