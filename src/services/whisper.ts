import OpenAI from 'openai';
import * as fs from 'fs';
import { TranscriptionResult, WhisperOptions } from '../types';

export class WhisperService {
  private openai: OpenAI;

  constructor() {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error('OPENAI_API_KEY environment variable is not set');
    }
    this.openai = new OpenAI({ apiKey });
  }

  public async transcribe(
    audioFilePath: string,
    options: WhisperOptions = {}
  ): Promise<TranscriptionResult> {
    if (!fs.existsSync(audioFilePath)) {
      throw new Error(`Audio file not found: ${audioFilePath}`);
    }

    try {
      const response = await this.openai.audio.transcriptions.create({
        file: fs.createReadStream(audioFilePath),
        model: options.model || 'whisper-1',
        language: options.language || 'ja',
        response_format: 'verbose_json',
        temperature: options.temperature || 0,
        prompt: options.prompt
      });

      // OpenAIのレスポンスを標準化された形式に変換
      const result: TranscriptionResult = {
        text: response.text,
        language: response.language,
        segments: response.segments?.map(segment => ({
          text: segment.text,
          start: segment.start,
          end: segment.end,
          confidence: 1.0 // Whisper APIは現在confidenceを提供していないため、デフォルト値を設定
        }))
      };

      return result;
    } catch (error) {
      console.error('Whisper API error:', error);
      throw new Error('Failed to transcribe audio');
    } finally {
      // 一時的な音声ファイルを削除
      this.cleanupAudioFile(audioFilePath);
    }
  }

  private cleanupAudioFile(filePath: string): void {
    try {
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    } catch (error) {
      console.error('Failed to cleanup audio file:', error);
    }
  }
}