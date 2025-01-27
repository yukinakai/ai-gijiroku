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
                'max_input_channels': 0,
                'max_output_channels': 2,
                'default_samplerate': 48000
            },
            {
                'name': 'Device 3',
                'max_input_channels': 2,
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
            selected = select_device(self.mock_devices, "入力")
            self.assertEqual(selected, 0)

    def test_select_device_invalid_then_valid_input(self):
        with patch('builtins.input', side_effect=['invalid', '0']), \
             patch('builtins.print') as mock_print:
            selected = select_device(self.mock_devices, "入力")
            self.assertEqual(selected, 0)

    def test_select_device_out_of_range_then_valid_input(self):
        with patch('builtins.input', side_effect=['5', '0']), \
             patch('builtins.print') as mock_print:
            selected = select_device(self.mock_devices, "入力")
            self.assertEqual(selected, 0)

    def test_select_device_invalid_input_device(self):
        with patch('builtins.input', side_effect=['1', '0']), \
             patch('builtins.print') as mock_print:
            selected = select_device(self.mock_devices, "入力")
            self.assertEqual(selected, 0)
            mock_print.assert_any_call("エラー: 選択されたデバイスは入力に対応していません。")

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
        with patch('sounddevice.query_devices', return_value=self.mock_devices):
            record_audio(mic_idx=0, system_idx=2)

        # ストリームが正しく開始・停止されたことを確認
        mock_mic_stream.start.assert_called_once()
        mock_system_stream.start.assert_called_once()
        mock_mic_stream.stop.assert_called_once()
        mock_system_stream.stop.assert_called_once()
        mock_mic_stream.close.assert_called_once()
        mock_system_stream.close.assert_called_once()

    def test_main_function(self):
        with patch('record_audio.list_devices', return_value=self.mock_devices), \
             patch('record_audio.select_device', side_effect=[0, 2]), \
             patch('record_audio.record_audio') as mock_record_audio, \
             patch('argparse.ArgumentParser.parse_args') as mock_args:
            
            mock_args.return_value = MagicMock(filename=None, rate=48000)
            
            from record_audio import main
            main()
            
            # record_audioが正しいパラメータで呼び出されたことを確認
            mock_record_audio.assert_called_once_with(None, 48000, 0, 2)

if __name__ == '__main__':
    unittest.main()