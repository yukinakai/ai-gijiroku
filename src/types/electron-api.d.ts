import { TranscriptionResult } from './index';

declare global {
  interface Window {
    electronAPI: {
      startRecording: () => Promise<string>;
      stopRecording: () => Promise<TranscriptionResult>;
    }
  }
}