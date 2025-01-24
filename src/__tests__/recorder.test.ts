import { RecordingService } from '../services/recorder';
import * as fs from 'fs';
import * as path from 'path';

describe('RecordingService', () => {
  let recordingService: RecordingService;

  beforeEach(() => {
    recordingService = new RecordingService();
    jest.clearAllMocks();
  });

  describe('startRecording', () => {
    it('録音を開始し、ファイルパスを返すこと', async () => {
      const filePath = await recordingService.startRecording();
      
      expect(filePath).toBeDefined();
      expect(path.basename(filePath)).toMatch(/^recording-\d+\.wav$/);
      expect(fs.createWriteStream).toHaveBeenCalledWith(filePath);
    });

    it('録音中に再度開始しようとするとエラーを投げること', async () => {
      await recordingService.startRecording();
      
      await expect(recordingService.startRecording())
        .rejects
        .toThrow('Recording is already in progress');
    });
  });

  describe('stopRecording', () => {
    it('録音を停止し、最後の録音ファイルのパスを返すこと', async () => {
      await recordingService.startRecording();
      const filePath = await recordingService.stopRecording();
      
      expect(filePath).toBeDefined();
      expect(path.basename(filePath)).toBe('recording-1.wav');
    });

    it('録音していない状態で停止しようとするとエラーを投げること', async () => {
      await expect(recordingService.stopRecording())
        .rejects
        .toThrow('No recording in progress');
    });
  });

  describe('録音ディレクトリの管理', () => {
    it('コンストラクタで録音ディレクトリが存在しない場合は作成すること', () => {
      (fs.existsSync as jest.Mock).mockReturnValueOnce(false);
      new RecordingService();
      
      expect(fs.mkdirSync).toHaveBeenCalledWith(
        expect.stringContaining('recordings'),
        expect.objectContaining({ recursive: true })
      );
    });
  });

  describe('プラットフォーム固有の設定', () => {
    const originalPlatform = process.platform;

    afterAll(() => {
      Object.defineProperty(process, 'platform', {
        value: originalPlatform
      });
    });

    it('macOSの場合、適切な音声ソース設定を返すこと', () => {
      Object.defineProperty(process, 'platform', {
        value: 'darwin'
      });

      recordingService = new RecordingService();
      const result = recordingService['getSystemAudioSource']();
      
      expect(result.options).toEqual(['-f', 'avfoundation', '-i', ':0']);
    });

    it('Windowsの場合、適切な音声ソース設定を返すこと', () => {
      Object.defineProperty(process, 'platform', {
        value: 'win32'
      });

      recordingService = new RecordingService();
      const result = recordingService['getSystemAudioSource']();
      
      expect(result.options).toEqual(['-f', 'dshow', '-i', 'audio=virtual-audio-capturer']);
    });
  });
});