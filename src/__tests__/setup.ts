// OpenAI APIキーのモック
process.env.OPENAI_API_KEY = 'test-api-key';

// AudioRecorderのモック
jest.mock('node-audiorecorder', () => {
  return class MockAudioRecorder {
    private eventHandlers: { [key: string]: Function[] } = {};

    constructor() {
      this.eventHandlers = {};
    }

    start() {
      return {
        stream: () => ({
          pipe: jest.fn()
        })
      };
    }

    stop() {
      return;
    }

    on(event: string, handler: Function) {
      if (!this.eventHandlers[event]) {
        this.eventHandlers[event] = [];
      }
      this.eventHandlers[event].push(handler);
    }

    emit(event: string, ...args: any[]) {
      if (this.eventHandlers[event]) {
        this.eventHandlers[event].forEach(handler => handler(...args));
      }
    }
  };
});

// fs モジュールのモック
jest.mock('fs', () => ({
  ...jest.requireActual('fs'),
  createWriteStream: jest.fn(),
  createReadStream: jest.fn(),
  existsSync: jest.fn().mockReturnValue(true),
  mkdirSync: jest.fn(),
  unlinkSync: jest.fn(),
  readdirSync: jest.fn().mockReturnValue(['recording-1.wav']),
}));

// OpenAI モジュールのモック
jest.mock('openai', () => {
  return class MockOpenAI {
    audio = {
      transcriptions: {
        create: jest.fn().mockResolvedValue({
          text: 'テスト文字起こし',
          language: 'ja',
          segments: [
            {
              text: 'テスト文字起こし',
              start: 0,
              end: 1,
            }
          ]
        })
      }
    };
  };
});