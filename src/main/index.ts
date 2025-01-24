import { app, BrowserWindow, ipcMain } from 'electron';
import * as path from 'path';
import * as dotenv from 'dotenv';
import { RecordingService } from '../services/recorder';
import { WhisperService } from '../services/whisper';

// 環境変数の読み込み
dotenv.config();

class MainProcess {
  private mainWindow: BrowserWindow | null = null;
  private recordingService: RecordingService;
  private whisperService: WhisperService;

  constructor() {
    // OpenAI APIキーの確認
    if (!process.env.OPENAI_API_KEY) {
      throw new Error('OPENAI_API_KEY environment variable is not set');
    }

    this.recordingService = new RecordingService();
    this.whisperService = new WhisperService();
    this.setupIpcHandlers();
  }

  private setupIpcHandlers(): void {
    ipcMain.handle('start-recording', async () => {
      return await this.recordingService.startRecording();
    });

    ipcMain.handle('stop-recording', async () => {
      const audioFile = await this.recordingService.stopRecording();
      return await this.whisperService.transcribe(audioFile);
    });
  }

  public async init(): Promise<void> {
    await app.whenReady();

    this.mainWindow = new BrowserWindow({
      width: 800,
      height: 600,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, 'preload.js')
      }
    });

    await this.mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));

    // 開発時はDevToolsを開く
    if (process.env.NODE_ENV === 'development') {
      this.mainWindow.webContents.openDevTools();
    }

    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        app.quit();
      }
    });

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        this.init();
      }
    });
  }
}

// エラーハンドリング
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  app.quit();
});

process.on('unhandledRejection', (error) => {
  console.error('Unhandled Rejection:', error);
  app.quit();
});

const main = new MainProcess();
main.init().catch(console.error);