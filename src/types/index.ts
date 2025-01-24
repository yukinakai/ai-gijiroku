export interface RecordingOptions {
  sampleRate?: number;
  channels?: number;
  format?: string;
}

export interface TranscriptionResult {
  text: string;
  language?: string;
  confidence?: number;
  segments?: Array<{
    text: string;
    start: number;
    end: number;
    confidence: number;
  }>;
}

export interface WhisperOptions {
  language?: string;
  prompt?: string;
  temperature?: number;
  model?: string;
}