import { contextBridge, ipcRenderer } from 'electron';

// Electronの機能をレンダラープロセスに公開
contextBridge.exposeInMainWorld(
  'electronAPI',
  {
    startRecording: () => ipcRenderer.invoke('start-recording'),
    stopRecording: () => ipcRenderer.invoke('stop-recording')
  }
);