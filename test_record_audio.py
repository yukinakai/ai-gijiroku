import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import os
from record_audio import record_audio, find_blackhole_device, find_macbook_mic

class TestRecordAudio(unittest.TestCase):
    @patch('sounddevice.InputStream')
    def test_record_audio_with_keyboard_interrupt(self, mock_input_stream):
        # ストリームのモック設定
        mock_mic_stream = MagicMock()
        mock_system_stream = MagicMock()
        
        # read メソッドが呼ばれたときのデータを設定
        mock_mic_data = np.zeros((1024, 1))
        mock_system_data = np.zeros((1024, 2))
        mock_mic_stream.read.return_value = (mock_mic_data, None)
        mock_system_stream.read.return_value = (mock_system_data, None)
        
        # InputStream が呼ばれたときに異なるモックを返すように設定
        mock_input_stream.side_effect = [mock_mic_stream, mock_system_stream]

        # 2回目のループで KeyboardInterrupt を発生させる
        mock_mic_stream.read.side_effect = [
            (mock_mic_data, None),
            KeyboardInterrupt
        ]

        # テスト実行
        with patch('record_audio.find_blackhole_device', return_value=1), \
             patch('record_audio.find_macbook_mic', return_value=0):
            record_audio()

        # ストリームが正しく開始・停止されたことを確認
        mock_mic_stream.start.assert_called_once()
        mock_system_stream.start.assert_called_once()
        mock_mic_stream.stop.assert_called_once()
        mock_system_stream.stop.assert_called_once()
        mock_mic_stream.close.assert_called_once()
        mock_system_stream.close.assert_called_once()

    def test_find_blackhole_device(self):
        with patch('sounddevice.query_devices', return_value=[
            {'name': 'Device 1'},
            {'name': 'BlackHole 2ch'},
            {'name': 'Device 3'}
        ]):
            device_idx = find_blackhole_device()
            self.assertEqual(device_idx, 1)

    def test_find_macbook_mic(self):
        with patch('sounddevice.query_devices', return_value=[
            {'name': 'Device 1'},
            {'name': 'MacBook Air マイク'},
            {'name': 'Device 3'}
        ]):
            device_idx = find_macbook_mic()
            self.assertEqual(device_idx, 1)

    def test_no_blackhole_device(self):
        with patch('sounddevice.query_devices', return_value=[
            {'name': 'Device 1'},
            {'name': 'Device 2'}
        ]):
            device_idx = find_blackhole_device()
            self.assertIsNone(device_idx)

    def test_no_macbook_mic(self):
        with patch('sounddevice.query_devices', return_value=[
            {'name': 'Device 1'},
            {'name': 'Device 2'}
        ]):
            device_idx = find_macbook_mic()
            self.assertIsNone(device_idx)

if __name__ == '__main__':
    unittest.main()