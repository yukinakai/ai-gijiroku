declare module 'node-audiorecorder' {
  import { EventEmitter } from 'events';

  interface AudioRecorderOptions {
    program?: string;
    device?: string | null;
    bits?: number;
    channels?: number;
    encoding?: string;
    rate?: number;
    type?: string;
    silence?: number;
    options?: string[];
  }

  class AudioRecorder extends EventEmitter {
    constructor(options?: AudioRecorderOptions, logger?: Console);
    start(): this;
    stop(): void;
    stream(): NodeJS.ReadableStream;
  }

  export default AudioRecorder;
}