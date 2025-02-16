import unittest
from unittest.mock import patch, MagicMock, call
import numpy as np
from datetime import datetime
from src.functions.recorder import AudioRecorder

class TestAudioRecorder(unittest.TestCase):
    def setUp(self):
        self.recordings_dir = "test_recordings"
        self.min_recording_duration = 0.5
        self.recorder = AudioRecorder(self.recordings_dir, self.min_recording_duration)
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
            devices = AudioRecorder.list_devices()
            self.assertEqual(devices, self.mock_devices)

    def test_find_blackhole_device_found(self):
        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            idx, device = AudioRecorder.find_blackhole_device()
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
            idx, device = AudioRecorder.find_blackhole_device()
            self.assertIsNone(idx)
            self.assertIsNone(device)

    @patch('sounddevice.InputStream')
    @patch('builtins.input', return_value='')
    @patch('soundfile.write')
    @patch('time.time')
    def test_record_filename_format(self, mock_time, mock_write, mock_input, mock_input_stream):
        """ファイル名のフォーマットをテスト"""
        # 録音時間をモック
        mock_time.side_effect = [0, 0.5, 1.0, 1.5, 2.0]

        # テスト用のデータを作成
        mock_input_data = np.ones((1024, 2)) * 0.5
        mock_blackhole_data = np.ones((1024, 2)) * 0.3

        # ストリーム設定
        mock_input_device_stream = MagicMock()
        mock_blackhole_stream = MagicMock()

        # read メソッドの設定
        mock_input_device_stream.read.return_value = (mock_input_data, None)
        mock_blackhole_stream.read.return_value = (mock_blackhole_data, None)

        mock_input_stream.side_effect = [mock_input_device_stream, mock_blackhole_stream]

        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch('datetime.datetime', autospec=True) as mock_datetime, \
             patch.object(AudioRecorder, '_is_key_pressed') as mock_key_pressed:
            
            # qキーが押されるまでNoneを返し、その後qを返す
            mock_key_pressed.side_effect = [None, None, 'q']
            
            # 日付を固定
            current_date = datetime.now()
            mock_datetime.now.return_value = current_date
            
            # カスタムファイル名でテスト
            result = self.recorder.record(filename="テスト会議", input_device_id=0)
            self.assertIsNotNone(result)
            # ファイル名が正しいフォーマットになっているか確認
            expected_filename = f"{current_date.strftime('%Y%m%d')}_テスト会議.wav"
            self.assertTrue(mock_write.call_args[0][0].endswith(expected_filename))

            # ストリームが正しく停止されたことを確認
            mock_input_device_stream.stop.assert_called_once()
            mock_input_device_stream.close.assert_called_once()
            mock_blackhole_stream.stop.assert_called_once()
            mock_blackhole_stream.close.assert_called_once()

    @patch('sounddevice.InputStream')
    @patch('builtins.input', return_value='')
    @patch('soundfile.write')
    @patch('time.time')
    def test_record_with_valid_duration(self, mock_time, mock_write, mock_input, mock_input_stream):
        # 録音時間をモック
        mock_time.side_effect = [0, self.min_recording_duration + 0.1, self.min_recording_duration + 0.2]

        # ストリームのモック設定
        mock_input_device_stream = MagicMock()
        mock_blackhole_stream = MagicMock()
        
        # read メソッドが呼ばれたときのデータを設定
        mock_input_data = np.ones((1024, 2)) * 0.5
        mock_blackhole_data = np.ones((1024, 2)) * 0.3
        
        mock_input_device_stream.read.return_value = (mock_input_data, None)
        mock_blackhole_stream.read.return_value = (mock_blackhole_data, None)
        
        mock_input_stream.side_effect = [mock_input_device_stream, mock_blackhole_stream]

        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch.object(AudioRecorder, '_is_key_pressed') as mock_key_pressed:
            
            # qキーが押されるまでNoneを返し、その後qを返す
            mock_key_pressed.side_effect = [None, 'q']
            
            result = self.recorder.record(input_device_id=0)
            
        self.assertIsNotNone(result)
        mock_write.assert_called_once()

        # ストリームが正しく停止されたことを確認
        mock_input_device_stream.stop.assert_called_once()
        mock_input_device_stream.close.assert_called_once()
        mock_blackhole_stream.stop.assert_called_once()
        mock_blackhole_stream.close.assert_called_once()

    @patch('sounddevice.InputStream')
    @patch('builtins.input', return_value='')
    @patch('soundfile.write')
    @patch('time.time')
    def test_record_with_too_short_duration(self, mock_time, mock_write, mock_input, mock_input_stream):
        # 録音時間をモック（最小録音時間未満）
        mock_time.side_effect = [0, self.min_recording_duration / 2]

        # ストリームのモック設定
        mock_input_device_stream = MagicMock()
        mock_blackhole_stream = MagicMock()
        
        mock_input_data = np.ones((1024, 2)) * 0.5
        mock_blackhole_data = np.ones((1024, 2)) * 0.3
        
        mock_input_device_stream.read.return_value = (mock_input_data, None)
        mock_blackhole_stream.read.return_value = (mock_blackhole_data, None)
        
        mock_input_stream.side_effect = [mock_input_device_stream, mock_blackhole_stream]

        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch.object(AudioRecorder, '_is_key_pressed') as mock_key_pressed, \
             patch('builtins.print') as mock_print:
            
            # すぐにqキーを押す
            mock_key_pressed.return_value = 'q'
            
            result = self.recorder.record(input_device_id=0)
            
        self.assertIsNone(result)
        mock_write.assert_not_called()

        # エラーメッセージの確認
        error_message = f"\nエラー: 録音時間が短すぎます（{self.min_recording_duration/2:.2f}秒）"
        mock_print.assert_any_call(error_message)

        # ストリームが正しく停止されたことを確認
        mock_input_device_stream.stop.assert_called_once()
        mock_input_device_stream.close.assert_called_once()
        mock_blackhole_stream.stop.assert_called_once()
        mock_blackhole_stream.close.assert_called_once()

    @patch('sounddevice.InputStream')
    @patch('builtins.input', return_value='')
    @patch('soundfile.write')
    def test_record_with_empty_frames(self, mock_write, mock_input, mock_input_stream):
        # ストリームのモック設定
        mock_input_device_stream = MagicMock()
        mock_blackhole_stream = MagicMock()
        
        mock_input_stream.side_effect = [mock_input_device_stream, mock_blackhole_stream]

        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch.object(AudioRecorder, '_is_key_pressed') as mock_key_pressed, \
             patch('builtins.print') as mock_print:
            
            # すぐにqキーを押す
            mock_key_pressed.return_value = 'q'
            
            result = self.recorder.record(input_device_id=0)
            
        self.assertIsNone(result)
        mock_write.assert_not_called()
        mock_print.assert_any_call("\nエラー: 録音データが空です。")

        # ストリームが正しく停止されたことを確認
        mock_input_device_stream.stop.assert_called_once()
        mock_input_device_stream.close.assert_called_once()
        mock_blackhole_stream.stop.assert_called_once()
        mock_blackhole_stream.close.assert_called_once()

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
            self.recorder.record(input_device_id=0)  # 有効な入力デバイスIDを指定
            mock_print.assert_any_call("\nエラー: BlackHoleデバイスが見つかりません。")

    def test_record_invalid_device_id(self):
        """無効なデバイスIDを指定した場合のテスト"""
        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch('builtins.print') as mock_print:
            self.recorder.record(input_device_id=len(self.mock_devices))  # 存在しないインデックス
            mock_print.assert_any_call("\nエラー: 有効な入力デバイスIDを指定してください。")

    def test_record_non_input_device(self):
        """入力チャンネルがないデバイスを指定した場合のテスト"""
        with patch('sounddevice.query_devices', return_value=self.mock_devices), \
             patch('builtins.print') as mock_print:
            self.recorder.record(input_device_id=2)  # Device 3 (入力チャンネルなし)
            mock_print.assert_any_call("\nエラー: デバイス 2 は入力デバイスではありません。")

if __name__ == '__main__':
    unittest.main()