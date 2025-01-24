import { WhisperService } from '../services/whisper';
import OpenAI from 'openai';
import * as fs from 'fs';

jest.mock('openai');

describe('WhisperService', () => {
  let whisperService: WhisperService;
  const mockAudioPath = '/path/to/audio.wav';

  beforeEach(() => {
    whisperService = new WhisperService();
    jest.clearAllMocks();
  });

  describe('constructor', () => {
    it('APIキーが設定されていない場合はエラーを投げること', () => {
      const originalApiKey = process.env.OPENAI_API_KEY;
      process.env.OPENAI_API_KEY = '';

      expect(() => new WhisperService()).toThrow('OPENAI_API_KEY environment variable is not set');

      process.env.OPENAI_API_KEY = originalApiKey;
    });
  });

  describe('transcribe', () => {
    it('音声ファイルを文字起こしし、結果を返すこと', async () => {
      const expectedResult = {
        text: 'テスト文字起こし',
        language: 'ja',
        segments: [{
          text: 'テスト文字起こし',
          start: 0,
          end: 1,
          confidence: 1.0
        }]
      };

      const result = await whisperService.transcribe(mockAudioPath);

      expect(result).toEqual(expectedResult);
      expect(fs.createReadStream).toHaveBeenCalledWith(mockAudioPath);
    });

    it('オプションを指定して文字起こしできること', async () => {
      const options = {
        language: 'en',
        model: 'whisper-1',
        temperature: 0.5,
        prompt: 'Meeting transcript'
      };

      await whisperService.transcribe(mockAudioPath, options);

      const mockOpenAI = (OpenAI as jest.MockedClass<typeof OpenAI>).mock.instances[0];
      const createCall = mockOpenAI.audio.transcriptions.create as jest.Mock;

      expect(createCall).toHaveBeenCalledWith(expect.objectContaining({
        language: options.language,
        model: options.model,
        temperature: options.temperature,
        prompt: options.prompt
      }));
    });

    it('音声ファイルが存在しない場合はエラーを投げること', async () => {
      (fs.existsSync as jest.Mock).mockReturnValueOnce(false);

      await expect(whisperService.transcribe('/nonexistent.wav'))
        .rejects
        .toThrow('Audio file not found');
    });

    it('API呼び出しが失敗した場合はエラーを投げること', async () => {
      const mockError = new Error('API Error');
      const mockOpenAI = (OpenAI as jest.MockedClass<typeof OpenAI>).mock.instances[0];
      (mockOpenAI.audio.transcriptions.create as jest.Mock).mockRejectedValueOnce(mockError);

      await expect(whisperService.transcribe(mockAudioPath))
        .rejects
        .toThrow('Failed to transcribe audio');
    });
  });

  describe('cleanupAudioFile', () => {
    it('音声ファイルを削除すること', () => {
      whisperService['cleanupAudioFile'](mockAudioPath);
      expect(fs.unlinkSync).toHaveBeenCalledWith(mockAudioPath);
    });

    it('ファイル削除に失敗してもエラーを投げないこと', () => {
      (fs.unlinkSync as jest.Mock).mockImplementationOnce(() => {
        throw new Error('Deletion failed');
      });

      expect(() => {
        whisperService['cleanupAudioFile'](mockAudioPath);
      }).not.toThrow();
    });
  });
});