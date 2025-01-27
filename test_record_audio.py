import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import os
from record_audio import record_audio, find_blackhole_device, find_macbook_mic

class TestRecordAudio(unittest.TestCase):
    @patch('sounddevice.rec')
    @patch('sounddevice.wait')
    @patch('sounddevice.stop')
    @patch('sounddevice.get_stream')
    @patch('soundfile.write')
    def test_record_audio_with_keyboard_interrupt(self, mock_sf_write, mock_get_stream, 
                                                mock_stop, mock_wait, mock_rec):
        # モックの設定
        mock_stream = MagicMock()
        mock_get_stream.return_value = mock_stream
        mock_stream.active = True

        # 録音データのモック
        mock_rec.side_effect = [
            np.zeros((1000, 1)),  # マイク録音
            np.zeros((1000, 2))   # システム音声
        ]

        # KeyboardInterruptをシミュレート
        def side_effect(*args, **kwargs):
            raise KeyboardInterrupt
        mock_stream.active = side_effect

        # テスト実行
        with patch('record_audio.find_blackhole_device', return_value=1), \
             patch('record_audio.find_macbook_mic', return_value=0):
            record_audio()

        # 録音が開始されたことを確認
        self.assertEqual(mock_rec.call_count, 2)
        
        # 録音が停止されたことを確認
        mock_stop.assert_called_once()
        
        # ファイルが保存されたことを確認
        mock_sf_write.assert_called_once()

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