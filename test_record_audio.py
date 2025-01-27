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
        mock_stream = MagicMock()
        
        # read メソッドが呼ばれたときのデータを設定
        mock_data = np.zeros((1024, 2))
        mock_stream.read.return_value = (mock_data, None)
        
        # InputStream が呼ばれたときにモックを返すように設定
        mock_input_stream.return_value = mock_stream

        # 2回目のループで KeyboardInterrupt を発生させる
        mock_stream.read.side_effect = [
            (mock_data, None),
            KeyboardInterrupt
        ]

        # テスト実行
        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            record_audio()

        # ストリームが正しく開始・停止されたことを確認
        mock_stream.start.assert_called_once()
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()

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
            record_audio()
            mock_print.assert_any_call("\nエラー: BlackHoleデバイスが見つかりません。")

    def test_main_function(self):
        with patch('record_audio.list_devices') as mock_list_devices, \
             patch('record_audio.record_audio') as mock_record_audio, \
             patch('argparse.ArgumentParser.parse_args') as mock_args:
            
            mock_args.return_value = MagicMock(filename=None, rate=48000)
            mock_list_devices.return_value = self.mock_devices
            
            from record_audio import main
            main()
            
            # list_devicesとrecord_audioが呼び出されたことを確認
            mock_list_devices.assert_called_once()
            mock_record_audio.assert_called_once_with(None, 48000)

if __name__ == '__main__':
    unittest.main()