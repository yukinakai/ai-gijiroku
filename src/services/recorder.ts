import AudioRecorder from 'node-audiorecorder';
import { EventEmitter } from 'events';
import * as path from 'path';
import * as fs from 'fs';
import { RecordingOptions } from '../types';

interface AudioSourceOptions {
  options: string[];
}

export class RecordingService extends EventEmitter {
  private recorder: AudioRecorder | null = null;
  private outputPath: string;
  private isRecording: boolean = false;
  private recordingOptions: RecordingOptions;

  constructor(options: RecordingOptions = {}) {
    super();
    this.outputPath = path.join(process.cwd(), 'recordings');
    this.recordingOptions = options;
    
    // 録音ディレクトリの作成
    if (!fs.existsSync(this.outputPath)) {
      fs.mkdirSync(this.outputPath, { recursive: true });
    }
  }

  public async startRecording(): Promise<string> {
    if (this.isRecording) {
      throw new Error('Recording is already in progress');
    }

    const fileName = `recording-${Date.now()}.wav`;
    const filePath = path.join(this.outputPath, fileName);

    const options = {
      program: 'rec',      // SoXのrecコマンドを使用
      silence: 0,
      device: null,
      bits: 16,
      channels: this.recordingOptions.channels ?? 1,
      encoding: 'signed-integer',
      rate: this.recordingOptions.sampleRate ?? 16000,
      type: this.recordingOptions.format ?? 'wav',
      ...this.getSystemAudioSource()
    };

    this.recorder = new AudioRecorder(options, console);

    // エラーハンドリング
    this.recorder.on('error', (error: Error) => {
      console.error('Recording error:', error);
      this.isRecording = false;
      throw error;
    });

    // 録音ストリームの作成
    const fileStream = fs.createWriteStream(filePath);
    this.recorder.start().stream().pipe(fileStream);

    this.isRecording = true;
    return filePath;
  }

  public async stopRecording(): Promise<string> {
    if (!this.isRecording || !this.recorder) {
      throw new Error('No recording in progress');
    }

    return new Promise((resolve, reject) => {
      try {
        this.recorder!.stop();
        this.isRecording = false;
        const lastRecording = this.getLastRecordingFile();
        resolve(lastRecording);
      } catch (error) {
        reject(error);
      }
    });
  }

  private getLastRecordingFile(): string {
    const files = fs.readdirSync(this.outputPath);
    const lastFile = files
      .filter(file => file.startsWith('recording-'))
      .sort()
      .pop();

    if (!lastFile) {
      throw new Error('No recording file found');
    }

    return path.join(this.outputPath, lastFile);
  }

  private getSystemAudioSource(): AudioSourceOptions {
    // プラットフォームに応じて適切な音声ソースを設定
    switch (process.platform) {
      case 'darwin':
        return {
          options: [
            '-d',           // デバイスを指定
            'coreaudio',    // macOSのCoreAudioを使用
            'default',      // デフォルトの入力デバイス
            '-t',           // 形式を指定
            'coreaudio'     // CoreAudioフォーマット
          ]
        };
      case 'win32':
        return {
          options: [
            '-d',
            'waveaudio',    // Windowsの音声システム
            'default',
            '-t',
            'waveaudio'
          ]
        };
      default:
        return {
          options: [
            '-d',
            'pulseaudio',   // Linux/UNIXのPulseAudio
            'default',
            '-t',
            'pulseaudio'
          ]
        };
    }
  }
}