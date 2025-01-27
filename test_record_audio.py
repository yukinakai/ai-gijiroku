import unittest
from unittest.mock import patch, MagicMock, call
import numpy as np
import os
from record_audio import record_audio, list_devices, select_device
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
                'name': 'Device 2',
                'max_input_channels': 2,
                'max_output_channels': 0,  # 出力チャンネルなし
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

    def test_select_device_valid_input(self):
        with patch('builtins.input', return_value='0'), \
             patch('builtins.print') as mock_print:
            selected = select_device(self.mock_devices)
            self.assertEqual(selected, 0)

    def test_select_device_invalid_then_valid_input(self):
        with patch('builtins.input', side_effect=['invalid', '0']), \
             patch('builtins.print') as mock_print:
            selected = select_device(self.mock_devices)
            self.assertEqual(selected, 0)

    def test_select_device_out_of_range_then_valid_input(self):
        with patch('builtins.input', side_effect=['5', '0']), \
             patch('builtins.print') as mock_print:
            selected = select_device(self.mock_devices)
            self.assertEqual(selected, 0)

    def test_select_device_no_output_channels(self):
        with patch('builtins.input', side_effect=['1', '0']), \
             patch('builtins.print') as mock_print:
            selected = select_device(self.mock_devices)
            self.assertEqual(selected, 0)
            mock_print.assert_any_call("エラー: 選択されたデバイスは出力に対応していません。")

    @patch('sounddevice.InputStream')
    def test_record_audio_with_keyboard_interrupt(self, mock_input_stream):
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
            record_audio(device_idx=0)

        # ストリームが正しく開始・停止されたことを確認
        mock_stream.start.assert_called_once()
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()

    def test_main_function(self):
        with patch('record_audio.list_devices', return_value=self.mock_devices), \
             patch('record_audio.select_device', return_value=0), \
             patch('record_audio.record_audio') as mock_record_audio, \
             patch('argparse.ArgumentParser.parse_args') as mock_args:
            
            mock_args.return_value = MagicMock(filename=None, rate=48000)
            
            from record_audio import main
            main()
            
            # record_audioが正しいパラメータで呼び出されたことを確認
            mock_record_audio.assert_called_once_with(None, 48000, 0)

if __name__ == '__main__':
    unittest.main()