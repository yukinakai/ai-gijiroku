class RecordingUI {
  private startButton: HTMLButtonElement;
  private stopButton: HTMLButtonElement;
  private statusDiv: HTMLDivElement;
  private transcriptDiv: HTMLDivElement;
  private isRecording: boolean = false;

  constructor() {
    this.startButton = document.getElementById('startRecording') as HTMLButtonElement;
    this.stopButton = document.getElementById('stopRecording') as HTMLButtonElement;
    this.statusDiv = document.getElementById('status') as HTMLDivElement;
    this.transcriptDiv = document.getElementById('transcript') as HTMLDivElement;

    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    this.startButton.addEventListener('click', () => this.startRecording());
    this.stopButton.addEventListener('click', () => this.stopRecording());
  }

  private async startRecording(): Promise<void> {
    try {
      this.isRecording = true;
      this.updateUIState();
      
      await window.electronAPI.startRecording();
      this.setStatus('録音中...', 'recording');
    } catch (error) {
      console.error('録音開始エラー:', error);
      this.setStatus('録音開始に失敗しました', '');
      this.isRecording = false;
      this.updateUIState();
    }
  }

  private async stopRecording(): Promise<void> {
    try {
      this.isRecording = false;
      this.updateUIState();
      this.setStatus('文字起こし中...', 'transcribing');

      const result = await window.electronAPI.stopRecording();
      this.displayTranscription(result);
      this.setStatus('完了', '');
    } catch (error) {
      console.error('録音停止エラー:', error);
      this.setStatus('録音停止に失敗しました', '');
    }
  }

  private updateUIState(): void {
    this.startButton.disabled = this.isRecording;
    this.stopButton.disabled = !this.isRecording;
  }

  private setStatus(message: string, className: string = ''): void {
    this.statusDiv.textContent = message;
    this.statusDiv.className = 'status ' + className;
  }

  private displayTranscription(result: any): void {
    let transcriptText = result.text;

    if (result.segments && result.segments.length > 0) {
      transcriptText = result.segments
        .map((segment: any) => {
          const timeStamp = this.formatTime(segment.start);
          return `[${timeStamp}] ${segment.text}`;
        })
        .join('\n');
    }

    this.transcriptDiv.textContent = transcriptText;
  }

  private formatTime(seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  }
}

// UIの初期化
window.addEventListener('DOMContentLoaded', () => {
  new RecordingUI();
});