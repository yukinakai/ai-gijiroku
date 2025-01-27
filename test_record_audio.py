import unittest
from unittest.mock import patch, MagicMock, call
import numpy as np
import os
from record_audio import record_audio, list_devices, find_blackhole_device
from io import StringIO

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
    def test_record_audio_with_keyboard_interrupt(self, mock_input, mock_input_stream):
        # ストリームのモック設定
        mock_input_device_stream = MagicMock()
        mock_blackhole_stream = MagicMock()
        
        # read メソッドが呼ばれたときのデータを設定
        mock_data = np.zeros((1024, 2))
        mock_input_device_stream.read.return_value = (mock_data, None)
        mock_blackhole_stream.read.return_value = (mock_data, None)
        
        # InputStream が呼ばれたときに異なるモックを返すように設定
        mock_input_stream.side_effect = [mock_input_device_stream, mock_blackhole_stream]

        # 2回目のループで KeyboardInterrupt を発生させる
        mock_input_device_stream.read.side_effect = [
            (mock_data, None),
            KeyboardInterrupt
        ]

        # テスト実行
        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            record_audio(input_device_id=0)

        # 両方のストリームが正しく開始・停止されたことを確認
        mock_input_device_stream.start.assert_called_once()
        mock_input_device_stream.stop.assert_called_once()
        mock_input_device_stream.close.assert_called_once()
        mock_blackhole_stream.start.assert_called_once()
        mock_blackhole_stream.stop.assert_called_once()
        mock_blackhole_stream.close.assert_called_once()

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

    def test_main_function(self):
        with patch('record_audio.list_devices') as mock_list_devices, \
             patch('record_audio.record_audio') as mock_record_audio, \
             patch('argparse.ArgumentParser.parse_args') as mock_args, \
             patch('builtins.input', return_value='0') as mock_input:
            
            mock_args.return_value = MagicMock(
                filename=None,
                rate=48000
            )
            mock_list_devices.return_value = self.mock_devices
            
            from record_audio import main
            main()
            
            # list_devicesとrecord_audioが呼び出されたことを確認
            mock_list_devices.assert_called_once()
            mock_record_audio.assert_called_once_with(None, 48000, 0)
            mock_input.assert_called_once()

if __name__ == '__main__':
    unittest.main()