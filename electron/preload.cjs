const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  openFileDialog: (options) => ipcRenderer.invoke('dialog:openFile', options),
  saveFileDialog: (options) => ipcRenderer.invoke('dialog:saveFile', options),
  getBackendStatus: () => ipcRenderer.invoke('app:getBackendStatus'),
  // Google OAuth: opens system browser, listens on local loopback, resolves with { code, redirect_uri }
  googleLogin: () => ipcRenderer.invoke('auth:googleLogin'),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
});
